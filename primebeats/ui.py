from __future__ import annotations
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .youtube import duration
from .effects import EFFECTS
import re, time

BRAND = "⚝ 𝐅ᴇᴀʀʟᴇss ꭗ 𝐌ᴜsɪᴄ ᯤ"
POWER = "🚀 ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ"
DONE = "❏ ʀᴇsᴛᴀʀᴛ ʏᴏᴜʀ ʙᴏᴛ — ᴅᴏɴᴇ! ✅"

_SMALL = str.maketrans({
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ',
    'n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'
})
_BOLD = {
    'A':'𝐀','B':'𝐁','C':'𝐂','D':'𝐃','E':'𝐄','F':'𝐅','G':'𝐆','H':'𝐇','I':'𝐈','J':'𝐉','K':'𝐊','L':'𝐋','M':'𝐌',
    'N':'𝐍','O':'𝐎','P':'𝐏','Q':'𝐐','R':'𝐑','S':'𝐒','T':'𝐓','U':'𝐔','V':'𝐕','W':'𝐖','X':'𝐗','Y':'𝐘','Z':'𝐙'
}

def esc(s:str)->str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _word_style(word:str)->str:
    m=re.match(r"([^A-Za-z]*)([A-Za-z])(.*)$", word)
    if not m: return word
    pre, first, rest=m.groups()
    out=pre+_BOLD.get(first.upper(), first)
    for ch in rest:
        out += _SMALL.get(ch.lower(), ch) if ch.isalpha() else ch
    return out

def style_text(text:str)->str:
    if not text:
        return text
    parts=re.split(r'(<code>.*?</code>|https?://\S+|t\.me/\S+|<[^>]+>|&(?:amp|lt|gt|quot|#\d+);)', text, flags=re.S|re.I)
    out=[]
    for part in parts:
        low=part.lower()
        if low.startswith('<code>') and low.endswith('</code>'):
            out.append(part)
        elif (part.startswith('<') and part.endswith('>')) or (low.startswith('&') and low.endswith(';')) or low.startswith('http://') or low.startswith('https://') or low.startswith('t.me/'):
            out.append(part)
        else:
            out.append(re.sub(r"[A-Za-z][A-Za-z'’+×/-]*", lambda m:_word_style(m.group(0)), part))
    return ''.join(out)

def frame(title:str, lines:list[str], footer:bool=True)->str:
    body="\n".join(lines)
    tail=f"\n\n{DONE}" if footer else ""
    return f"<b>╭━━━━━━━━━━━━━━━━━━━━╮</b>\n<b>🔸 {style_text(title)}</b>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n{POWER}\n{body}{tail}\n\n{BRAND}"

def links(cfg):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 𝐎ᴡɴᴇʀ",url="https://t.me/Prime_Fearless_45"),
         InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ",url="https://t.me/SPARK_X_NETWORK")],
        [InlineKeyboardButton("📢 𝐂ʜᴀɴɴᴇʟ",url="https://t.me/SPARK_X_NETWORK_OP"),
         InlineKeyboardButton("⚡ 𝐎ғғɪᴄɪᴀʟ",url="https://t.me/Prime_Arrived")]
    ])

def home_keyboard(cfg):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 𝐏ʟᴀʏ",callback_data="help:play"),InlineKeyboardButton("📜 𝐐ᴜᴇᴜᴇ",callback_data="queue")],
        [InlineKeyboardButton("▶️ 𝐍ᴏᴡ 𝐏ʟᴀʏɪɴɢ",callback_data="now"),InlineKeyboardButton("♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ",callback_data="auto")],
        [InlineKeyboardButton("🎙️ 𝐒ᴛᴀʀᴛ 𝐕𝐂",callback_data="startvc")],
        [InlineKeyboardButton("⏸️ 𝐏ᴀᴜsᴇ",callback_data="pause"),InlineKeyboardButton("⏭️ 𝐒ᴋɪᴘ",callback_data="skip"),InlineKeyboardButton("⏹️ sᴛᴏᴘ",callback_data="stop")],
        [InlineKeyboardButton("🔀 sʜᴜғғʟᴇ",callback_data="shuffle"),InlineKeyboardButton("🔁 𝐋ᴏᴏᴘ",callback_data="loop")],
        [InlineKeyboardButton("🔉 ᴠᴏʟ −",callback_data="voldown"),InlineKeyboardButton("🔊 ᴠᴏʟ +",callback_data="volup"),InlineKeyboardButton("🔇 ᴍᴜᴛᴇ",callback_data="mute")],
        [InlineKeyboardButton("🎛️ 𝐀ᴜᴅɪᴏ 𝐄ғғᴇᴄᴛs",callback_data="effects:0"),InlineKeyboardButton("📖 𝐇ᴇʟᴘ",callback_data="help"),InlineKeyboardButton("⚡ 𝐏ɪɴɢ",callback_data="ping")],
        [InlineKeyboardButton("🌐 sᴜᴘᴘᴏʀᴛ & 𝐋ɪɴᴋs",callback_data="links")]
    ])

def player_keyboard():
    # Telegram inline keyboards do not expose arbitrary background colours to
    # bots; button colours follow the Telegram client/theme.  We therefore
    # use colour-like visual grouping via icons, spacing and button labels,
    # while keeping the existing callback_data contract intact.
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸  PAUSE", callback_data="pause"),
            InlineKeyboardButton("⏹  STOP", callback_data="stop"),
        ],
        [
            InlineKeyboardButton("«  −20s", callback_data="seek:-20"),
            InlineKeyboardButton("🔄  REFRESH", callback_data="refresh"),
            InlineKeyboardButton("+20s  »", callback_data="seek:20"),
        ],
        [
            InlineKeyboardButton("⏭  SKIP TO NEXT", callback_data="skip"),
            InlineKeyboardButton("⚡ SPEED / MODE", callback_data="mode"),
        ],
        [
            InlineKeyboardButton("🎛  AUDIO EFFECTS", callback_data="effects:0"),
        ],
        [
            InlineKeyboardButton("🔊  VOLUME −", callback_data="voldown"),
            InlineKeyboardButton("🔊  VOLUME +", callback_data="volup"),
            InlineKeyboardButton("🔇  MUTE", callback_data="mute"),
        ],
        [
            InlineKeyboardButton("📜  QUEUE", callback_data="queue"),
            InlineKeyboardButton("♾  AUTOPLAY", callback_data="auto"),
            InlineKeyboardButton("🔀  SHUFFLE", callback_data="shuffle"),
        ],
        [
            InlineKeyboardButton("🔁  LOOP", callback_data="loop"),
            InlineKeyboardButton("🧹  CLEAR", callback_data="clear"),
        ],
    ])

def effects_keyboard(page=0):
    keys=list(EFFECTS.items()); per=10
    chunk=keys[page*per:(page+1)*per]; rows=[]
    for i in range(0,len(chunk),2):
        rows.append([InlineKeyboardButton(style_text(label),callback_data=f"effect:{k}") for k,(label,_) in chunk[i:i+2]])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("🟣 « 𝐏ʀᴇᴠ",callback_data=f"effects:{page-1}"))
    if (page+1)*per<len(keys): nav.append(InlineKeyboardButton("🔵 𝐍ᴇxᴛ »",callback_data=f"effects:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🟢 ↩ 𝐁ᴀᴄᴋ ᴛᴏ 𝐏ʟᴀʏᴇʀ",callback_data="now")])
    return InlineKeyboardMarkup(rows)

def welcome(cfg,user):
    return (
        f"<b>╭━━━〔 {BRAND} 〕━━━╮</b>\n"
        f"<b>┃ ⚡ {esc(cfg.bot_name)}</b>\n"
        f"<b>┃ {POWER}</b>\n"
        "<b>┃ 🎧 𝐀ᴜᴅɪᴏ • 🎥 𝐕ɪᴅᴇᴏ • ♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ</b>\n"
        "<b>┃ 🎛 39+ 𝐀ᴜᴅɪᴏ 𝐅𝐗 • ⚡ 𝐔ʟᴛʀᴀ 𝐅ᴀsᴛ</b>\n"
        f"<b>┃ 👤 𝐖ᴇʟᴄᴏᴍᴇ, {esc(user)}</b>\n"
        "<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        "<blockquote><b>⚡ 𝐅𝐄𝐀𝐑𝐋𝐄𝐒𝐒 𝟒𝟓 𝐏𝐑𝐎 𝐄𝐍𝐆𝐈𝐍𝐄</b>\n"
        "🎵 𝐈ɴsᴛᴀɴᴛ ᴘʟᴀʏ • 🎙 𝐒ᴍᴏᴏᴛʜ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ\n"
        "🚀 𝐘ᴜᴋɪ ᴘʀɪᴍᴀʀʏ • 🔁 ʏᴛ-ᴅʟᴘ ғᴀʟʟʙᴀᴄᴋ</blockquote>\n\n"
        "<b>🚀 𝐐ᴜɪᴄᴋ sᴛᴀʀᴛ</b>\n"
        "<code>/play O Maahi</code> • 𝐀ᴜᴅɪᴏ\n"
        "<code>/vplay music video</code> • 𝐕ɪᴅᴇᴏ\n"
        "<code>/autoplay Romantic Hindi Songs</code>\n"
        "<code>/radio Romantic Hindi Songs</code> • ᴄᴏɴᴛɪɴᴜᴏᴜs ᴅɪsᴄᴏᴠᴇʀʏ"
    )

