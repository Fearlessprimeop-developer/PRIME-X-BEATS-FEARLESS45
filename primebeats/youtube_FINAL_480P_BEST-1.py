import asyncio
import os
import random
import re
import shutil
import urllib.parse
from typing import Union

import aiohttp
from py_yt import VideosSearch, Playlist

API_URL = os.environ.get("MEOW_API_URL", "https://music.yukiapi.site")

API_KEY = os.environ.get("MEOW_API_KEY", "YOUR_API_KEY") ## Get This API KEY FROM TELEGRAM BOT USERNAME: @MeowApiRobot
DOWNLOAD_DIR = "downloads"

_global_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()


async def get_session() -> aiohttp.ClientSession:
    global _global_session
    if _global_session is not None and not _global_session.closed:
        return _global_session

    async with _session_lock:
        if _global_session is not None and not _global_session.closed:
            return _global_session

        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=50,
            ttl_dns_cache=600,
            keepalive_timeout=300,
            enable_cleanup_closed=True,
            force_close=False,
        )
        timeout = aiohttp.ClientTimeout(total=180, connect=10, sock_read=60)
        _global_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
        )
        return _global_session


_thumb_cache: dict[str, str] = {}
_THUMB_CACHE_MAX = 1000


def _cache_thumb(vidid: str, url: str) -> str:
    if len(_thumb_cache) >= _THUMB_CACHE_MAX:
        del _thumb_cache[next(iter(_thumb_cache))]
    _thumb_cache[vidid] = url
    return url


def _extract_video_id(link: str) -> str | None:
    if not link:
        return None
    for pat in [
        r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"youtu\.be/([0-9A-Za-z_-]{11})",
        r"embed/([0-9A-Za-z_-]{11})",
        r"shorts/([0-9A-Za-z_-]{11})",
    ]:
        m = re.search(pat, link)
        if m:
            return m.group(1)
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", link.strip()):
        return link.strip()
    return None


def _clean_link(link: str) -> str:
    return link.split("&")[0] if "&" in link else link


def time_to_seconds(time_str: str) -> int:
    if not time_str:
        return 0
    parts = time_str.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return int(parts[0]) if parts[0].isdigit() else 0


