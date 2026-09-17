from __future__ import annotations

import asyncio
import inspect
import os
import re
import urllib.parse
from typing import Any

import aiohttp

from .state import Track

# ============================================================================
# PRIME × BEATS — HYBRID YOUTUBE PROVIDER
# ============================================================================
#
# Provider order:
#
#   SEARCH:
#       1. py-yt-search
#       2. public YouTube Music Vercel search
#       3. Yuki REST /search
#       4. yt-dlp flat search
#
#   PLAYBACK:
#       1. Yuki /download + /stream (direct URL, preferred)
#       2. yt-dlp direct extraction for audio
#       3. yt-dlp local MP4 fallback for video
#
# This intentionally does NOT use Yuki /details because the live deployment
# has returned 404/502 for that route in this bot's environment.
#
# If Yuki /search is temporarily unavailable (502, 503, timeout, etc.),
# /search and /play still have independent fallback providers.
# ============================================================================

API_URL = os.environ.get(
    "MEOW_API_URL", "https://music.yukiapi.site"
).rstrip("/")
API_KEY = os.environ.get("MEOW_API_KEY", "").strip()

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")

_YTDLP_SEMAPHORE = asyncio.Semaphore(2)
_SEARCH_SEMAPHORE = asyncio.Semaphore(4)

# Small in-process cache prevents repeated provider calls for the same query.
_SEARCH_CACHE: dict[tuple[str, int], tuple[float, list[dict]]] = {}
_SEARCH_CACHE_TTL = 60.0
_SEARCH_CACHE_MAX = 200


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _get(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _extract_video_id(value: Any) -> str | None:
    """Extract an 11-character YouTube video ID from common URL forms."""
    text = str(value or "").strip()
    if not text:
        return None

    # Bare ID.
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text

    patterns = (
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?[^#]*?(?:[?&])v=([A-Za-z0-9_-]{11})(?:[&#]|$)",
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})(?:[&#]|$)",
        r"(?:https?://)?youtu\.be/([A-Za-z0-9_-]{11})(?:[?&#/]|$)",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})(?:[?&#/]|$)",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})(?:[?&#/]|$)",
        r"(?:https?://)?(?:www\.)?youtube\.com/live/([A-Za-z0-9_-]{11})(?:[?&#/]|$)",
    )

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)

    # Query-string fallback for unusual parameter ordering.
    try:
        parsed = urllib.parse.urlparse(text)
        host = (parsed.netloc or "").lower()
        if "youtube.com" in host:
            values = urllib.parse.parse_qs(parsed.query).get("v") or []
            if values and re.fullmatch(r"[A-Za-z0-9_-]{11}", values[0]):
                return values[0]
    except Exception:
        pass

    return None


def _clean_link(link: str) -> str:
    return str(link or "").strip()


def _seconds(value: Any) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))

    text = str(value or "").strip()
    if not text:
        return 0

    if text.isdigit():
        return max(0, int(text))

    parts = text.split(":")
    try:
        total = 0
        for part in parts:
            total = total * 60 + int(part)
        return max(0, total)
    except Exception:
        return 0


def duration(value: Any) -> str:
    sec = _seconds(value)
    return f"{sec // 60}:{sec % 60:02d}"


def _thumbnail(item: Any) -> str:
    thumb = _get(item, "thumbnail", "") or ""
    if thumb:
        return str(thumb)

    thumbs = _get(item, "thumbnails", []) or []
    if thumbs:
        first = thumbs[0]
        url = _get(first, "url", "") or ""
        if url:
            return str(url)

    vid = str(_get(item, "id", "") or _get(item, "vidid", "") or "")
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""


def _link(item: Any) -> str:
    link = _get(item, "link", "") or _get(item, "webpage_url", "")
    if link:
        return str(link)

    vid = str(_get(item, "id", "") or _get(item, "vidid", "") or "")
    return f"https://www.youtube.com/watch?v={vid}" if vid else ""