def progress_bar(p, width=14):
    if not p.current or not p.current.duration or not p.started_at: return "LIVE"
    elapsed=max(0,int(time.monotonic()-p.started_at)); elapsed=min(elapsed,int(p.current.duration))
    ratio=min(1,elapsed/max(1,p.current.duration)); filled=int(width*ratio)
    return "━"*filled+"●"+"─"*(width-filled)+f" {elapsed//60}:{elapsed%60:02d}/{duration(p.current.duration)}"

def player_text(p,name):
    auto = "ON • " + esc(p.autoplay_topic) if p.autoplay and p.autoplay_topic else ("ON" if p.autoplay else "OFF")
    effect = getattr(p, "effect", "normal")
    effect_name = EFFECTS.get(effect, ("Normal", ""))[0]

    if not p.current:
        return (
            f"<b>{PANEL_TOP}</b>\n"
            f"<b>┃ 🎧 {style_text('NOW STREAMING')}</b>\n"
            f"<b>{PANEL_MID}</b>\n"
            "┃ 🟢 <b>PLAYER READY</b>\n"
            f"┃ ♾️ Autoplay: <code>{auto}</code>\n"
            f"┃ 🎛 FX: <code>{esc(effect_name)}</code>\n"
            f"┃ 📚 Queue: <code>{len(p.queue)}</code>\n"
            f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
        )

    t = p.current
    mode = "🎥 VIDEO" if getattr(t, "video", False) else "🎧 AUDIO"
    state = "⏸️ PAUSED" if getattr(p, "paused", False) else "▶️ PLAYING"
    try:
        left = remaining_seconds(p)
    except Exception:
        left = 0

    # Telegram's coloured-looking quote card. The actual quote colour is
    # selected by the Telegram client/theme; the bot supplies the blockquote.
    quote = (
        "<blockquote>"
        f"<b>🎧 Now Streaming</b>  ❯❯\n"
        f"🎵 <b>Title:</b> <i>{esc(_clip(t.title, 90))}</i>\n"
        f"⏱ <b>Duration:</b> <code>{duration(t.duration)}</code>\n"
        f"⏳ <b>Remaining:</b> <code>{duration(left)}</code>\n"
        f"👤 <b>Requested by:</b> {esc(_clip(t.requested_by, 55))}\n"
        f"🎧 <b>Mode:</b> <code>{mode}</code>\n"
        f"🔊 <b>Volume:</b> <code>{p.volume}%</code>\n"
        f"🎛 <b>Effects:</b> <code>{esc(effect_name)}</code>\n"
        f"🔁 <b>Loop:</b> <code>{'ON' if p.loop else 'OFF'}</code>  •  "
        f"♾️ <b>Autoplay:</b> <code>{auto}</code>"
        "</blockquote>"
    )

    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {state} • {mode}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"🎵 <b>{esc(_clip(t.title, 78))}</b>\n"
        f"⏱ <code>{duration(t.duration)}</code> • "
        f"⏳ <code>{duration(left)} left</code>\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n"
        f"{quote}\n\n"
        f"{POWER}\n{BRAND}"
    )

def help_text(name):
    return f"""<b>{BRAND}</b>\n\n{POWER}\n\n<b>🎧 𝐏ʟᴀʏʙᴀᴄᴋ</b>\n<code>/play</code> <code>/vplay</code> <code>/pause</code> <code>/resume</code> <code>/skip</code> <code>/stop</code>\n<code>/queue</code> <code>/now</code> <code>/clear</code> <code>/remove 2</code> <code>/jump 3</code>\n<code>/shuffle</code> <code>/loop</code> <code>/volume 0-200</code> <code>/mute</code> <code>/unmute</code>\n\n<b>♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ</b>\n<code>/autoplay Romantic Hindi Songs</code>\n<code>/radio Romantic Hindi Songs</code> • ᴄᴏɴᴛɪɴᴜᴏᴜs ᴅɪsᴄᴏᴠᴇʀʏ\n<code>/discover topic</code> • ғɪʟʟ ғʀᴇsʜ ʀᴇsᴜʟᴛs\n\n<b>🎛 𝐄ғғᴇᴄᴛs</b>\n<code>/effect bass_boost</code> • 30+ ᴘʀᴇsᴇᴛs\n\n<b>🛠 𝐃ɪsᴄᴏᴠᴇʀʏ & 𝐓ᴏᴏʟs</b>\n<code>/search song</code> <code>/discover topic</code> <code>/radio topic</code>\n<code>/ping</code> <code>/stats</code> <code>/history</code> <code>/health</code> <code>/settings</code> <code>/features</code>\n\n<b>👑 𝐎ᴡɴᴇʀ</b>\n<code>/approvegc</code> <code>/revoke_gc</code> <code>/clone</code> <code>/clones</code>\n\n<blockquote>🛡 ᴘʟᴀʏʙᴀᴄᴋ ɪs ʟᴏᴄᴋᴇᴅ ᴜɴᴛɪʟ ᴛʜᴇ ᴍᴀɪɴ ᴏᴡɴᴇʀ ᴀᴘᴘʀᴏᴠᴇs ᴛʜᴇ ɢʀᴏᴜᴘ.\n⚡ ᴀᴜᴛᴏᴘʟᴀʏ ᴜsᴇs ᴄᴜʀᴀᴛᴇᴅ + ʟɪᴠᴇ ᴅɪsᴄᴏᴠᴇʀʏ ᴀɴᴅ ᴋᴇᴇᴘs ʀᴇғɪʟʟɪɴɢ ᴛʜᴇ ǫᴜᴇᴜᴇ.\n\n{DONE}</blockquote>"""
# ============================================================================
# FEARLESS PRO UI EXTENSION
# ============================================================================
# This section intentionally keeps callback_data compatible with the existing
# app.py.  It adds reusable visual panels, richer help/status copy, compact
# typography helpers, and UI presets without inventing callbacks that app.py
# does not handle.
# ============================================================================

UI_VERSION = "FEARLESS PRO UI 5.0"
UI_SIGNATURE = "FEARLESS × MUSIC • PROFESSIONAL TELEGRAM VOICE PLAYER"

PANEL_TOP = "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮"
PANEL_MID = "├━━━━━━━━━━━━━━━━━━━━━━━━━━━━┤"
PANEL_BOTTOM = "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"

STATUS_READY = "🟢 READY"
STATUS_PLAYING = "▶️ PLAYING"
STATUS_PAUSED = "⏸️ PAUSED"
STATUS_IDLE = "⚪ IDLE"
STATUS_LOADING = "🟡 LOADING"
STATUS_ERROR = "🔴 ERROR"

def _safe(value, fallback="—"):
    value = "" if value is None else str(value).strip()
    return value if value else fallback

def _clip(value, limit=60):
    value = _safe(value)
    return value if len(value) <= limit else value[:max(1, limit-1)] + "…"

def _num(value, fallback=0):
    try:
        return int(value)
    except Exception:
        return fallback

def _pct(value):
    return max(0, min(100, _num(value, 0)))

def meter(value, width=12, left="━", right="─", marker="●"):
    value = _pct(value)
    width = max(4, int(width))
    filled = round(width * value / 100)
    filled = max(0, min(width, filled))
    return left * filled + marker + right * (width - filled)

def volume_meter(volume):
    value = _pct(volume)
    return f"{meter(value, 10)} <code>{value}%</code>"

def queue_meter(count, maximum=10):
    count = max(0, _num(count))
    maximum = max(1, _num(maximum, 10))
    ratio = min(100, round(count * 100 / maximum))
    return f"{meter(ratio, 10)} <code>{count}/{maximum}</code>"

def status_line(label, value, icon="•"):
    return f"{icon} <b>{esc(_safe(label))}</b>  <code>{esc(_safe(value))}</code>"

def info_panel(title, *lines, footer=True):
    body = "\n".join(str(x) for x in lines if x is not None)
    tail = f"\n\n{DONE}" if footer else ""
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {style_text(_safe(title))}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"{body}{tail}\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def loading_text(action="CONNECTING"):
    action = _safe(action, "CONNECTING").upper()
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 🟡 {style_text(action)}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        "┃ ▰▰▰▰▰▰▱▱▱▱  <code>PROCESSING…</code>\n"
        "┃ ⚡ Preparing the fastest available route\n"
        "┃ 🎧 Audio engine • YouTube resolver • Voice Chat\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def searching_text(query):
    q = esc(_clip(query, 80))
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 🔎 {style_text('PRIME SEARCH')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 🎵 Query: <code>{q}</code>\n"
        "┃ ⚡ Searching high-speed sources…\n"
        "┃ 🧠 Selecting the most relevant result\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}"
    )