async def _fetch_oembed(video_id: str) -> dict | None:
    session = await get_session()
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
            if resp.status == 200:
                data = await resp.json()
                title = data.get("title", "")
                thumb = data.get("thumbnail_url", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")
                return {
                    "id": video_id,
                    "title": title,
                    "link": f"https://www.youtube.com/watch?v={video_id}",
                    "duration": "0:00",
                    "thumbnails": [{"url": thumb}],
                }
    except Exception:
        pass
    return None


async def _search_vercel(query: str, limit: int = 1) -> list[dict]:
    session = await get_session()
    url = f"https://yt-music-api-seven.vercel.app/search/musics?query={urllib.parse.quote(query)}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status == 200:
                data = await resp.json()
                out = []
                for item in data.get("content", []):
                    vid_id = item.get("id")
                    title = item.get("title")
                    if not vid_id or not title:
                        continue
                    dur_obj = item.get("duration", {})
                    dur_str = dur_obj.get("formatted") if isinstance(dur_obj, dict) else "0:00"
                    thumbs = item.get("thumbnails", [])
                    thumb = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
                    out.append({
                        "id": vid_id,
                        "title": title,
                        "link": f"https://www.youtube.com/watch?v={vid_id}",
                        "duration": dur_str or "0:00",
                        "thumbnails": [{"url": thumb}],
                    })
                    if len(out) >= limit:
                        break
                return out
    except Exception:
        pass
    return []


async def _search_one(query: str) -> dict | None:
    vid = _extract_video_id(query)
    if vid:
        # Direct YouTube URLs used to fall back to oEmbed immediately, which has
        # no duration field. Try the search providers first so /play and /vplay
        # can display the real duration.
        try:
            vercel = await _search_vercel(vid, limit=1)
            if vercel and vercel[0].get("id") == vid:
                return vercel[0]
        except Exception:
            pass
        try:
            s = VideosSearch(vid, limit=1)
            res = await s.next()
            items = res.get("result", [])
            if items:
                r = items[0]
                if r.get("id") == vid:
                    thumb = (
                        r["thumbnails"][0]["url"].split("?")[0]
                        if r.get("thumbnails")
                        else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                    )
                    return {
                        "id": vid,
                        "title": r.get("title", f"YouTube Video ({vid})"),
                        "link": r.get("link", f"https://www.youtube.com/watch?v={vid}"),
                        "duration": r.get("duration", "0:00"),
                        "thumbnails": [{"url": thumb}],
                    }
        except Exception:
            pass
        oembed = await _fetch_oembed(vid)
        if oembed:
            return oembed

    try:
        s = VideosSearch(query, limit=1)
        res = await s.next()
        items = res.get("result", [])
        if items and items[0].get("id"):
            r = items[0]
            thumb = (
                r["thumbnails"][0]["url"].split("?")[0]
                if r.get("thumbnails")
                else f"https://i.ytimg.com/vi/{r['id']}/hqdefault.jpg"
            )
            return {
                "id": r["id"],
                "title": r.get("title", query),
                "link": r.get("link", f"https://www.youtube.com/watch?v={r['id']}"),
                "duration": r.get("duration", "0:00"),
                "thumbnails": [{"url": thumb}],
            }
    except Exception:
        pass

    vercel_results = await _search_vercel(query, limit=1)
    if vercel_results:
        return vercel_results[0]

    try:
        import yt_dlp
        loop = asyncio.get_running_loop()

        def _ytdlp_flat():
            opts = {"extract_flat": True, "quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                target = query if vid else f"ytsearch1:{query}"
                info = ydl.extract_info(target, download=False)
                if "entries" in info and info["entries"]:
                    return info["entries"][0]
                return info

        info = await loop.run_in_executor(None, _ytdlp_flat)
        if info and info.get("id"):
            v_id = info["id"]
            dur_s = int(info.get("duration") or 0)
            dur_str = f"{dur_s//60}:{dur_s%60:02d}" if dur_s else "0:00"
            thumb = f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
            return {
                "id": v_id,
                "title": info.get("title", query),
                "link": f"https://www.youtube.com/watch?v={v_id}",
                "duration": dur_str,
                "thumbnails": [{"url": thumb}],
            }
    except Exception:
        pass

    if vid:
        return {
            "id": vid,
            "title": f"YouTube Video ({vid})",
            "link": f"https://www.youtube.com/watch?v={vid}",
            "duration": "0:00",
            "thumbnails": [{"url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}],
        }
    return None


async def _search_many(query: str, limit: int = 10) -> list[dict]:
    try:
        s = VideosSearch(query, limit=limit)
        res = await s.next()
        items = res.get("result", [])
        out = []
        for r in items:
            if not r.get("id"):
                continue
            thumb = (
                r["thumbnails"][0]["url"].split("?")[0]
                if r.get("thumbnails")
                else f"https://i.ytimg.com/vi/{r['id']}/hqdefault.jpg"
            )
            out.append({
                "id": r["id"],
                "title": r.get("title", ""),
                "link": r.get("link", f"https://www.youtube.com/watch?v={r['id']}"),
                "duration": r.get("duration", "0:00"),
                "thumbnails": [{"url": thumb}],
            })
        if out:
            return out
    except Exception:
        pass

    vercel_results = await _search_vercel(query, limit=limit)
    if vercel_results:
        return vercel_results

    return []


async def _media_duration(path: str) -> int:
    """Read the actual downloaded file duration when search metadata is missing."""
    if not os.path.exists(path) or not shutil.which("ffprobe"):
        return 0
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        return max(0, int(float(out.decode().strip()))) if out.strip() else 0
    except Exception:
        return 0


async def _probe_media(path: str, require_video: bool) -> bool:
    """Verify that the downloaded file really contains the requested media stream."""
    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        return False
    if not shutil.which("ffprobe"):
        return True
    wanted = "v:0" if require_video else "a:0"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-select_streams", wanted,
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        return proc.returncode == 0 and bool(out.strip())
    except Exception:
        return False


def _cookie_file() -> str | None:
    """Return a writable copy of the YouTube cookies.

    Render Secret Files are mounted read-only. yt-dlp may update/save the
    cookie jar, so never give yt-dlp the /etc/secrets file directly.
    """
    candidates = [
        os.environ.get("YOUTUBE_COOKIES_FILE"),
        "/etc/secrets/cookies.txt",
        "/app/cookies.txt",
        os.path.join(os.getcwd(), "cookies.txt"),
    ]
    source = next(
        (
            path for path in candidates
            if path and os.path.isfile(path) and os.path.getsize(path) > 0
        ),
        None,
    )
    if not source:
        return None

    writable = "/tmp/primebeats_youtube_cookies.txt"
    try:
        if (
            not os.path.isfile(writable)
            or os.path.getmtime(writable) < os.path.getmtime(source)
            or os.path.getsize(writable) == 0
        ):
            import shutil as _shutil
            _shutil.copyfile(source, writable)
            os.chmod(writable, 0o600)
        return writable
    except OSError as exc:
        print(f"[yt-dlp] could not create writable cookie copy: {exc}")
        return None


def _ytdlp_download_sync(video_id: str, is_video: bool, out_dir: str,
                         cookie_file: str | None):
    """Download a local media file with yt-dlp after the Yuki provider fails."""
    import yt_dlp

    target = f"https://www.youtube.com/watch?v={video_id}"
    base_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "outtmpl": os.path.join(out_dir, f"{video_id}.%(ext)s"),
        "restrictfilenames": True,
        "overwrites": False,
    }

    if cookie_file:
        base_opts["cookiefile"] = cookie_file

    # Use an installed JS runtime when available. Recent YouTube extraction
    # can require a runtime for the challenge/player code.
    js_runtimes = {}
    if shutil.which("deno"):
        js_runtimes["deno"] = {}
    if shutil.which("node"):
        js_runtimes["node"] = {}
    if js_runtimes:
        base_opts["js_runtimes"] = js_runtimes

    if is_video:
        base_opts.update({
            "format": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "merge_output_format": "mp4",
        })
    else:
        base_opts.update({
            "format": "bestaudio/best/worst",
        })

    # Different YouTube clients can expose different playable formats.
    clients = (
        {"youtube": {"player_client": ["web"]}},
        {"youtube": {"player_client": ["mweb"]}},
        {"youtube": {"player_client": ["android"]}},
        {"youtube": {"player_client": ["web_embedded"]}},
    )

    errors = []
    for index, extractor_args in enumerate(clients, 1):
        opts = dict(base_opts)
        opts["extractor_args"] = extractor_args
        try:
            print(
                f"[yt-dlp fallback] attempt={index} "
                f"type={'video' if is_video else 'audio'} video_id={video_id} "
                f"cookies={'yes' if cookie_file else 'no'}"
            )
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(target, download=True) or {}
                requested = info.get("requested_downloads") or []
                candidates = []

                for item in requested:
                    path = item.get("filepath") or item.get("_filename")
                    if path:
                        candidates.append(path)

                prepared = info.get("_filename")
                if prepared:
                    candidates.append(prepared)

                # The final merged file is commonly represented by
                # prepare_filename(), so include that path too.
                try:
                    candidates.append(ydl.prepare_filename(info))
                except Exception:
                    pass

                for path in candidates:
                    if path and os.path.isfile(path) and os.path.getsize(path) > 10000:
                        return path

                # Find a matching file if yt-dlp selected/merged a different
                # extension than the metadata filename.
                prefix = os.path.join(out_dir, video_id + ".")
                matches = [
                    os.path.join(out_dir, name)
                    for name in os.listdir(out_dir)
                    if os.path.join(out_dir, name).startswith(prefix)
                    and os.path.isfile(os.path.join(out_dir, name))
                    and os.path.getsize(os.path.join(out_dir, name)) > 10000
                ]
                if matches:
                    matches.sort(key=os.path.getmtime, reverse=True)
                    return matches[0]

        except Exception as exc:
            errors.append(str(exc))
            print(
                f"[yt-dlp fallback] attempt={index} failed for {video_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    raise RuntimeError(
        f"yt-dlp fallback failed for {video_id}: "
        f"{errors[-1] if errors else 'unknown error'}"
    )


async def _download_with_ytdlp(video_id: str, is_video: bool) -> str:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    cookie_file = _cookie_file()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _ytdlp_download_sync,
        video_id,
        is_video,
        DOWNLOAD_DIR,
        cookie_file,
    )


async def download_media(video_id: str, is_video: bool = False) -> str:
    """Download media through Yuki first, then fall back to yt-dlp."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    req_type = "video" if is_video else "audio"

    # Telegram/PyTgCalls supports up to 720p for group-call video.
    qualities = (480, 360) if is_video else (360,)
    session = await get_session()
    last_error = None

    # Yuki is optional: if its endpoint is unavailable (including HTTP 530),
    # continue automatically to the local yt-dlp fallback.
    if API_KEY and API_KEY != "YOUR_API_KEY":
        for quality in qualities:
            ext = "mp4" if is_video else "mp3"
            suffix = f".video{quality}" if is_video else ""
            out_path = os.path.join(DOWNLOAD_DIR, f"{video_id}{suffix}.{ext}")

            if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                if await _probe_media(out_path, is_video):
                    return out_path
                try:
                    os.remove(out_path)
                except OSError:
                    pass

            stream_url = (
                f"{API_URL}/stream/{video_id}?key={API_KEY}"
                f"&type={req_type}&quality={quality}"
            )
            tmp_path = f"{out_path}.tmp.{random.randint(1000, 9999)}"

            try:
                print(
                    f"[Yuki API] requesting {req_type} "
                    f"quality={quality} video_id={video_id}"
                )
                async with session.get(stream_url) as resp:
                    if resp.status == 200:
                        with open(tmp_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(65536):
                                f.write(chunk)

                        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 10000:
                            os.replace(tmp_path, out_path)
                            if await _probe_media(out_path, is_video):
                                print(f"[Yuki API] ready: {out_path}")
                                return out_path
                            last_error = (
                                "provider returned a file without the "
                                "requested media stream"
                            )
                    elif resp.status == 401:
                        last_error = "HTTP 401 (invalid API key)"
                    else:
                        last_error = f"HTTP {resp.status}"
            except Exception as exc:
                last_error = str(exc)
                print(
                    f"[Yuki API] Stream error for {video_id} "
                    f"quality={quality}: {exc}"
                )
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        print(
            f"[Yuki API] unavailable for {video_id} "
            f"({last_error or 'unknown error'}); trying yt-dlp fallback"
        )
    else:
        print("[Yuki API] API key unavailable; using yt-dlp fallback")

    try:
        path = await _download_with_ytdlp(video_id, is_video)
        if await _probe_media(path, is_video):
            print(f"[yt-dlp fallback] ready: {path}")
            return path
        raise RuntimeError("yt-dlp produced a file without the requested media stream")
    except Exception as exc:
        raise RuntimeError(
            f"Yuki API failed ({last_error or 'unavailable'}) and "
            f"yt-dlp fallback failed: {exc}"
        ) from exc


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://www.youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        vid = _extract_video_id(link) if not videoid else link
        return bool(vid)

    async def url(self, message_or_text) -> str | None:
        text = message_or_text.text if hasattr(message_or_text, "text") else str(message_or_text)
        vid = _extract_video_id(text)
        return f"https://www.youtube.com/watch?v={vid}" if vid else None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        clean = _clean_link(link)
        r = await _search_one(clean)
        if not r:
            raise RuntimeError(f"No track details found for: {link}")

        title = r["title"]
        dur_str = r["duration"]
        dur_sec = time_to_seconds(dur_str)
        thumb = r["thumbnails"][0]["url"]
        vid = r["id"]
        _cache_thumb(vid, thumb)
        return title, dur_str, dur_sec, thumb, vid

    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        r = await _search_one(_clean_link(link))
        return r["title"] if r else ""

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        r = await _search_one(_clean_link(link))
        return r["duration"] if r else "0:00"

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        vid = _extract_video_id(link)
        if vid and vid in _thumb_cache:
            return _thumb_cache[vid]
        r = await _search_one(_clean_link(link))
        if r:
            thumb = r["thumbnails"][0]["url"]
            if vid:
                _cache_thumb(vid, thumb)
            return thumb
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        r = await _search_one(_clean_link(link))
        if not r:
            raise RuntimeError(f"No track found for: {link}")
        thumb = r["thumbnails"][0]["url"]
        _cache_thumb(r["id"], thumb)
        return {
            "title": r["title"],
            "link": r["link"],
            "vidid": r["id"],
            "duration_min": r["duration"],
            "thumb": thumb,
        }, r["id"]

    async def playlist(self, link: str, limit: int, user_id: int, videoid: Union[bool, str] = None) -> list[str]:
        if videoid:
            link = self.listbase + link
        clean = _clean_link(link)

        list_id = None
        if "list=" in link:
            m = re.search(r"[?&]list=([0-9A-Za-z_-]+)", link)
            if m:
                list_id = m.group(1)

        targets = [clean]
        if list_id and list_id.startswith("RD"):
            seed_vid = list_id[2:]
            if "_" in seed_vid:
                seed_vid = seed_vid.split("_")[-1]
            elif len(seed_vid) >= 11:
                seed_vid = seed_vid[:11]
            if seed_vid:
                targets.insert(0, f"https://www.youtube.com/watch?v={seed_vid}&list={list_id}")

        try:
            import yt_dlp
            for tgt in targets:
                try:
                    loop = asyncio.get_running_loop()

                    def _extract_pl(url_to_extract):
                        opts = {"extract_flat": True, "quiet": True, "no_warnings": True, "playlistend": limit}
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            info = ydl.extract_info(url_to_extract, download=False) or {}
                            entries = info.get("entries") or []
                            return [
                                f"https://www.youtube.com/watch?v={e['id']}"
                                for e in entries
                                if e and e.get("id")
                            ]

                    res = await loop.run_in_executor(None, _extract_pl, tgt)
                    if res:
                        return res[:limit]
                except Exception:
                    pass
        except ImportError:
            pass

        try:
            plist = Playlist(clean)
            while plist.hasMore():
                await plist.getNext()
                if len(plist.videos) >= limit:
                    break
            if plist.videos:
                return [v["link"] for v in plist.videos[:limit]]
        except Exception:
            pass
        return []

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return [], link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        items = await _search_many(_clean_link(link), limit=10)
        if not items:
            raise RuntimeError(f"No search results for: {link}")
        if query_type >= len(items):
            query_type = 0
        r = items[query_type]
        thumb = r["thumbnails"][0]["url"]
        _cache_thumb(r["id"], thumb)
        return r["title"], r["duration"], thumb, r["id"]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        vid = _extract_video_id(link) or (link if videoid else None)
        if not vid:
            return 0, None
        try:
            path = await download_media(vid, is_video=True)
            return 1, path
        except Exception as e:
            print(f"[video] Error: {e}")
            return 0, None

    async def is_live(self, link: str, videoid: Union[bool, str] = None) -> bool:
        return False

    async def download(
        self,
        link: str,
        mystic=None,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> tuple[str, bool]:
        is_vid = bool(video or songvideo)
        vid = _extract_video_id(link) or link
        path = await download_media(vid, is_video=is_vid)
        return path, True


YouTube = YouTubeAPI()


async def download_song(link: str) -> str:
    vid = _extract_video_id(link) or link
    return await download_media(vid, is_video=False)


async def download_video(link: str) -> str:
    vid = _extract_video_id(link) or link
    return await download_media(vid, is_video=True)


# ---------------------------------------------------------------------------
# PRIME × BEATS compatibility layer
# The uploaded YouTubeAPI is retained above. The current PRIME × BEATS app
# imports these functions from primebeats.youtube, so expose the same API.
# ---------------------------------------------------------------------------

import inspect
from urllib.parse import urlparse

try:
    from .state import Track
except Exception:
    Track = None


def _seconds(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return time_to_seconds(str(value or "0:00"))


def _make_prime_track(info: dict, requested_by: str):
    """Create the project's Track object without assuming one exact signature."""
    if Track is None:
        return info

    url = info.get("link") or f"https://www.youtube.com/watch?v={info.get('id')}"
    duration_str = info.get("duration") or "0:00"
    duration_sec = _seconds(duration_str)
    thumb = (info.get("thumbnails") or [{}])[0].get("url", "")
    vid = info.get("id", "")

    values = {
        "title": info.get("title") or "Unknown",
        "webpage_url": url,
        "requested_by": requested_by or "Unknown",
        "requested_by_id": None,
        "stream_url": None,
        "duration": duration_sec,
        "thumbnail": thumb,
        "video": False,
        "vidid": vid,
        "id": vid,
        "duration_min": duration_str,
        "link": url,
        "thumb": thumb,
    }

    # Build only fields accepted by the installed Track dataclass/class.
    try:
        sig = inspect.signature(Track)
        kwargs = {
            name: values[name]
            for name in sig.parameters
            if name != "self" and name in values
        }
        return Track(**kwargs)
    except Exception:
        # Fallback for positional/simple Track implementations.
        for args in (
            (values["title"], url, requested_by, duration_sec, thumb),
            (values["title"], url, requested_by),
            (values["title"], url),
        ):
            try:
                return Track(*args)
            except Exception:
                pass
        raise RuntimeError("Could not construct PRIME × BEATS Track object")


async def search_results(query: str, limit: int = 8) -> list[dict]:
    """Search using the uploaded YouTube implementation."""
    return await _search_many(query, limit=max(1, int(limit)))


async def resolve(link_or_query: str, requested_by: str = "Unknown",
                  video: bool = False):
    """
    Resolve a YouTube URL/search term and prepare local media through the
    uploaded Yuki API downloader. Local media is passed to PyTgCalls.
    """
    info = await _search_one(_clean_link(str(link_or_query).strip()))
    if not info:
        raise RuntimeError(f"No YouTube result found for: {link_or_query}")

    track = _make_prime_track(info, requested_by)

    # Download once here. download_media() has a persistent per-video cache,
    # so subsequent resolve() calls do not redownload the same media.
    media_path = await download_media(info["id"], is_video=bool(video))
    actual_duration = await _media_duration(media_path)
    metadata_duration = _seconds(info.get("duration"))
    resolved_duration = actual_duration or metadata_duration

    # Track may be a dataclass with fixed fields, so set attributes safely.
    for name, value in (
        ("stream_url", media_path),
        ("title", info.get("title") or "Unknown"),
        ("duration", resolved_duration),
        ("thumbnail", (info.get("thumbnails") or [{}])[0].get("url", "")),
        ("webpage_url", info.get("link")),
        ("video", bool(video)),
    ):
        try:
            setattr(track, name, value)
        except Exception:
            pass

    return track


async def resolve_playlist(link: str, requested_by: str = "Unknown",
                           limit: int = 20) -> list:
    urls = await YouTubeAPI().playlist(link, int(limit), 0)
    result = []
    for url in urls[:int(limit)]:
        try:
            # Playlist import should not download everything immediately.
            info = await _search_one(_clean_link(url))
            if info:
                result.append(_make_prime_track(info, requested_by))
        except Exception:
            continue
    return result


def duration(link_or_value) -> str:
    """Normalize duration to the format expected by the player UI."""
    if isinstance(link_or_value, (int, float)):
        sec = int(link_or_value)
        return f"{sec // 60}:{sec % 60:02d}"

    value = str(link_or_value or "0:00")
    if ":" in value and all(p.isdigit() for p in value.split(":")):
        sec = time_to_seconds(value)
        return f"{sec // 60}:{sec % 60:02d}"
    return value


def topic_seeds(topic: str) -> list[str]:
    topic = (topic or "").strip()
    if not topic:
        return []
    return [
        topic,
        f"{topic} songs",
        f"{topic} music",
        f"{topic} playlist",
    ]


async def discover_topic(topic: str, requested_by: str = "Autoplay",
                         limit: int = 12, exclude=None, round_no: int = 0):
    exclude = {str(x).lower() for x in (exclude or set())}
    found = []
    seen = set()

    seeds = topic_seeds(topic)
    if seeds:
        seed = seeds[int(round_no) % len(seeds)]
    else:
        seed = "music"

    # Use several queries so autoplay remains a real discovery system.
    queries = [seed]
    if len(seeds) > 1:
        queries.append(seeds[(int(round_no) + 1) % len(seeds)])

    for query in queries:
        try:
            rows = await _search_many(query, limit=max(8, int(limit)))
        except Exception:
            rows = []

        for row in rows:
            url = (row.get("link") or "").lower()
            vid = str(row.get("id") or "").lower()
            key = url or vid
            if not key or key in exclude or key in seen:
                continue
            seen.add(key)
            found.append(_make_prime_track(row, requested_by))
            if len(found) >= int(limit):
                return found

    return found


# ---------------------------------------------------------------------------
# PRIME × BEATS compatibility helper
# app.py imports resolve_result from this module. Keep this wrapper compatible
# with search-result dictionaries while reusing the existing resolve() path.
# ---------------------------------------------------------------------------

async def resolve_result(result, requested_by: str = "Unknown",
                         video: bool = False):
    """Resolve a search result (or URL/ID) through the existing resolver."""
    if isinstance(result, dict):
        link = (
            result.get("webpage_url")
            or result.get("url")
            or result.get("link")
            or result.get("id")
        )
    else:
        link = getattr(result, "webpage_url", None) or getattr(result, "link", None)
        if not link:
            link = str(result)

    if not link:
        raise RuntimeError("Search result does not contain a YouTube URL or video ID")

    return await resolve(str(link), requested_by=requested_by, video=video)