def _normalize_result(item: Any) -> dict:
    vid = str(_get(item, "id", "") or _get(item, "vidid", "") or "").strip()
    title = str(_get(item, "title", "Unknown") or "Unknown")
    dur = _get(item, "duration", None)

    if dur is None:
        dur = _get(item, "duration_string", "0:00")

    thumb = _thumbnail(item)
    link = _link(item)

    if not link and vid:
        link = f"https://www.youtube.com/watch?v={vid}"

    return {
        "id": vid,
        "title": title,
        "link": link,
        "duration": str(dur or "0:00"),
        "duration_sec": _seconds(
            _get(item, "duration_sec", _get(item, "duration", 0))
        ),
        "thumbnails": [{"url": thumb}] if thumb else [],
    }


def _entry_from_id(video_id: str, title: str = "") -> dict:
    return {
        "id": video_id,
        "title": title or f"YouTube Video ({video_id})",
        "link": f"https://www.youtube.com/watch?v={video_id}",
        "duration": "0:00",
        "duration_sec": 0,
        "thumbnails": [
            {"url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"}
        ],
    }


def _make_track(
    item: Any,
    requested_by: str = "Unknown",
    stream_url: str = "",
    video: bool = False,
) -> Track:
    row = _normalize_result(item)

    return Track(
        title=row["title"],
        webpage_url=row["link"],
        stream_url=stream_url or "",
        duration=_seconds(row.get("duration_sec") or row.get("duration")),
        thumbnail=_thumbnail(row),
        requested_by=requested_by or "Unknown",
        source="YouTube",
        video=bool(video),
    )


# ---------------------------------------------------------------------------
# Search provider 1 — py-yt-search
# ---------------------------------------------------------------------------