def resolving_text(title="Unknown", video=False):
    media = "🎥 VIDEO" if video else "🎧 AUDIO"
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 🟡 {style_text('STREAM PREPARING')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ {media}\n"
        f"┃ 🎵 <b>{esc(_clip(title, 70))}</b>\n"
        "┃ ⚡ Connecting to the media route…\n"
        "┃ 🚀 Voice Chat engine is being prepared\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def success_text(title, duration_text="0:00", mode="AUDIO"):
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 🟢 {style_text('PLAYBACK STARTED')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 🎵 <b>{esc(_clip(title, 72))}</b>\n"
        f"┃ 🎧 Mode: <code>{esc(mode)}</code>\n"
        f"┃ ⏱ Duration: <code>{esc(duration_text)}</code>\n"
        "┃ ⚡ Stream connected successfully\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def error_text(title="Playback Error", detail="Please try again."):
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 🔴 {style_text(_safe(title))}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ ⚠️ <code>{esc(_clip(detail, 180))}</code>\n"
        "┃ 🔄 The fallback route can be retried safely.\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{BRAND}"
    )

def queue_header(count=0):
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 📜 {style_text('SMART QUEUE')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 📚 Tracks waiting: <code>{max(0, _num(count))}</code>\n"
        f"┃ {queue_meter(count)}\n"
        f"<b>{PANEL_BOTTOM}</b>"
    )

def now_playing_header(title, artist="", duration_text="0:00"):
    artist = f"\n┃ 👤 <b>{esc(_clip(artist, 55))}</b>" if artist else ""
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ ▶️ {style_text('NOW PLAYING')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 🎵 <b>{esc(_clip(title, 70))}</b>{artist}\n"
        f"┃ ⏱ <code>{esc(duration_text)}</code>\n"
        f"<b>{PANEL_BOTTOM}</b>"
    )

def settings_text(p=None):
    if p is None:
        return info_panel(
            "PLAYER SETTINGS",
            "┃ 🔊 Volume: <code>—</code>",
            "┃ 🎛 FX: <code>Normal</code>",
            "┃ 🔁 Loop: <code>OFF</code>",
            "┃ ♾️ Autoplay: <code>OFF</code>",
            "┃ ⚡ Speed: <code>1.00x</code>",
        )
    effect = getattr(p, "effect", "normal")
    effect_name = EFFECTS.get(effect, ("Normal", ""))[0]
    auto = "ON" if getattr(p, "autoplay", False) else "OFF"
    loop = "ON" if getattr(p, "loop", False) else "OFF"
    volume = _pct(getattr(p, "volume", 100))
    speed = getattr(p, "speed", 1.0)
    try:
        speed = float(speed)
    except Exception:
        speed = 1.0
    return info_panel(
        "PLAYER SETTINGS",
        f"┃ 🔊 Volume: <code>{volume}%</code>",
        f"┃ {volume_meter(volume)}",
        f"┃ 🎛 FX: <code>{esc(effect_name)}</code>",
        f"┃ 🔁 Loop: <code>{loop}</code>",
        f"┃ ♾️ Autoplay: <code>{auto}</code>",
        f"┃ ⚡ Speed: <code>{speed:.2f}x</code>",
    )

def features_text():
    return f"""<b>{BRAND}</b>

{POWER}

<b>╭━━〔 ⚡ CORE ENGINE 〕━━╮</b>
┃ 🎧 High-speed audio playback
┃ 🎥 Video Voice Chat playback
┃ 🔎 Smart YouTube search
┃ 📚 Queue management
┃ 🔀 Shuffle + 🔁 Loop
┃ ♾️ Topic-based autoplay
┃ 🎛 Multi-preset audio effects
┃ 🔊 Volume control
┃ ⏱ Playback position / remaining time
┃ 🧠 Automatic resolver fallback
<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>

<b>╭━━〔 🎛 CONTROL CENTER 〕━━╮</b>
┃ ▶️ Play / Pause / Resume
┃ ⏭ Skip / ⏮ Previous
┃ ⏪ Seek backward / ⏩ Seek forward
┃ 📜 Queue / Now Playing
┃ 🧹 Clear queue
┃ 🔀 Shuffle queue
┃ 🔁 Repeat current track
┃ 🔇 Mute / volume adjustment
<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>

<b>╭━━〔 ♾️ DISCOVERY 〕━━╮</b>
┃ 🎵 Search by song or artist
┃ 📻 Radio-style continuous playback
┃ ♾️ Autoplay by topic
┃ 🔥 Fresh topic discovery
┃ 🎯 Result selection before playback
<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>

<blockquote>{DONE}</blockquote>"""

def playback_help_text():
    return f"""<b>{BRAND}</b>

<b>🎧 PLAYBACK COMMANDS</b>
<code>/play song name</code>
<code>/vplay video name</code>
<code>/pause</code>
<code>/resume</code>
<code>/skip</code>
<code>/stop</code>
<code>/queue</code>
<code>/now</code>
<code>/nleft</code>

<b>📚 QUEUE CONTROL</b>
<code>/clear</code>
<code>/remove 2</code>
<code>/jump 3</code>
<code>/shuffle</code>
<code>/loop</code>

<b>🔊 AUDIO CONTROL</b>
<code>/volume 100</code>
<code>/mute</code>
<code>/unmute</code>
<code>/effect bass_boost</code>

<b>♾️ DISCOVERY</b>
<code>/autoplay Romantic Hindi Songs</code>
<code>/radio Romantic Hindi Songs</code>
<code>/discover topic</code>

{POWER}"""

def owner_help_text():
    return f"""<b>{BRAND}</b>

<b>👑 OWNER CONTROL</b>
<code>/approvegc</code> — approve a group
<code>/revoke_gc</code> — revoke group access
<code>/clone</code> — clone management
<code>/clones</code> — show active clones

<b>🛡 ACCESS</b>
Playback approval remains controlled by the application's owner
approval system. Commands and callbacks still use the existing
permission checks in <code>app.py</code>.

{DONE}"""

def tools_help_text():
    return f"""<b>{BRAND}</b>

<b>🛠 TOOLS & STATUS</b>
<code>/search song</code>
<code>/discover topic</code>
<code>/radio topic</code>
<code>/ping</code>
<code>/stats</code>
<code>/history</code>
<code>/health</code>
<code>/settings</code>
<code>/features</code>

<b>⚡ PERFORMANCE</b>
• Fast search path
• Direct streaming when available
• Downloader fallback when required
• Thumbnail-aware player messages
• Voice Chat playback controls
• Queue state preserved by the player store

{POWER}"""

def compact_player_text(p, name=""):
    """Compact player card for messages where a shorter caption is useful."""
    if not getattr(p, "current", None):
        return (
            f"<b>{BRAND}</b>\n"
            f"🟢 <b>PLAYER READY</b>\n"
            f"📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>\n"
            f"🔊 Volume: <code>{_pct(getattr(p, 'volume', 100))}%</code>\n"
            f"{POWER}"
        )
    t = p.current
    state = STATUS_PAUSED if getattr(p, "paused", False) else STATUS_PLAYING
    media = "VIDEO" if getattr(t, "video", False) else "AUDIO"
    return (
        f"<b>{BRAND}</b>\n"
        f"{state} • <code>{media}</code>\n"
        f"🎵 <b>{esc(_clip(t.title, 65))}</b>\n"
        f"⏱ <code>{duration(getattr(t, 'duration', 0))}</code>\n"
        f"🔊 <code>{_pct(getattr(p, 'volume', 100))}%</code> • "
        f"📚 <code>{len(getattr(p, 'queue', []))}</code>\n"
        f"{POWER}"
    )

def search_result_hint():
    return (
        "<blockquote>▶ Play • ⏭ Play Next • ➕ Add to Queue\n"
        "Use the result buttons to choose exactly what should play.</blockquote>"
    )

def footer_text():
    return f"{POWER}\n\n{BRAND}\n<code>{UI_VERSION}</code>"

# Additional visual presets. These are plain text helpers so they never create
# unsupported callback_data in the existing application.
VISUAL_PRESETS = {
    "home": "HOME / PLAYER / DISCOVERY",
    "player": "LIVE PLAYER / QUEUE / CONTROLS",
    "effects": "AUDIO EFFECT LAB / PRESETS",
    "search": "PRIME SEARCH / RESULT SELECTOR",
    "status": "ENGINE STATUS / PERFORMANCE",
    "owner": "OWNER CONTROL / ACCESS",
}

def visual_preset(name="home"):
    key = str(name or "home").lower()
    label = VISUAL_PRESETS.get(key, VISUAL_PRESETS["home"])
    return info_panel(
        label,
        "┃ ⚡ FAST ROUTE: ACTIVE",
        "┃ 🎧 AUDIO ENGINE: READY",
        "┃ 🎙️ VOICE CHAT: CONTROLLED BY PLAYER",
        "┃ 📚 QUEUE: SMART",
        "┃ 🎛 FX: AVAILABLE",
    )

# Keep the module's public surface explicit and easy to inspect.
__all__ = [
    "BRAND", "POWER", "DONE",
    "esc", "style_text", "frame", "links",
    "home_keyboard", "player_keyboard", "effects_keyboard",
    "welcome", "progress_bar", "remaining_seconds", "remaining_text",
    "player_text", "help_text",
    "meter", "volume_meter", "queue_meter", "status_line",
    "info_panel", "loading_text", "searching_text", "resolving_text",
    "success_text", "error_text", "queue_header", "now_playing_header",
    "settings_text", "features_text", "playback_help_text",
    "owner_help_text", "tools_help_text", "compact_player_text",
    "search_result_hint", "footer_text", "visual_preset",
]


# ============================================================================
# EXTENDED DOCUMENTATION / MICRO-CARDS
# ============================================================================
# These reusable text blocks are intentionally kept in ui.py so the bot can
# expose richer help/status cards later without changing its playback engine.
# They do not register handlers and therefore cannot interfere with app.py.

COMMAND_CARDS = {
    "play": """<b>🎧 PLAY</b>
<code>/play &lt;song name&gt;</code>
Searches for a track and sends it to the current player.
For a direct YouTube URL, use the same command with the URL.
The player keeps the queue and starts the next item automatically.""",

    "video": """<b>🎥 VPLAY</b>
<code>/vplay &lt;video name&gt;</code>
Requests video playback through the Voice Chat player.
Video playback uses the same queue and player controls as audio.""",

    "queue": """<b>📜 SMART QUEUE</b>
<code>/queue</code> — view queued tracks
<code>/remove 2</code> — remove a queue position
<code>/jump 3</code> — jump to a queue position
<code>/clear</code> — clear waiting tracks
<code>/shuffle</code> — randomize waiting tracks""",

    "controls": """<b>🎚 PLAYER CONTROLS</b>
<code>/pause</code> — pause current media
<code>/resume</code> — resume playback
<code>/skip</code> — move to the next track
<code>/stop</code> — stop the player
<code>/now</code> — refresh the player card
<code>/nleft</code> — show remaining time
<code>/loop</code> — toggle current-track loop""",

    "volume": """<b>🔊 VOLUME</b>
<code>/volume 100</code>
<code>/mute</code>
<code>/unmute</code>
The inline player also provides quick volume controls.
The displayed value is kept inside the player's configured range.""",

    "effects": """<b>🎛 AUDIO EFFECT LAB</b>
<code>/effect &lt;preset&gt;</code>
Choose an available preset from the inline Effects panel.
The player reads the application's existing EFFECTS registry, so this
UI never invents effect identifiers that the engine does not know.""",

    "autoplay": """<b>♾️ AUTOPLAY</b>
<code>/autoplay Romantic Hindi Songs</code>
Keeps discovering tracks around the selected topic.
The topic is shown in the player card when active.""",

    "radio": """<b>📻 RADIO MODE</b>
<code>/radio Romantic Hindi Songs</code>
Starts topic-based continuous discovery using the application's radio
implementation. Queue controls remain available while the player runs.""",

    "discover": """<b>🔎 DISCOVER</b>
<code>/discover topic</code>
Fills the discovery flow with fresh results.
Use the result selector to play immediately, play next, or queue a result.""",

    "search": """<b>🔍 SEARCH</b>
<code>/search song name</code>
Shows a paginated result selector.
▶ plays a result, ⏭ places it next, and ➕ adds it to the queue.
Expired result pages are rejected by the application callback layer.""",

    "status": """<b>⚡ STATUS</b>
<code>/ping</code>
<code>/stats</code>
<code>/health</code>
Use these to inspect bot responsiveness and runtime state.
The UI is presentation-only; status calculations remain in app.py.""",

    "history": """<b>🕘 HISTORY</b>
<code>/history</code>
Shows playback history supplied by the application.
Track metadata remains escaped before being placed in Telegram HTML.""",

    "settings": """<b>⚙️ SETTINGS</b>
<code>/settings</code>
Player preferences can include volume, effect, loop, autoplay and speed.
The UI reads attributes defensively so missing optional state does not
cause a rendering crash.""",

    "features": """<b>✨ FEATURES</b>
<code>/features</code>
Displays the available feature categories without changing the underlying
feature registry.""",

    "approval": """<b>🛡 GROUP APPROVAL</b>
<code>/approvegc</code>
<code>/revoke_gc</code>
Playback access is controlled by the application's existing approval
system. UI buttons do not bypass owner or administrator checks.""",

    "clone": """<b>👑 CLONE MANAGEMENT</b>
<code>/clone</code>
<code>/clones</code>
Clone operations remain handled by the application's CloneManager.
This module only supplies presentation text.""",
}

def command_card(command):
    key = str(command or "").strip().lower().lstrip("/")
    return COMMAND_CARDS.get(
        key,
        info_panel("COMMAND NOT FOUND",
                   f"┃ Requested: <code>{esc(_clip(command, 50))}</code>",
                   "┃ Use <code>/help</code> to see supported command groups.")
    )

def command_index():
    groups = [
        ("🎧", "Playback", "/play • /vplay • /pause • /resume • /skip • /stop"),
        ("📚", "Queue", "/queue • /remove • /jump • /clear • /shuffle • /loop"),
        ("🔊", "Audio", "/volume • /mute • /unmute • /effect"),
        ("♾️", "Discovery", "/autoplay • /radio • /discover • /search"),
        ("⚡", "Status", "/ping • /stats • /health • /history"),
        ("⚙️", "Settings", "/settings • /features"),
        ("👑", "Owner", "/approvegc • /revoke_gc • /clone • /clones"),
    ]
    rows = [
        f"┃ {icon} <b>{esc(title)}</b>\n┃ <code>{esc(commands)}</code>"
        for icon, title, commands in groups
    ]
    return info_panel("COMMAND INDEX", *rows)

def engine_card(p=None):
    queue_count = len(getattr(p, "queue", [])) if p is not None else 0
    current = getattr(p, "current", None) if p is not None else None
    playing = bool(current) and not bool(getattr(p, "paused", False))
    paused = bool(current) and bool(getattr(p, "paused", False))
    state = STATUS_PLAYING if playing else STATUS_PAUSED if paused else STATUS_READY
    volume = _pct(getattr(p, "volume", 100)) if p is not None else 100
    effect = getattr(p, "effect", "normal") if p is not None else "normal"
    effect_name = EFFECTS.get(effect, ("Normal", ""))[0]
    return info_panel(
        "ENGINE STATUS",
        f"┃ 🎙️ Player: <code>{state}</code>",
        f"┃ 🔊 Volume: <code>{volume}%</code>  {meter(volume, 8)}",
        f"┃ 📚 Queue: <code>{queue_count}</code>",
        f"┃ 🎛 FX: <code>{esc(effect_name)}</code>",
        "┃ ⚡ Resolver: <code>FAST + FALLBACK</code>",
        "┃ 🖼 Thumbnails: <code>ENABLED WHEN AVAILABLE</code>",
    )

def autoplay_card(p=None):
    enabled = bool(getattr(p, "autoplay", False)) if p is not None else False
    topic = getattr(p, "autoplay_topic", "") if p is not None else ""
    topic_text = esc(_clip(topic, 70)) if topic else "No topic selected"
    state = "ON" if enabled else "OFF"
    return info_panel(
        "AUTOPLAY CENTER",
        f"┃ ♾️ Status: <code>{state}</code>",
        f"┃ 🎯 Topic: <code>{topic_text}</code>",
        "┃ 🔎 Discovery: <code>CURATED + LIVE</code>",
        "┃ 📚 Queue: <code>AUTO REFILL</code>",
    )

def effect_catalog(page=0):
    items = list(EFFECTS.items())
    per_page = 12
    page = max(0, _num(page))
    total = max(1, (len(items) + per_page - 1) // per_page)
    page = min(page, total - 1)
    chunk = items[page * per_page:(page + 1) * per_page]
    lines = [
        f"┃ 🎛 <code>{esc(_safe(label))}</code> • <code>{esc(key)}</code>"
        for key, (label, _) in chunk
    ]
    lines.append(f"┃ 📄 Page <code>{page + 1}/{total}</code>")
    return info_panel("EFFECT CATALOG", *lines)

def queue_card(p, page=0, per=8):
    queue = list(getattr(p, "queue", []) or [])
    per = max(1, min(12, _num(per, 8)))
    total = max(1, (len(queue) + per - 1) // per)
    page = max(0, min(_num(page), total - 1))
    chunk = queue[page * per:(page + 1) * per]
    if not chunk:
        return info_panel("SMART QUEUE",
                          "┃ 📭 <b>Queue is empty.</b>",
                          "┃ Add a track with <code>/play song</code>.")
    lines = []
    for idx, track in enumerate(chunk, page * per + 1):
        title = _clip(getattr(track, "title", "Unknown"), 55)
        dur = duration(getattr(track, "duration", 0))
        lines.append(f"┃ <code>{idx:02}</code> • <b>{esc(title)}</b> • <code>{dur}</code>")
    lines.append(f"┃ 📄 Page <code>{page + 1}/{total}</code>")
    return info_panel("SMART QUEUE", *lines)

def request_card(user, query, mode="audio"):
    media = "🎥 VIDEO" if str(mode).lower() == "video" else "🎧 AUDIO"
    return info_panel(
        "PLAY REQUEST",
        f"┃ 👤 User: <b>{esc(_clip(user, 45))}</b>",
        f"┃ {media}",
        f"┃ 🔎 Query: <code>{esc(_clip(query, 80))}</code>",
        "┃ ⚡ Resolving the fastest usable stream…",
    )

def track_card(track, p=None):
    title = getattr(track, "title", "Unknown")
    by = getattr(track, "requested_by", "Unknown")
    dur = duration(getattr(track, "duration", 0))
    mode = "VIDEO" if getattr(track, "video", False) else "AUDIO"
    queue_count = len(getattr(p, "queue", [])) if p is not None else 0
    return info_panel(
        "TRACK DETAILS",
        f"┃ 🎵 <b>{esc(_clip(title, 72))}</b>",
        f"┃ 👤 {esc(_clip(by, 50))}",
        f"┃ 🎧 Mode: <code>{mode}</code>",
        f"┃ ⏱ Duration: <code>{dur}</code>",
        f"┃ 📚 Waiting: <code>{queue_count}</code>",
    )

def announcement_card(title, subtitle="", icon="⚡"):
    subtitle = f"\n┃ {esc(_clip(subtitle, 100))}" if subtitle else ""
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {icon} {style_text(_clip(title, 70))}</b>\n"
        f"<b>{PANEL_MID}</b>{subtitle}\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def divider():
    return "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Extended copy kept as data rather than handlers. This makes the module
# useful for future help screens while remaining a drop-in ui.py today.
UI_COPY = {
    "welcome_tagline": "A fast, polished Telegram Voice Chat music experience.",
    "search_tagline": "Find • Select • Play Next • Queue",
    "player_tagline": "Control playback without leaving the player card.",
    "effects_tagline": "Tune the current track with the application's effect presets.",
    "queue_tagline": "Keep your next tracks organized and ready.",
    "autoplay_tagline": "Let the discovery engine refill the queue around a topic.",
    "performance_tagline": "Fast resolver path with a safe fallback route.",
    "privacy_tagline": "UI text escapes user-provided values before Telegram HTML rendering.",
    "compatibility_tagline": "Designed as a drop-in presentation module for the existing app.py.",
}

def tagline(name, default=""):
    return esc(UI_COPY.get(str(name or "").strip().lower(), default))

def help_section(title, description, commands=()):
    command_lines = "\n".join(f"┃ <code>{esc(c)}</code>" for c in commands)
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {style_text(_safe(title))}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ {esc(_safe(description))}\n"
        f"{command_lines}\n"
        f"<b>{PANEL_BOTTOM}</b>"
    )

def full_help():
    sections = [
        help_section("PLAYBACK", tagline("player_tagline"),
                     ["/play song", "/vplay video", "/pause", "/resume", "/skip", "/stop"]),
        help_section("QUEUE", tagline("queue_tagline"),
                     ["/queue", "/remove 2", "/jump 3", "/clear", "/shuffle", "/loop"]),
        help_section("DISCOVERY", tagline("search_tagline"),
                     ["/search song", "/discover topic", "/radio topic", "/autoplay topic"]),
        help_section("AUDIO", tagline("effects_tagline"),
                     ["/volume 100", "/mute", "/unmute", "/effect preset"]),
        help_section("TOOLS", tagline("performance_tagline"),
                     ["/ping", "/stats", "/health", "/history", "/settings", "/features"]),
        help_section("OWNER", "Owner operations remain protected by app.py.",
                     ["/approvegc", "/revoke_gc", "/clone", "/clones"]),
    ]
    return f"<b>{BRAND}</b>\n\n" + "\n\n".join(sections) + f"\n\n{footer_text()}"

# Compatibility aliases for future code. They do not replace any function
# imported by the current app.py.
home_text = welcome
player_card = player_text
effects_text = effect_catalog
queue_text = queue_card
status_text = engine_card


# ============================================================================
# FINAL PRO PRESENTATION PACK
# ============================================================================

TIP_CARDS = (
    "💡 Use /play <song> for the quickest normal music flow.",
    "💡 Use /vplay <video> when you specifically need video playback.",
    "💡 Use the player card to control pause, resume, skip, loop and volume.",
    "💡 Use /queue to inspect waiting tracks before changing the order.",
    "💡 Use /shuffle when you want the waiting queue randomized.",
    "💡 Use /autoplay <topic> for continuous topic-based discovery.",
    "💡 Use /radio <topic> for a radio-style continuous session.",
    "💡 Use /search <song> when you want to select a specific result.",
    "💡 Use /effect <preset> to change the current audio effect.",
    "💡 Use /nleft to check the estimated remaining playback time.",
    "💡 Use /ping to check bot responsiveness.",
    "💡 Use /health or /stats for application status information.",
    "💡 Keep the Voice Chat active and make sure the bot has the required rights.",
    "💡 Thumbnails are rendered by the application when a valid thumbnail is available.",
    "💡 Queue entries are escaped before being inserted into Telegram HTML.",
    "💡 Playback permissions remain enforced by the existing application.",
    "💡 The UI never stores or exposes API credentials.",
    "💡 Direct-stream availability can vary with the upstream media source.",
    "💡 If a direct stream cannot be used, the existing resolver can use its fallback.",
    "💡 UI refreshes do not themselves start a new track.",
)

def tips_text(limit=8):
    limit = max(1, min(len(TIP_CARDS), _num(limit, 8)))
    return info_panel("FEARLESS TIPS", *(
        f"┃ {esc(tip)}" for tip in TIP_CARDS[:limit]
    ))

def welcome_extended(cfg, user):
    return (
        f"{welcome(cfg, user)}\n\n"
        f"<b>╭━━〔 ⚡ QUICK CONTROL 〕━━╮</b>\n"
        "┃ 🎧 <code>/play song</code> — instant music request\n"
        "┃ 🎥 <code>/vplay video</code> — video request\n"
        "┃ 📜 <code>/queue</code> — inspect your queue\n"
        "┃ ▶️ <code>/now</code> — open the live player\n"
        "┃ 🎛 <code>/effect preset</code> — tune playback\n"
        "┃ ♾️ <code>/autoplay topic</code> — continuous discovery\n"
        "<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        f"{POWER}"
    )

def player_banner(title="No track", state="READY"):
    state = _safe(state, "READY").upper()
    icon = "▶️" if state == "PLAYING" else "⏸️" if state == "PAUSED" else "🟢"
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {icon} {style_text('FEARLESS PLAYER')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 🎵 <b>{esc(_clip(title, 70))}</b>\n"
        f"┃ 📡 State: <code>{esc(state)}</code>\n"
        f"<b>{PANEL_BOTTOM}</b>"
    )

def playback_snapshot(p, name=""):
    current = getattr(p, "current", None)
    if not current:
        return player_banner("Nothing is playing", "READY")
    state = "PAUSED" if getattr(p, "paused", False) else "PLAYING"
    title = getattr(current, "title", "Unknown")
    total = getattr(current, "duration", 0)
    return (
        f"{player_banner(title, state)}\n\n"
        f"👤 <b>{esc(_clip(name or getattr(current, 'requested_by', 'Unknown'), 50))}</b>\n"
        f"⏱ <code>{duration(total)}</code>\n"
        f"🔊 {volume_meter(getattr(p, 'volume', 100))}\n"
        f"📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>\n"
        f"🎛 FX: <code>{esc(EFFECTS.get(getattr(p, 'effect', 'normal'), ('Normal',''))[0])}</code>\n\n"
        f"{POWER}\n{BRAND}"
    )

def minimal_footer():
    return f"<i>{esc(UI_SIGNATURE)}</i>"

# A small collection of visual glyphs used by future UI callers.
GLYPHS = {
    "top": "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮",
    "middle": "├━━━━━━━━━━━━━━━━━━━━━━━━━━━━┤",
    "bottom": "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯",
    "dot": "•",
    "arrow": "➜",
    "play": "▶️",
    "pause": "⏸️",
    "stop": "⏹️",
    "skip": "⏭️",
    "previous": "⏮️",
    "queue": "📜",
    "search": "🔎",
    "music": "🎵",
    "video": "🎥",
    "audio": "🎧",
    "effects": "🎛️",
    "volume": "🔊",
    "mute": "🔇",
    "loop": "🔁",
    "autoplay": "♾️",
    "shuffle": "🔀",
    "success": "🟢",
    "warning": "🟡",
    "error": "🔴",
    "info": "🔵",
    "owner": "👑",
    "settings": "⚙️",
    "speed": "⚡",
}

def glyph(name, default="•"):
    return GLYPHS.get(str(name or "").lower(), default)

def badge(text, icon="•"):
    return f"<b>{icon} {style_text(_safe(text))}</b>"

def labeled_value(label, value, icon="•"):
    return f"┃ {icon} <b>{esc(_safe(label))}</b>: <code>{esc(_safe(value))}</code>"

def safe_track_title(track):
    return esc(_clip(getattr(track, "title", "Unknown"), 72))

def safe_requested_by(track):
    return esc(_clip(getattr(track, "requested_by", "Unknown"), 50))

def media_label(track):
    return "VIDEO" if bool(getattr(track, "video", False)) else "AUDIO"

def player_state(p):
    if not getattr(p, "current", None):
        return "READY"
    return "PAUSED" if getattr(p, "paused", False) else "PLAYING"

def player_mode(p):
    current = getattr(p, "current", None)
    if not current:
        return "IDLE"
    return media_label(current)

def player_summary(p):
    current = getattr(p, "current", None)
    if not current:
        return (
            f"{badge('PLAYER READY', glyph('success'))}\n"
            f"┃ 📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>\n"
            f"┃ 🔊 Volume: <code>{_pct(getattr(p, 'volume', 100))}%</code>"
        )
    return (
        f"{badge(player_state(p), glyph('play') if player_state(p) == 'PLAYING' else glyph('pause'))}\n"
        f"┃ 🎵 <b>{safe_track_title(current)}</b>\n"
        f"┃ 🎧 Mode: <code>{media_label(current)}</code>\n"
        f"┃ ⏱ <code>{duration(getattr(current, 'duration', 0))}</code>\n"
        f"┃ 📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>"
    )

# End of presentation pack.



def now_streaming_quote(track, p=None):
    """The coloured Telegram-style quote used inside song/player messages."""
    title = esc(_clip(getattr(track, "title", "Unknown"), 90))
    by = esc(_clip(getattr(track, "requested_by", "Unknown"), 55))
    total = getattr(track, "duration", 0)
    try:
        left = remaining_seconds(p) if p is not None else 0
    except Exception:
        left = 0
    return (
        "<blockquote>"
        "<b>🎧 Now Streaming</b>  ❯❯\n"
        f"🎵 <b>Title:</b> <i>{title}</i>\n"
        f"⏱ <b>Duration:</b> <code>{duration(total)}</code>\n"
        f"⏳ <b>Remaining:</b> <code>{duration(left)}</code>\n"
        f"👤 <b>Requested by:</b> {by}"
        "</blockquote>"
    )

# ============================================================================
# THUMBNAIL-FIRST SONG MESSAGE PACK
# ============================================================================
# Telegram photo/caption rendering is performed by app.py. These helpers
# prepare thumbnail-aware captions and media metadata without changing the
# playback engine or inventing callback handlers.
# ============================================================================

def thumbnail_url(track_or_url):
    """Return the best available thumbnail URL from a Track/result-like object."""
    if not track_or_url:
        return ""
    if isinstance(track_or_url, str):
        value = track_or_url.strip()
        return value if value.startswith(("http://", "https://")) else ""
    direct = getattr(track_or_url, "thumbnail", "") or getattr(track_or_url, "thumb", "")
    if direct:
        return str(direct)
    thumbs = getattr(track_or_url, "thumbnails", None) or []
    if isinstance(thumbs, (list, tuple)):
        for item in thumbs:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
            if isinstance(item, dict):
                url = item.get("url") or item.get("thumbnail")
                if url:
                    return str(url)
            url = getattr(item, "url", "") if item is not None else ""
            if url:
                return str(url)
    return ""

def youtube_thumbnail(video_id):
    """Generate the standard YouTube thumbnail fallback for an 11-char ID."""
    vid = str(video_id or "").strip()
    if len(vid) == 11:
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    return ""

def song_caption(track, p=None, heading="NOW PLAYING"):
    """Rich thumbnail-ready caption for any song-related Telegram photo."""
    title = getattr(track, "title", "Unknown")
    by = getattr(track, "requested_by", "Unknown")
    total = getattr(track, "duration", 0)
    mode = "🎥 VIDEO" if bool(getattr(track, "video", False)) else "🎧 AUDIO"

    volume = _pct(getattr(p, "volume", 100)) if p is not None else 100
    queue_count = len(getattr(p, "queue", [])) if p is not None else 0
    effect = getattr(p, "effect", "normal") if p is not None else "normal"
    effect_name = EFFECTS.get(effect, ("Normal", ""))[0]

    state = "⏸️ PAUSED" if p is not None and getattr(p, "paused", False) else "▶️ PLAYING"
    auto = "ON" if p is not None and getattr(p, "autoplay", False) else "OFF"
    loop = "ON" if p is not None and getattr(p, "loop", False) else "OFF"

    remaining = ""
    if p is not None:
        try:
            remaining = f"\n┃ ⏳ Left: <code>{duration(remaining_seconds(p))}</code>"
        except Exception:
            pass

    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {style_text(_safe(heading))}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ {state} • {mode}\n"
        f"┃ 🎵 <b>{esc(_clip(title, 75))}</b>\n"
        f"┃ 👤 {esc(_clip(by, 50))}\n"
        f"┃ ⏱ <code>{duration(total)}</code>{remaining}\n"
        f"┃ 🔊 <code>{volume}%</code> • 📚 <code>{queue_count}</code>\n"
        f"┃ 🎛 <code>{esc(_clip(effect_name, 30))}</code> • 🔁 <code>{loop}</code>\n"
        f"┃ ♾️ Autoplay: <code>{auto}</code>\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n"
        f"{POWER}\n{BRAND}"
    )

def song_search_caption(query, result_count=0):
    """Caption for thumbnail-bearing search result/player messages."""
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 🔎 {style_text('PRIME SEARCH')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 🎵 Query: <code>{esc(_clip(query, 80))}</code>\n"
        f"┃ 🎯 Results: <code>{max(0, _num(result_count))}</code>\n"
        "┃ 🖼 Song thumbnail: <code>AVAILABLE WHEN PROVIDED</code>\n"
        "┃ ▶ Play • ⏭ Play Next • ➕ Queue\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def song_queue_caption(track, position, total_queue):
    """Thumbnail-ready queue item caption."""
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 📜 {style_text('QUEUED TRACK')}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ #{_num(position, 1):02d} • {esc(_clip(getattr(track, 'title', 'Unknown'), 72))}\n"
        f"┃ ⏱ <code>{duration(getattr(track, 'duration', 0))}</code>\n"
        f"┃ 📚 Queue: <code>{max(0, _num(total_queue))}</code>\n"
        f"┃ 👤 {esc(_clip(getattr(track, 'requested_by', 'Unknown'), 45))}\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def song_status_caption(track, status="READY"):
    """Thumbnail-ready status card for resolving/starting/finished messages."""
    icon = {
        "READY": "🟢",
        "LOADING": "🟡",
        "RESOLVING": "🟡",
        "PLAYING": "▶️",
        "PAUSED": "⏸️",
        "ERROR": "🔴",
        "DONE": "✅",
    }.get(str(status).upper(), "🔵")
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ {icon} {style_text(str(status).upper())}</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        f"┃ 🎵 <b>{esc(_clip(getattr(track, 'title', 'Unknown'), 75))}</b>\n"
        f"┃ 🎧 Mode: <code>{media_label(track)}</code>\n"
        f"┃ ⏱ Duration: <code>{duration(getattr(track, 'duration', 0))}</code>\n"
        "┃ 🖼 Thumbnail: <code>TRACK THUMBNAIL</code>\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )

def thumbnail_message_data(track, p=None, heading="NOW PLAYING"):
    """
    Return a small dictionary for callers that want one standard source of
    thumbnail + caption. app.py can pass `photo` and `caption` directly to
    send_photo/edit-media without duplicating formatting logic.
    """
    thumb = thumbnail_url(track)
    return {
        "photo": thumb,
        "caption": song_caption(track, p, heading=heading),
        "thumbnail": thumb,
    }

def thumbnail_required_note(track):
    if thumbnail_url(track):
        return "🖼 Thumbnail ready"
    return "🖼 Thumbnail unavailable for this track"

def thumbnail_fallback_for_id(video_id):
    return youtube_thumbnail(video_id)

THUMBNAIL_POLICY = (
    "Song-related cards should use the track thumbnail whenever one is "
    "available. UI helpers never replace an unavailable thumbnail with a "
    "fake image; app.py decides whether to send a photo or text fallback."
)


# ============================================================================
# FEARLESS RICH UI — PREMIUM PRESENTATION LAYER
# ============================================================================
# Drop-in UI helpers. They do not register handlers and do not alter playback.
# ============================================================================

RICH_VERSION = "FEARLESS RICH UI 6.0"

RICH_COLORS = {
    "primary": "🟣",
    "success": "🟢",
    "warning": "🟡",
    "danger": "🔴",
    "info": "🔵",
    "audio": "🎧",
    "video": "🎥",
    "music": "🎵",
    "queue": "📜",
    "effects": "🎛️",
    "speed": "⚡",
    "voice": "🎙️",
    "search": "🔎",
    "auto": "♾️",
    "volume": "🔊",
    "settings": "⚙️",
    "owner": "👑",
    "star": "⭐",
}

RICH_FRAMES = {
    "top": "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮",
    "line": "┃ ──────────────────────────────",
    "mid": "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫",
    "bottom": "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯",
}

def rich_frame(title, lines=(), icon="🔷", footer=True):
    body = "\n".join(str(x) for x in lines if x is not None)
    tail = f"\n\n{DONE}" if footer else ""
    return (
        f"<b>{RICH_FRAMES['top']}</b>\n"
        f"<b>┃ {icon} {style_text(_safe(title))}</b>\n"
        f"<b>{RICH_FRAMES['mid']}</b>\n"
        f"{body}{tail}\n"
        f"<b>{RICH_FRAMES['bottom']}</b>\n\n"
        f"{POWER}\n{BRAND}"
    )

def rich_home_text(cfg, user):
    bot_name = esc(getattr(cfg, "bot_name", "FEARLESS MUSIC"))
    return rich_frame(
        "FEARLESS CONTROL CENTER",
        (
            f"┃ 👤 <b>{esc(_clip(user, 45))}</b>",
            f"┃ 🤖 <b>{bot_name}</b>",
            "┃ 🚀 <code>FAST MEDIA • SMART QUEUE • VOICE CHAT</code>",
            "┃ 🎧 Audio  •  🎥 Video  •  ♾️ Autoplay",
            "┃ 🔎 Search  •  📜 Queue  •  🎛 Effects",
            "┃ 🖼 Thumbnail-aware song cards",
            "",
            "┃ <b>QUICK START</b>",
            "┃ <code>/play O Maahi</code>",
            "┃ <code>/vplay music video</code>",
            "┃ <code>/autoplay Romantic Hindi Songs</code>",
        ),
    )

def rich_now_playing(p, user=""):
    current = getattr(p, "current", None)
    if not current:
        return rich_frame(
            "NOW PLAYING",
            (
                "┃ 🟢 <b>PLAYER READY</b>",
                f"┃ 📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>",
                f"┃ 🔊 Volume: <code>{_pct(getattr(p, 'volume', 100))}%</code>",
                "┃ 🎵 Send <code>/play song</code> to begin.",
            ),
            icon="🎧",
        )
    state = "⏸️ PAUSED" if getattr(p, "paused", False) else "▶️ PLAYING"
    mode = "🎥 VIDEO" if getattr(current, "video", False) else "🎧 AUDIO"
    total = int(getattr(current, "duration", 0) or 0)
    try:
        left = remaining_seconds(p)
    except Exception:
        left = 0
    elapsed = max(0, total - left)
    percent = round(elapsed * 100 / total) if total else 0
    effect = getattr(p, "effect", "normal")
    effect_name = EFFECTS.get(effect, ("Normal", ""))[0]
    return rich_frame(
        "NOW PLAYING",
        (
            f"┃ {state}  •  {mode}",
            f"┃ 🎵 <b>{safe_track_title(current)}</b>",
            f"┃ 👤 {safe_requested_by(current)}",
            f"┃ ⏱ <code>{duration(elapsed)}</code> / <code>{duration(total)}</code>",
            f"┃ {meter(percent, 18)} <code>{percent}%</code>",
            f"┃ ⏳ Remaining: <code>{duration(left)}</code>",
            f"┃ 🔊 {volume_meter(getattr(p, 'volume', 100))}",
            f"┃ 🎛 FX: <code>{esc(_clip(effect_name, 30))}</code>",
            f"┃ 📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>",
            f"┃ 🔁 Loop: <code>{'ON' if getattr(p, 'loop', False) else 'OFF'}</code>",
            f"┃ ♾️ Autoplay: <code>{'ON' if getattr(p, 'autoplay', False) else 'OFF'}</code>",
        ),
        icon="🎵",
    )

def rich_queue(p, page=0, per_page=8):
    queue = list(getattr(p, "queue", []) or [])
    per_page = max(1, min(12, _num(per_page, 8)))
    pages = max(1, (len(queue) + per_page - 1) // per_page)
    page = max(0, min(_num(page), pages - 1))
    chunk = queue[page * per_page:(page + 1) * per_page]
    if not chunk:
        lines = (
            "┃ 📭 <b>QUEUE EMPTY</b>",
            "┃ Add tracks with <code>/play song</code>.",
            "┃ Use <code>/autoplay topic</code> for automatic refill.",
        )
    else:
        lines = tuple(
            f"┃ <code>{i:02d}</code>  🎵 <b>{safe_track_title(track)}</b>\n"
            f"┃      ⏱ <code>{duration(getattr(track, 'duration', 0))}</code> • "
            f"👤 {safe_requested_by(track)}"
            for i, track in enumerate(chunk, page * per_page + 1)
        )
        lines += (f"┃ 📄 Page <code>{page + 1}/{pages}</code> • {len(queue)} total",)
    return rich_frame("SMART QUEUE", lines, icon="📜")

def rich_search(query, results=0, page=1, pages=1):
    return rich_frame(
        "PRIME SEARCH",
        (
            f"┃ 🔎 <code>{esc(_clip(query, 90))}</code>",
            f"┃ 🎯 Results: <code>{max(0, _num(results))}</code>",
            f"┃ 📄 Page: <code>{max(1, _num(page))}/{max(1, _num(pages, 1))}</code>",
            "",
            "┃ ▶ Play   ⏭ Play Next   ➕ Queue",
            "┃ 🖼 Result cards use the available song thumbnail.",
            "┃ ⚡ Select a result to continue playback.",
        ),
        icon="🔎",
    )

def rich_effects(page=0):
    items = list(EFFECTS.items())
    per = 12
    pages = max(1, (len(items) + per - 1) // per)
    page = max(0, min(_num(page), pages - 1))
    chunk = items[page * per:(page + 1) * per]
    lines = tuple(
        f"┃ 🎛 <code>{esc(_safe(key))}</code> • <b>{esc(_safe(label))}</b>"
        for key, (label, _) in chunk
    ) + (f"┃ 📄 Page <code>{page + 1}/{pages}</code>",)
    return rich_frame("AUDIO EFFECT LAB", lines, icon="🎛️")

def rich_autoplay(p):
    enabled = bool(getattr(p, "autoplay", False))
    topic = esc(_clip(getattr(p, "autoplay_topic", ""), 75)) or "Not selected"
    return rich_frame(
        "AUTOPLAY CENTER",
        (
            f"┃ ♾️ Status: <code>{'ON' if enabled else 'OFF'}</code>",
            f"┃ 🎯 Topic: <code>{topic}</code>",
            "┃ 🔎 Discovery: <code>CURATED + LIVE</code>",
            "┃ 📚 Queue: <code>AUTO REFILL</code>",
            "┃ 🎧 Playback: <code>CONTINUOUS</code>",
        ),
        icon="♾️",
    )

def rich_volume(p):
    volume = _pct(getattr(p, "volume", 100))
    return rich_frame(
        "VOLUME CONTROL",
        (
            f"┃ 🔊 Level: <code>{volume}%</code>",
            f"┃ {meter(volume, 22)}",
            "┃ Use the player buttons for quick adjustment.",
            "┃ Use <code>/volume 100</code> for a precise value.",
            f"┃ Mute: <code>{'ON' if volume == 0 else 'OFF'}</code>",
        ),
        icon="🔊",
    )

def rich_settings(p):
    return rich_frame(
        "PLAYER SETTINGS",
        (
            f"┃ 🔊 Volume: <code>{_pct(getattr(p, 'volume', 100))}%</code>",
            f"┃ 🎛 FX: <code>{esc(_clip(EFFECTS.get(getattr(p, 'effect', 'normal'), ('Normal',''))[0], 35))}</code>",
            f"┃ 🔁 Loop: <code>{'ON' if getattr(p, 'loop', False) else 'OFF'}</code>",
            f"┃ ♾️ Autoplay: <code>{'ON' if getattr(p, 'autoplay', False) else 'OFF'}</code>",
            f"┃ ⚡ Speed: <code>{float(getattr(p, 'speed', 1.0) or 1.0):.2f}x</code>",
            f"┃ 📚 Queue: <code>{len(getattr(p, 'queue', []))}</code>",
        ),
        icon="⚙️",
    )

def rich_track(track):
    return rich_frame(
        "TRACK INFORMATION",
        (
            f"┃ 🎵 <b>{safe_track_title(track)}</b>",
            f"┃ 👤 {safe_requested_by(track)}",
            f"┃ 🎧 Type: <code>{media_label(track)}</code>",
            f"┃ ⏱ Duration: <code>{duration(getattr(track, 'duration', 0))}</code>",
            f"┃ 🖼 Thumbnail: <code>{'READY' if thumbnail_url(track) else 'UNAVAILABLE'}</code>",
            f"┃ 🔗 Source: <code>{esc(_clip(getattr(track, 'source', 'YouTube'), 30))}</code>",
        ),
        icon="🎵",
    )

def rich_loading(query="", stage="SEARCHING"):
    q = f"\n┃ 🔎 <code>{esc(_clip(query, 85))}</code>" if query else ""
    return rich_frame(
        stage,
        (
            f"┃ 🟡 <b>{esc(_safe(stage).upper())}</b>{q}",
            "┃ ▰▰▰▰▰▰▰▱▱▱  <code>PROCESSING</code>",
            "┃ ⚡ Fast resolver route is being attempted.",
            "┃ 🧠 Fallback remains available if required.",
        ),
        icon="⚡",
        footer=False,
    )

def rich_success(track):
    return rich_frame(
        "PLAYBACK LIVE",
        (
            "┃ 🟢 <b>STREAM CONNECTED</b>",
            f"┃ 🎵 <b>{safe_track_title(track)}</b>",
            f"┃ 🎧 Mode: <code>{media_label(track)}</code>",
            f"┃ ⏱ <code>{duration(getattr(track, 'duration', 0))}</code>",
            f"┃ 🖼 Thumbnail: <code>{'READY' if thumbnail_url(track) else 'UNAVAILABLE'}</code>",
            "┃ 🎙️ Voice Chat: <code>PLAYBACK ACTIVE</code>",
        ),
        icon="🚀",
    )

def rich_error(message, query=""):
    lines = [
        f"┃ 🔴 <b>{esc(_clip(message, 150))}</b>",
        "┃ 🔄 You can retry the request.",
    ]
    if query:
        lines.append(f"┃ 🔎 Query: <code>{esc(_clip(query, 75))}</code>")
    return rich_frame("PLAYBACK ERROR", lines, icon="🔴")

def rich_command_menu():
    return rich_frame(
        "COMMAND CENTER",
        (
            "┃ 🎧 <b>PLAYBACK</b> — /play /vplay /pause /resume /skip /stop",
            "┃ 📜 <b>QUEUE</b> — /queue /remove /jump /clear /shuffle /loop",
            "┃ 🔊 <b>AUDIO</b> — /volume /mute /unmute /effect",
            "┃ 🔎 <b>DISCOVERY</b> — /search /discover /radio /autoplay",
            "┃ ⚡ <b>STATUS</b> — /ping /stats /health /history",
            "┃ ⚙️ <b>TOOLS</b> — /settings /features",
            "┃ 👑 <b>OWNER</b> — /approvegc /revoke_gc /clone /clones",
        ),
        icon="📖",
    )

def rich_about(cfg):
    return rich_frame(
        "ABOUT FEARLESS",
        (
            f"┃ 🤖 <b>{esc(getattr(cfg, 'bot_name', 'FEARLESS MUSIC'))}</b>",
            "┃ 🎧 Telegram Voice Chat Music Player",
            "┃ ⚡ Fast resolver + fallback playback",
            "┃ 📚 Smart queue management",
            "┃ 🎛 Audio effect presets",
            "┃ ♾️ Topic-based autoplay",
            "┃ 🖼 Thumbnail-aware media cards",
            "┃ 🛡 Permission checks remain in app.py",
            f"┃ <code>{RICH_VERSION}</code>",
        ),
        icon="⚝",
    )

def rich_links():
    return links(None)

def rich_notification(title, message, level="info"):
    icon = RICH_COLORS.get(str(level).lower(), RICH_COLORS["info"])
    return rich_frame(
        title,
        (f"┃ {icon} {esc(_clip(message, 180))}",),
        icon=icon,
    )

# Semantic aliases for a richer API without changing existing app imports.
control_center = rich_home_text
now_playing_card = rich_now_playing
smart_queue_card = rich_queue
search_card = rich_search
effect_lab_card = rich_effects
autoplay_center_card = rich_autoplay
volume_card = rich_volume
settings_card = rich_settings
track_info_card = rich_track
loading_card = rich_loading
success_card = rich_success
error_card = rich_error
command_center = rich_command_menu
about_card = rich_about


# ============================================================================
# RICH TELEGRAM QUOTE / BLOCKQUOTE PACK
# ============================================================================
# Telegram HTML blockquotes are rendered as visually distinct quote blocks.
# A Telegram bot cannot choose an arbitrary quote background colour from
# ui.py; the Telegram client controls the actual colour/theme. These helpers
# create the supported HTML quote forms and keep song cards visually rich.
# ============================================================================

def quote_block(text, expandable=False):
    """Create a Telegram HTML blockquote with safely escaped content."""
    clean = esc(str(text or "").strip())
    if not clean:
        clean = "—"
    if expandable:
        return f"<blockquote expandable>{clean}</blockquote>"
    return f"<blockquote>{clean}</blockquote>"

def quote_lines(*lines, expandable=False):
    clean = [esc(str(x)) for x in lines if str(x or "").strip()]
    return quote_block("\n".join(clean), expandable=expandable)

def accent_quote(title, lines=(), icon="◆", expandable=False):
    """Rich coloured-looking quote card; colour itself is Telegram-controlled."""
    title = esc(_safe(title))
    body = "\n".join(
        f"{esc(str(icon))} {esc(str(line))}"
        for line in lines
        if str(line or "").strip()
    )
    content = f"<b>{title}</b>"
    if body:
        content += f"\n{body}"
    return quote_block(content, expandable=expandable)

def song_quote(track, p=None, title="TRACK INFORMATION"):
    """Quote block for a song-related message/caption."""
    name = esc(_clip(getattr(track, "title", "Unknown"), 75))
    by = esc(_clip(getattr(track, "requested_by", "Unknown"), 50))
    dur = duration(getattr(track, "duration", 0))
    mode = media_label(track)
    queue_count = len(getattr(p, "queue", [])) if p is not None else 0
    volume = _pct(getattr(p, "volume", 100)) if p is not None else 100

    return accent_quote(
        title,
        (
            f"🎵 {name}",
            f"👤 Requested by: {by}",
            f"🎧 Mode: {mode}",
            f"⏱ Duration: {dur}",
            f"🔊 Volume: {volume}%",
            f"📚 Queue: {queue_count}",
        ),
        icon="┃",
    )

def player_quote(p):
    """Live-player quote block containing state and current-track details."""
    current = getattr(p, "current", None)
    if not current:
        return accent_quote(
            "PLAYER STATUS",
            ("🟢 Player ready", f"📚 Queue: {len(getattr(p, 'queue', []))}"),
            icon="┃",
        )

    state = "⏸️ PAUSED" if getattr(p, "paused", False) else "▶️ PLAYING"
    left = 0
    try:
        left = remaining_seconds(p)
    except Exception:
        pass

    return accent_quote(
        "LIVE PLAYER",
        (
            f"{state} • {media_label(current)}",
            f"🎵 {esc(_clip(getattr(current, 'title', 'Unknown'), 75))}",
            f"⏱ {duration(getattr(current, 'duration', 0))}",
            f"⏳ {duration(left)} remaining",
            f"🔊 {_pct(getattr(p, 'volume', 100))}%",
            f"📚 {len(getattr(p, 'queue', []))} queued",
        ),
        icon="┃",
    )

def status_quote(status, detail="", icon="●"):
    return accent_quote(
        f"{icon} {str(status).upper()}",
        (detail,) if detail else (),
        icon="┃",
    )

def success_quote(title, detail="Playback started successfully."):
    return accent_quote(
        "PLAYBACK STARTED",
        (f"🎵 {title}", f"⚡ {detail}", "🎙️ Voice Chat stream is active."),
        icon="┃",
    )

def warning_quote(title, detail):
    return accent_quote(
        f"⚠️ {title}",
        (detail, "🔄 You can retry the current request."),
        icon="┃",
    )

def error_quote(title, detail):
    return accent_quote(
        f"🔴 {title}",
        (detail, "🛠 Check the Voice Chat and media source, then retry."),
        icon="┃",
    )

def loading_quote(action, detail="Preparing media…"):
    return accent_quote(
        f"🟡 {action}",
        (detail, "⚡ Selecting the fastest available media route."),
        icon="┃",
    )

def search_quote(query, count=0):
    return accent_quote(
        "🔎 PRIME SEARCH",
        (
            f"🎵 Query: {query}",
            f"🎯 Results: {max(0, _num(count))}",
            "▶️ Play • ⏭️ Play Next • ➕ Queue",
        ),
        icon="┃",
    )

def queue_quote(p, page=0, per=8):
    queue = list(getattr(p, "queue", []) or [])
    per = max(1, min(12, _num(per, 8)))
    total = max(1, (len(queue) + per - 1) // per)
    page = max(0, min(_num(page), total - 1))
    chunk = queue[page * per:(page + 1) * per]
    if not chunk:
        return accent_quote(
            "📜 SMART QUEUE",
            ("📭 Queue is empty.", "Use /play <song> to add a track."),
            icon="┃",
        )
    rows = []
    for idx, item in enumerate(chunk, page * per + 1):
        rows.append(
            f"{idx:02d}. {esc(_clip(getattr(item, 'title', 'Unknown'), 65))} "
            f"• {duration(getattr(item, 'duration', 0))}"
        )
    rows.append(f"📄 Page {page + 1}/{total}")
    return accent_quote("📜 SMART QUEUE", rows, icon="┃")

def effects_quote(preset=None):
    if preset:
        label = EFFECTS.get(str(preset), (str(preset), ""))[0]
        return accent_quote(
            "🎛 EFFECT LAB",
            (f"Selected: {label}", "The application will handle the actual effect."),
            icon="┃",
        )
    return accent_quote(
        "🎛 EFFECT LAB",
        ("Choose a preset from the Effects panel.", f"Available: {len(EFFECTS)} presets"),
        icon="┃",
    )

def autoplay_quote(p):
    enabled = bool(getattr(p, "autoplay", False))
    topic = getattr(p, "autoplay_topic", "") or "Not selected"
    return accent_quote(
        "♾️ AUTOPLAY CENTER",
        (
            f"Status: {'ON' if enabled else 'OFF'}",
            f"Topic: {esc(_clip(topic, 75))}",
            "Discovery: curated + live",
            "Queue: automatic refill",
        ),
        icon="┃",
    )

def quote_song_caption(track, p=None):
    """Full rich song caption with a Telegram quote block."""
    return (
        song_caption(track, p, heading="NOW PLAYING")
        + "\n\n"
        + song_quote(track, p)
    )

def quote_player_caption(p, name=""):
    """Player caption with the live-player quote appended."""
    return (
        player_text(p, name)
        + "\n\n"
        + player_quote(p)
    )

def quote_search_caption(query, result_count=0):
    return song_search_caption(query, result_count) + "\n\n" + search_quote(
        query, result_count
    )

def quote_queue_caption(p, page=0, per=8):
    return queue_header(len(getattr(p, "queue", []))) + "\n\n" + queue_quote(
        p, page, per
    )

# Telegram-supported quote capabilities, kept explicit for maintainability.
TELEGRAM_QUOTE_INFO = {
    "standard": "<blockquote>...</blockquote>",
    "expandable": "<blockquote expandable>...</blockquote>",
    "client_colour": "Telegram client/theme controlled",
    "ui_role": "Song, player, search, queue, status and help cards",
}

def telegram_quote_info():
    return (
        f"<b>{PANEL_TOP}</b>\n"
        f"<b>┃ 💬 TELEGRAM QUOTE UI</b>\n"
        f"<b>{PANEL_MID}</b>\n"
        "┃ ▌ Rich blockquotes are supported in Telegram HTML.\n"
        "┃ ▌ The visible quote colour is controlled by Telegram's client/theme.\n"
        "┃ ▌ The bot can control the quote content and layout, not an arbitrary RGB colour.\n"
        "┃ ▌ Song thumbnails remain separate media supplied by app.py.\n"
        f"<b>{PANEL_BOTTOM}</b>\n\n{POWER}\n{BRAND}"
    )