async def _search_pyyt(query: str, limit: int) -> list[dict]:
    try:
        from py_yt import VideosSearch

        search = VideosSearch(query, limit=max(1, int(limit)))
        result = await search.next()

        rows = result.get("result", []) if isinstance(result, dict) else []
        output: list[dict] = []

        for row in rows:
            if not row or not row.get("id"):
                continue

            item = {
                "id": row.get("id"),
                "title": row.get("title") or query,
                "link": row.get("link")
                or f"https://www.youtube.com/watch?v={row['id']}",
                "duration": row.get("duration") or "0:00",
                "thumbnails": row.get("thumbnails") or [],
            }

            output.append(_normalize_result(item))

            if len(output) >= int(limit):
                break

        if output:
            print(f"[YouTube search] py-yt-search OK: {query!r}")
        return output

    except Exception as exc:
        print(f"[YouTube search] py-yt-search failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Search provider 2 — public YouTube Music API
# ---------------------------------------------------------------------------

async def _search_vercel(query: str, limit: int) -> list[dict]:
    url = (
        "https://yt-music-api-seven.vercel.app/search/musics"
        f"?query={urllib.parse.quote(query)}"
    )

    timeout = aiohttp.ClientTimeout(total=8, connect=4, sock_read=6)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    print(
                        f"[YouTube search] Vercel HTTP {resp.status}"
                    )
                    return []

                data = await resp.json(content_type=None)

        output: list[dict] = []

        for item in data.get("content", []) if isinstance(data, dict) else []:
            vid = item.get("id")
            title = item.get("title")

            if not vid or not title:
                continue

            dur_obj = item.get("duration") or {}
            if isinstance(dur_obj, dict):
                dur = dur_obj.get("formatted") or "0:00"
            else:
                dur = str(dur_obj or "0:00")

            thumbs = item.get("thumbnails") or []
            thumb = ""

            if thumbs:
                last = thumbs[-1]
                if isinstance(last, dict):
                    thumb = str(last.get("url") or "")

            output.append(
                _normalize_result(
                    {
                        "id": vid,
                        "title": title,
                        "link": f"https://www.youtube.com/watch?v={vid}",
                        "duration": dur,
                        "thumbnails": [{"url": thumb}] if thumb else [],
                    }
                )
            )

            if len(output) >= int(limit):
                break

        if output:
            print(f"[YouTube search] Vercel OK: {query!r}")

        return output

    except Exception as exc:
        print(f"[YouTube search] Vercel failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Search provider 3 — Yuki REST
# ---------------------------------------------------------------------------

async def _yuki_request(
    path: str,
    params: dict | None = None,
    attempts: int = 2,
) -> dict:
    """
    Direct Yuki REST request.

    Both documented Yuki base URLs are tried. Temporary 5xx responses are
    treated as provider failures, not fatal bot failures.
    """
    timeout = aiohttp.ClientTimeout(
        total=15,
        connect=5,
        sock_read=10,
    )

    bases = []
    for base in (API_URL, "https://yukiapi.site/music"):
        base = str(base or "").rstrip("/")
        if base and base not in bases:
            bases.append(base)

    last_error = "unknown error"

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for base in bases:
            for attempt in range(max(1, int(attempts))):
                try:
                    url = f"{base}{path}"

                    async with session.get(url, params=params) as resp:
                        body = await resp.text()

                        if resp.status == 200:
                            try:
                                import json
                                data = json.loads(body)
                            except Exception as exc:
                                raise RuntimeError(
                                    f"invalid JSON: {exc}"
                                ) from exc

                            if not isinstance(data, dict):
                                raise RuntimeError(
                                    "Yuki response was not a JSON object"
                                )

                            return data

                        last_error = f"HTTP {resp.status}: {body[:250]}"

                        # Retry transient server errors.
                        if resp.status in (408, 425, 429, 500, 502, 503, 504):
                            if attempt + 1 < max(1, int(attempts)):
                                await asyncio.sleep(0.35 * (attempt + 1))
                                continue

                        break

                except Exception as exc:
                    last_error = str(exc)

                    if attempt + 1 < max(1, int(attempts)):
                        await asyncio.sleep(0.35 * (attempt + 1))
                        continue

                    break

    raise RuntimeError(f"Yuki API request failed: {last_error}")


async def _search_yuki(query: str, limit: int) -> list[dict]:
    try:
        data = await _yuki_request(
            "/search",
            {
                "q": query,
                "limit": max(1, int(limit)),
            },
            attempts=2,
        )

        rows = data.get("results") or []
        output = [_normalize_result(row) for row in rows[: int(limit)]]

        output = [row for row in output if row.get("id")]

        if output:
            print(f"[YouTube search] Yuki OK: {query!r}")

        return output

    except Exception as exc:
        print(f"[YouTube search] Yuki unavailable: {exc}")
        return []


# ---------------------------------------------------------------------------
# Search provider 4 — yt-dlp flat extraction
# ---------------------------------------------------------------------------

def _ytdlp_search_sync(query: str, limit: int) -> list[dict]:
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
        "playlistend": max(1, int(limit)),
    }

    # Use the local bgutil provider when it is installed/running.
    opts["extractor_args"] = {
        "youtubepot-bgutilhttp": {
            "base_url": os.environ.get(
                "BGUTIL_POT_PROVIDER_URL",
                os.environ.get(
                    "BGUTIL_POT_BASE_URL",
                    "http://127.0.0.1:4416",
                ),
            )
        }
    }

    target = query
    if not _extract_video_id(query):
        target = f"ytsearch{max(1, int(limit))}:{query}"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(target, download=False) or {}

    entries = info.get("entries") or []

    if entries:
        entries = [entry for entry in entries if entry][: int(limit)]
    else:
        entries = [info] if info.get("id") else []

    output = []

    for entry in entries:
        vid = entry.get("id")
        if not vid:
            continue

        dur = int(entry.get("duration") or 0)

        output.append(
            _normalize_result(
                {
                    "id": vid,
                    "title": entry.get("title") or "Unknown",
                    "link": entry.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={vid}",
                    "duration": (
                        f"{dur // 60}:{dur % 60:02d}"
                        if dur
                        else "0:00"
                    ),
                    "duration_sec": dur,
                    "thumbnails": [
                        {
                            "url": entry.get("thumbnail")
                            or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                        }
                    ],
                }
            )
        )

    return output


async def _search_ytdlp(query: str, limit: int) -> list[dict]:
    try:
        output = await asyncio.to_thread(
            _ytdlp_search_sync,
            query,
            int(limit),
        )

        if output:
            print(f"[YouTube search] yt-dlp OK: {query!r}")

        return output

    except Exception as exc:
        print(f"[YouTube search] yt-dlp failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------

async def search_results(query: str, limit: int = 8) -> list[dict]:
    """
    Search with independent fallbacks.

    IMPORTANT:
    Yuki being down must NOT make /search fail.
    """
    query = str(query or "").strip()
    limit = max(1, min(int(limit), 20))

    if not query:
        return []

    cache_key = (query.lower(), limit)
    now = asyncio.get_running_loop().time()

    cached = _SEARCH_CACHE.get(cache_key)
    if cached and now - cached[0] < _SEARCH_CACHE_TTL:
        return [dict(row) for row in cached[1]]

    # Direct URL/ID gets a fast metadata search first.
    providers = (
        _search_pyyt,
        _search_vercel,
        _search_yuki,
        _search_ytdlp,
    )

    async with _SEARCH_SEMAPHORE:
        for provider in providers:
            try:
                rows = await provider(query, limit)
            except Exception as exc:
                print(
                    f"[YouTube search] provider {provider.__name__} "
                    f"crashed: {exc}"
                )
                rows = []

            if rows:
                # Deduplicate by video ID.
                seen = set()
                clean = []

                for row in rows:
                    vid = str(row.get("id") or "").strip()
                    if not vid or vid in seen:
                        continue

                    seen.add(vid)
                    clean.append(row)

                if clean:
                    if len(_SEARCH_CACHE) >= _SEARCH_CACHE_MAX:
                        oldest = min(
                            _SEARCH_CACHE,
                            key=lambda key: _SEARCH_CACHE[key][0],
                        )
                        _SEARCH_CACHE.pop(oldest, None)

                    _SEARCH_CACHE[cache_key] = (
                        asyncio.get_running_loop().time(),
                        clean[:limit],
                    )
                    return clean[:limit]

    return []


async def _search_one(query: str) -> dict | None:
    rows = await search_results(query, 1)
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Yuki direct stream
# ---------------------------------------------------------------------------

async def _yuki_direct_stream(video_id: str, video: bool) -> str:
    vid = str(video_id or "").strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        raise RuntimeError("Invalid YouTube video ID")

    media_type = "video" if video else "audio"

    data = await _yuki_request(
        "/download",
        {
            "url": vid,
            "type": media_type,
        },
        attempts=2,
    )

    token = str(
        data.get("download_token")
        or data.get("token")
        or ""
    ).strip()

    if not token:
        raise RuntimeError("Yuki did not return a download token")

    return (
        f"{API_URL}/stream/{vid}"
        f"?type={urllib.parse.quote(media_type)}"
        f"&token={urllib.parse.quote(token, safe='')}"
    )


# ---------------------------------------------------------------------------
# yt-dlp direct playback fallback
# ---------------------------------------------------------------------------

def _youtube_cookie_file() -> str | None:
    """Return the first usable YouTube cookies file.

    Render Secret Files are exposed at /etc/secrets/<filename>. For local
    development we also support /app/cookies.txt and a custom path through
    YOUTUBE_COOKIES_FILE.
    """
    candidates = [
        os.environ.get("YOUTUBE_COOKIES_FILE", "").strip(),
        "/etc/secrets/cookies.txt",
        "/app/cookies.txt",
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.path.getsize(path) > 0:
            return path
    return None


def _yt_dlp_common_opts() -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_retries": 3,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        # Current YouTube extraction requires a JS runtime for challenge
        # solving. Deno is installed by the Docker image; Node is used when
        # available as a secondary runtime.
        "js_runtimes": {"deno": {}, "node": {}},
        "remote_components": ["ejs:npm"],
        "extractor_args": {
            "youtubepot-bgutilhttp": {
                "base_url": os.environ.get(
                    "BGUTIL_POT_PROVIDER_URL",
                    os.environ.get(
                        "BGUTIL_POT_BASE_URL",
                        "http://127.0.0.1:4416",
                    ),
                )
            }
        },
    }
    cookie_file = _youtube_cookie_file()
    if cookie_file:
        opts["cookiefile"] = cookie_file
        print(f"[youtube] Using cookies file: {cookie_file}", flush=True)
    else:
        print("[youtube] No cookies file found; using anonymous extraction", flush=True)
    return opts


def _ytdlp_extract_with_profiles(video_id: str, video: bool = False) -> dict:
    """Try several YouTube player clients without changing the public API."""
    import yt_dlp

    target = f"https://www.youtube.com/watch?v={video_id}"
    profiles = [
        ("default", None),
        ("mweb", ["mweb"]),
        ("web_creator", ["web_creator", "mweb", "default"]),
        ("android", ["android", "web_embedded", "default"]),
        ("web_embedded", ["web_embedded"]),
    ]
    errors: list[str] = []

    for name, clients in profiles:
        opts = _yt_dlp_common_opts()
        opts["skip_download"] = True
        opts["format"] = (
            "best[height<=720][ext=mp4][vcodec!=none][acodec!=none]/"
            "best[height<=720][vcodec!=none][acodec!=none]/best"
            if video
            else
            "bestaudio[ext=m4a]/bestaudio[acodec=opus]/bestaudio/best"
        )
        if clients:
            opts["extractor_args"]["youtube"] = {"player_client": clients}

        try:
            print(f"[yt-dlp] profile={name} target={video_id}", flush=True)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(target, download=False) or {}
            if info.get("entries"):
                info = next((item for item in info["entries"] if item), None) or {}
            if info.get("url"):
                return info
            formats = info.get("formats") or []
            usable = [
                f for f in formats
                if f.get("url") and (
                    (video and f.get("vcodec") not in (None, "none")) or
                    (not video and f.get("acodec") not in (None, "none"))
                )
            ]
            if usable:
                return usable[-1] | {
                    "id": info.get("id", video_id),
                    "title": info.get("title", "Unknown"),
                    "thumbnail": info.get("thumbnail"),
                    "webpage_url": info.get("webpage_url", target),
                    "duration": info.get("duration", 0),
                }
        except Exception as exc:
            text = str(exc).replace("\n", " ").strip()
            errors.append(f"{name}: {text[-350:]}")

    raise RuntimeError("yt-dlp extraction failed | " + " || ".join(errors))


def _ytdlp_audio_url_sync(video_id: str) -> str:
    info = _ytdlp_extract_with_profiles(video_id, video=False)
    url = info.get("url")
    if url:
        return str(url)
    raise RuntimeError("yt-dlp returned no audio URL")


def _ytdlp_video_file_sync(video_id: str) -> str:
    import yt_dlp

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    out_path = os.path.abspath(
        os.path.join(DOWNLOAD_DIR, f"{video_id}.fallback.mp4")
    )

    if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
        return out_path

    target = f"https://www.youtube.com/watch?v={video_id}"
    profiles = [
        ("default", None),
        ("mweb", ["mweb"]),
        ("web_creator", ["web_creator", "mweb", "default"]),
        ("android", ["android", "web_embedded", "default"]),
        ("web_embedded", ["web_embedded"]),
    ]
    errors: list[str] = []

    for name, clients in profiles:
        opts = _yt_dlp_common_opts()
        opts.pop("skip_download", None)
        opts.update({
            "format": (
                "bestvideo[height<=720]+bestaudio/"
                "best[height<=720]/best"
            ),
            "merge_output_format": "mp4",
            "outtmpl": out_path,
            "overwrites": False,
            "retries": 2,
            "fragment_retries": 2,
        })
        if clients:
            opts["extractor_args"]["youtube"] = {"player_client": clients}

        try:
            print(f"[yt-dlp] video profile={name} target={video_id}", flush=True)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([target])
            if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                return out_path
        except Exception as exc:
            text = str(exc).replace("\n", " ").strip()
            errors.append(f"{name}: {text[-350:]}")

    raise RuntimeError("yt-dlp video download failed | " + " || ".join(errors))


async def _fallback_stream(video_id: str, video: bool) -> str:
    async with _YTDLP_SEMAPHORE:
        if video:
            return await asyncio.to_thread(
                _ytdlp_video_file_sync,
                video_id,
            )

        return await asyncio.to_thread(
            _ytdlp_audio_url_sync,
            video_id,
        )


async def _get_stream(video_id: str, video: bool) -> str:
    """
    Preferred Yuki direct URL, with yt-dlp fallback.

    This means a temporary Yuki 502 no longer kills playback.
    """
    try:
        stream = await _yuki_direct_stream(video_id, video)
        print(
            f"[Playback] Yuki stream OK: id={video_id} "
            f"type={'video' if video else 'audio'}"
        )
        return stream
    except Exception as exc:
        print(
            f"[Playback] Yuki stream unavailable for {video_id}: {exc}"
        )

    stream = await _fallback_stream(video_id, video)

    print(
        f"[Playback] yt-dlp fallback OK: id={video_id} "
        f"type={'video' if video else 'audio'}"
    )

    return stream


# ---------------------------------------------------------------------------
# Track resolution
# ---------------------------------------------------------------------------

async def resolve_result(
    item: Any,
    requested_by: str = "Unknown",
    video: bool = False,
) -> Track:
    """
    Resolve a cached /search result without performing another metadata search.
    """
    row = (
        item
        if isinstance(item, dict)
        else _normalize_result(item)
    )

    vid = str(
        _get(row, "id", "")
        or _get(row, "vidid", "")
        or ""
    ).strip()

    if not vid:
        vid = _extract_video_id(_link(row)) or ""

    if not vid:
        raise RuntimeError("Search result has no YouTube video ID")

    stream_url = await _get_stream(vid, bool(video))

    return _make_track(
        row,
        requested_by=requested_by,
        stream_url=stream_url,
        video=bool(video),
    )


async def resolve(
    link_or_query: str,
    requested_by: str = "Unknown",
    video: bool = False,
) -> Track:
    """
    Resolve a YouTube query or URL.

    No /details request is used anywhere in the primary path.
    """
    query = str(link_or_query or "").strip()

    if not query:
        raise RuntimeError("Empty YouTube query")

    vid = _extract_video_id(query)

    if vid:
        # Try all search providers for proper title/duration/thumbnail.
        row = await _search_one(vid)

        if not row:
            row = _entry_from_id(vid, query)

        return await resolve_result(
            row,
            requested_by=requested_by,
            video=bool(video),
        )

    # Text query.
    row = await _search_one(query)

    if not row:
        raise RuntimeError(
            f"No YouTube result found for: {query}"
        )

    return await resolve_result(
        row,
        requested_by=requested_by,
        video=bool(video),
    )


# ---------------------------------------------------------------------------
# Compatibility helpers
# ---------------------------------------------------------------------------

async def _details(query_or_url: str) -> dict:
    """
    Compatibility metadata helper.

    Kept for older code, but implemented through the resilient search path.
    It NEVER calls Yuki /details.
    """
    row = await _search_one(str(query_or_url or "").strip())

    if not row:
        raise RuntimeError(
            f"No YouTube result found for: {query_or_url}"
        )

    return row


async def _direct_stream(query_or_url: str, video: bool) -> str:
    vid = _extract_video_id(query_or_url)

    if not vid:
        row = await _details(query_or_url)
        vid = str(
            row.get("id")
            or row.get("vidid")
            or ""
        ).strip()

    if not vid:
        raise RuntimeError("Could not determine YouTube video ID")

    return await _get_stream(vid, bool(video))


async def resolve_playlist(
    link: str,
    requested_by: str = "Unknown",
    limit: int = 20,
) -> list[Track]:
    """
    Playlist compatibility path.

    Yuki playlist is attempted first; yt-dlp flat playlist is the fallback.
    """
    limit = max(1, int(limit))

    # Yuki playlist.
    try:
        data = await _yuki_request(
            "/playlist",
            {
                "url": str(link).strip(),
                "limit": limit,
            },
            attempts=2,
        )

        rows = data.get("tracks") or []

        if rows:
            return [
                _make_track(row, requested_by=requested_by)
                for row in rows[:limit]
                if _get(row, "id") or _extract_video_id(_link(row))
            ]

    except Exception as exc:
        print(f"[Playlist] Yuki unavailable: {exc}")

    # yt-dlp fallback.
    try:
        import yt_dlp

        def _extract_playlist():
            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "playlistend": limit,
                "skip_download": True,
                "extractor_args": {
                    "youtubepot-bgutilhttp": {
                        "base_url": os.environ.get(
                            "BGUTIL_POT_PROVIDER_URL",
                            os.environ.get(
                                "BGUTIL_POT_BASE_URL",
                                "http://127.0.0.1:4416",
                            ),
                        )
                    }
                },
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(
                    str(link).strip(),
                    download=False,
                ) or {}

            entries = info.get("entries") or []

            result = []
            for entry in entries[:limit]:
                if not entry or not entry.get("id"):
                    continue

                result.append(
                    _normalize_result(
                        {
                            "id": entry["id"],
                            "title": entry.get("title") or "Unknown",
                            "link": entry.get("webpage_url")
                            or f"https://www.youtube.com/watch?v={entry['id']}",
                            "duration": entry.get("duration") or "0:00",
                            "duration_sec": entry.get("duration") or 0,
                            "thumbnails": [
                                {
                                    "url": entry.get("thumbnail")
                                    or f"https://i.ytimg.com/vi/{entry['id']}/hqdefault.jpg"
                                }
                            ],
                        }
                    )
                )

            return result

        rows = await asyncio.to_thread(_extract_playlist)

        return [
            _make_track(row, requested_by=requested_by)
            for row in rows[:limit]
        ]

    except Exception as exc:
        print(f"[Playlist] yt-dlp fallback failed: {exc}")
        return []


def topic_seeds(topic: str) -> list[str]:
    topic = str(topic or "").strip()

    if not topic:
        return []

    return [
        topic,
        f"{topic} songs",
        f"{topic} music",
        f"{topic} playlist",
    ]


async def discover_topic(
    topic: str,
    requested_by: str = "Autoplay",
    limit: int = 12,
    exclude=None,
    round_no: int = 0,
) -> list[Track]:
    excluded = {
        str(x).lower()
        for x in (exclude or set())
    }

    seeds = topic_seeds(topic)

    if not seeds:
        return []

    queries = [
        seeds[int(round_no) % len(seeds)]
    ]

    if len(seeds) > 1:
        queries.append(
            seeds[(int(round_no) + 1) % len(seeds)]
        )

    found: list[Track] = []
    seen: set[str] = set()

    for query in queries:
        try:
            rows = await search_results(
                query,
                max(8, int(limit)),
            )
        except Exception as exc:
            print(f"[Autoplay] search failed: {exc}")
            continue

        for row in rows:
            key = str(
                row.get("id")
                or row.get("link")
                or ""
            ).lower()

            if not key:
                continue

            if key in excluded or key in seen:
                continue

            seen.add(key)

            try:
                found.append(
                    _make_track(
                        row,
                        requested_by=requested_by,
                    )
                )
            except Exception:
                continue

            if len(found) >= int(limit):
                return found

    return found


# ---------------------------------------------------------------------------
# Legacy YouTubeAPI compatibility object
# ---------------------------------------------------------------------------

class YouTubeAPI:
    async def search(
        self,
        query: str,
        limit: int = 5,
    ):
        return await search_results(query, limit)

    async def details(
        self,
        link: str,
        videoid=None,
    ):
        if videoid:
            link = (
                "https://www.youtube.com/watch?v="
                + str(videoid)
            )

        item = await _details(link)

        return (
            str(_get(item, "title", "Unknown")),
            str(_get(item, "duration", "0:00")),
            _seconds(
                _get(
                    item,
                    "duration_sec",
                    _get(item, "duration", 0),
                )
            ),
            _thumbnail(item),
            str(
                _get(item, "id", "")
                or _extract_video_id(link)
                or ""
            ),
        )

    async def title(self, link: str, videoid=None):
        if videoid:
            link = (
                "https://www.youtube.com/watch?v="
                + str(videoid)
            )

        return str(
            _get(
                await _details(link),
                "title",
                "",
            )
        )

    async def duration(self, link: str, videoid=None):
        if videoid:
            link = (
                "https://www.youtube.com/watch?v="
                + str(videoid)
            )

        return str(
            _get(
                await _details(link),
                "duration",
                "0:00",
            )
        )

    async def thumbnail(self, link: str, videoid=None):
        if videoid:
            link = (
                "https://www.youtube.com/watch?v="
                + str(videoid)
            )

        return _thumbnail(await _details(link))

    async def video(self, link: str, videoid=None):
        if videoid:
            link = (
                "https://www.youtube.com/watch?v="
                + str(videoid)
            )

        track = await resolve(
            link,
            requested_by="Unknown",
            video=True,
        )

        return 1, track.stream_url

    async def download(
        self,
        link: str,
        mystic=None,
        video=False,
        videoid=None,
        songaudio=None,
        songvideo=None,
        format_id=None,
        title=None,
    ):
        if videoid:
            link = (
                "https://www.youtube.com/watch?v="
                + str(videoid)
            )

        is_video = bool(video or songvideo)

        track = await resolve(
            link,
            requested_by="Unknown",
            video=is_video,
        )

        return track.stream_url, True


YouTube = YouTubeAPI()


# ---------------------------------------------------------------------------
# Convenience download helpers
# ---------------------------------------------------------------------------

async def download_song(link: str) -> str:
    vid = _extract_video_id(link)

    if not vid:
        row = await _details(link)
        vid = str(row.get("id") or "").strip()

    if not vid:
        raise RuntimeError("Could not determine video ID")

    # For compatibility, prefer Yuki's local download endpoint if available.
    try:
        import yukiapi

        yuki = yukiapi.YukiAPI(
            base_url=API_URL,
            timeout=60,
        )

        return await yuki.download(
            vid,
            type="audio",
            output_dir=DOWNLOAD_DIR,
        )

    except Exception:
        # Fall back to yt-dlp MP3 download.
        import yt_dlp

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        output = os.path.abspath(
            os.path.join(DOWNLOAD_DIR, f"{vid}.mp3")
        )

        if os.path.exists(output) and os.path.getsize(output) > 10000:
            return output

        def _download():
            opts = {
                "quiet": True,
                "no_warnings": True,
                "format": "bestaudio/best",
                "outtmpl": output,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "extractor_args": {
                    "youtubepot-bgutilhttp": {
                        "base_url": os.environ.get(
                            "BGUTIL_POT_PROVIDER_URL",
                            os.environ.get(
                                "BGUTIL_POT_BASE_URL",
                                "http://127.0.0.1:4416",
                            ),
                        )
                    }
                },
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download(
                    [
                        f"https://www.youtube.com/watch?v={vid}"
                    ]
                )

        await asyncio.to_thread(_download)

        if os.path.exists(output):
            return output

        raise RuntimeError("Audio download failed")


async def download_video(link: str) -> str:
    vid = _extract_video_id(link)

    if not vid:
        row = await _details(link)
        vid = str(row.get("id") or "").strip()

    if not vid:
        raise RuntimeError("Could not determine video ID")

    # Use the robust local MP4 fallback.
    return await asyncio.to_thread(
        _ytdlp_video_file_sync,
        vid,
    )


async def close():
    """
    Kept for compatibility. All REST requests use short-lived sessions.
    """
    return None
