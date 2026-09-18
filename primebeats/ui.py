from __future__ import annotations
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .youtube import duration
from .effects import EFFECTS
import re, time, html

BRAND = "⚝ 𝐅ᴇᴀʀʟᴇss ꭗ 𝐌ᴜsɪᴄ ᯤ"
POWER = "🚀 ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ"
OWNER = "@Prime_Fearless_45"
OWNER_ID = "7915543522"

_SMALL = str.maketrans({
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ',
    'n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'
})
_BOLD = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"))

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
    parts=re.split(r'(<code>.*?</code>|<pre>.*?</pre>|https?://\S+|t\.me/\S+|<[^>]+>|&(?:amp|lt|gt|quot|#\d+);)', text, flags=re.S|re.I)
    out=[]
    for part in parts:
        low=part.lower()
        if low.startswith("<code>") or low.startswith("<pre>"):
            out.append(part)
        elif (part.startswith("<") and part.endswith(">")) or (low.startswith("&") and low.endswith(";")) or low.startswith(("http://","https://","t.me/")):
            out.append(part)
        else:
            out.append(re.sub(r"[A-Za-z][A-Za-z'’+×/-]*", lambda m:_word_style(m.group(0)), part))
    return "".join(out)

def _btn(text, data):
    return InlineKeyboardButton(text, callback_data=data)

def links(cfg):
    return InlineKeyboardMarkup([
        [_btn("👑 𝐎ᴡɴᴇʀ", "yourdaddy"), InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ", url="https://t.me/SPARK_X_NETWORK")],
        [InlineKeyboardButton("📢 𝐂ʜᴀɴɴᴇʟ", url="https://t.me/SPARK_X_NETWORK_OP"), InlineKeyboardButton("⚡ 𝐎ғғɪᴄɪᴀʟ", url="https://t.me/Prime_Arrived")],
        [_btn("🎧 𝐏ʟᴀʏ", "help:play"), _btn("🎥 𝐕ɪᴅᴇᴏ 𝐏ʟᴀʏ", "help:vplay")]
    ])

def home_keyboard(cfg):
    return InlineKeyboardMarkup([
        [_btn("🎧 𝐏ʟᴀʏ", "help:play"), _btn("🎥 𝐕ɪᴅᴇᴏ", "help:vplay"), _btn("📜 𝐐ᴜᴇᴜᴇ", "queue")],
        [_btn("▶️ 𝐍ᴏᴡ 𝐏ʟᴀʏɪɴɢ", "now"), _btn("♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ", "auto")],
        [_btn("🎙️ 𝐒ᴛᴀʀᴛ 𝐕𝐂", "startvc"), _btn("👑 𝐘ᴏᴜʀ 𝐃ᴀᴅᴅʏ", "yourdaddy")],
        [_btn("⏸️ 𝐏ᴀᴜsᴇ", "pause"), _btn("▶️ 𝐑ᴇsᴜᴍᴇ", "resume"), _btn("⏭️ 𝐒ᴋɪᴘ", "skip"), _btn("⏹️ 𝐒ᴛᴏᴘ", "stop")],
        [_btn("🔀 sʜᴜғғʟᴇ", "shuffle"), _btn("🔁 𝐋ᴏᴏᴘ", "loop"), _btn("⭐ 𝐅ᴀᴠ", "favorite")],
        [_btn("🔉 ᴠᴏʟ −", "voldown"), _btn("🔊 ᴠᴏʟ +", "volup"), _btn("🔇 ᴍᴜᴛᴇ", "mute")],
        [_btn("🎛️ 𝐅𝐗 𝐋ᴀʙ", "effects:0"), _btn("📖 𝐇ᴇʟᴘ", "help"), _btn("⚡ 𝐏ɪɴɢ", "ping")],
        [_btn("🌐 𝐒ᴜᴘᴘᴏʀᴛ & 𝐋ɪɴᴋs", "links")]
    ])

def player_keyboard():
    return InlineKeyboardMarkup([
        [_btn("⏸️ 𝐏ᴀᴜsᴇ", "pause"), _btn("▶️ 𝐑ᴇsᴜᴍᴇ", "resume"), _btn("⏭️ 𝐒ᴋɪᴘ", "skip"), _btn("⏹️ 𝐒ᴛᴏᴘ", "stop")],
        [_btn("⏪ −20s", "seek:-20"), _btn("🔄 𝐑ᴇғʀᴇsʜ", "refresh"), _btn("+20s ⏩", "seek:20")],
        [_btn("⏮️ 𝐏ʀᴇᴠ", "previous"), _btn("📜 𝐐ᴜᴇᴜᴇ", "queue"), _btn("🔀 sʜᴜғғʟᴇ", "shuffle")],
        [_btn("🔁 𝐋ᴏᴏᴘ", "loop"), _btn("⭐ 𝐅ᴀᴠ", "favorite"), _btn("🎚️ 𝐌ᴏᴅᴇ", "mode")],
        [_btn("🎛️ 𝐀ᴜᴅɪᴏ 𝐅𝐗 𝐋ᴀʙ", "effects:0")],
        [_btn("♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ", "auto"), _btn("🔉 −", "voldown"), _btn("🔊 +", "volup")],
        [_btn("🧹 𝐂ʟᴇᴀʀ", "clear"), _btn("⚡ 𝐏ɪɴɢ", "ping"), _btn("👑 𝐃ᴀᴅᴅʏ", "yourdaddy")]
    ])

def effects_keyboard(page=0):
    keys=list(EFFECTS.items()); per=10
    chunk=keys[page*per:(page+1)*per]; rows=[]
    for i in range(0,len(chunk),2):
        rows.append([_btn(style_text(label), f"effect:{k}") for k,(label,_) in chunk[i:i+2]])
    nav=[]
    if page>0: nav.append(_btn("◀️ 𝐏ʀᴇᴠ", f"effects:{page-1}"))
    if (page+1)*per<len(keys): nav.append(_btn("𝐍ᴇxᴛ ▶️", f"effects:{page+1}"))
    if nav: rows.append(nav)
    rows.append([_btn("↩️ 𝐁ᴀᴄᴋ ᴛᴏ 𝐏ʟᴀʏᴇʀ", "now")])
    return InlineKeyboardMarkup(rows)

def welcome(cfg,user):
    return (
        f"<b>╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮</b>\n"
        f"<b>┃  {BRAND}</b>\n"
        f"<b>┃  ⚡ {esc(cfg.bot_name)}</b>\n"
        f"<b>╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        f"<blockquote>🚀 <b>POWER • SPEED • CONTROL</b>\n"
        f"🎧 𝐇ɪɢʜ-ǫᴜᴀʟɪᴛʏ 𝐀ᴜᴅɪᴏ  •  🎥 𝐇𝐃 𝐕ɪᴅᴇᴏ\n"
        f"♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ  •  🎛️ 𝐀ᴜᴅɪᴏ 𝐅𝐗  •  📚 𝐒ᴍᴀʀᴛ 𝐐ᴜᴇᴜᴇ\n"
        f"👤 𝐖ᴇʟᴄᴏᴍᴇ, {esc(user)}</blockquote>\n\n"
        f"<b>⚡ 𝐐ᴜɪᴄᴋ 𝐒ᴛᴀʀᴛ</b>\n"
        f"╰─ <code>/play O Maahi</code>\n"
        f"╰─ <code>/vplay Music Video</code> <i>• up to 720p/30fps cap</i>\n"
        f"╰─ <code>/autoplay Romantic Hindi Songs</code>\n"
        f"╰─ <code>/yourdaddy</code> <i>• owner profile</i>\n\n"
        f"<b>👑 𝐎ᴡɴᴇʀ</b> • <a href=\"https://t.me/Prime_Fearless_45\">{OWNER}</a>\n"
        f"<b>🔐 𝐌ᴏᴅᴇ</b> • <code>FEARLESS / PRO</code>"
    )

def progress_bar(p, width=16):
    if not p.current or not p.current.duration or not p.started_at:
        return "LIVE • ━━━━━━━━━━━━━━━━"
    elapsed=max(0,int(time.monotonic()-p.started_at))
    elapsed=min(elapsed,int(p.current.duration))
    ratio=min(1,elapsed/max(1,p.current.duration))
    filled=min(width,max(0,int(width*ratio)))
    return "━"*filled+"●"+"─"*(width-filled)+f" {elapsed//60}:{elapsed%60:02d}/{duration(p.current.duration)}"

def requester_markup(value):
    if not value:
        return "Unknown"
    text=str(value).strip()
    raw=html.unescape(text)
    match=re.fullmatch(r'<a\s+href=["\']?tg://user\?id=(\d+)["\']?[^>]*>(.*?)</a>',raw,flags=re.I|re.S)
    if match:
        uid,display=match.groups()
        display=re.sub(r'<[^>]+>','',html.unescape(display)).strip() or "User"
        return f'<a href="tg://user?id={uid}">{esc(display)}</a>'
    return esc(text)

def player_text(p,name):
    auto=f"ON • {esc(p.autoplay_topic)}" if p.autoplay and p.autoplay_topic else ("ON" if p.autoplay else "OFF")
    effect=getattr(p,"effect","normal")
    effect_name=EFFECTS.get(effect,("Normal",""))[0]
    speed=getattr(p,"speed",1.0)
    if not p.current:
        return (
            f"<b>╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮</b>\n"
            f"<b>┃  ⚡ 𝐏ʟᴀʏᴇʀ 𝐑ᴇᴀᴅʏ</b>\n"
            f"<b>╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯</b>\n\n"
            f"🟢 <b>ENGINE</b> <code>READY</code>\n"
            f"🎚️ <b>FX</b> <code>{esc(effect_name)}</code>   ⚡ <b>SPEED</b> <code>{speed:.2f}x</code>\n"
            f"📚 <b>QUEUE</b> <code>{len(p.queue)}</code>   ♾️ <b>AUTO</b> <code>{auto}</code>\n\n"
            f"<blockquote>{POWER}\n🎧 /play • 🎥 /vplay • 👑 /yourdaddy</blockquote>\n"
            f"<b>{BRAND}</b>"
        )
    t=p.current
    is_video=bool(getattr(p,"video",False))
    mode="🎥 𝐕ɪᴅᴇᴏ • <code>720p / 30fps cap</code>" if is_video else "🎧 𝐀ᴜᴅɪᴏ • <code>HQ</code>"
    state="⏸️ 𝐏ᴀᴜsᴇᴅ" if p.paused else "▶️ 𝐏ʟᴀʏɪɴɢ"
    return (
        f"<b>╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮</b>\n"
        f"<b>┃  {state}</b>  <i>• {mode}</i>\n"
        f"<b>┃  🎵 {esc(t.title[:120])}</b>\n"
        f"<b>╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        f"⏱️ <code>{progress_bar(p)}</code>\n"
        f"👤 <b>REQUESTED BY</b> • {requester_markup(t.requested_by)}\n"
        f"🔊 <b>VOLUME</b> <code>{p.volume}%</code>   📚 <b>QUEUE</b> <code>{len(p.queue)}</code>\n"
        f"🎛️ <b>FX</b> <code>{esc(effect_name)}</code>   ⚡ <b>SPEED</b> <code>{speed:.2f}x</code>\n"
        f"🔁 <b>LOOP</b> <code>{'ON' if p.loop else 'OFF'}</code>   ♾️ <b>AUTO</b> <code>{auto}</code>\n\n"
        f"<blockquote>⚡ <b>PRIME ENGINE</b> • <code>FAST / STABLE / PRO</code></blockquote>\n"
        f"<b>{BRAND}</b>"
    )

def help_text(name):
    return f"""<b>╭━━━━━━━━━━━━━━━━━━━━━━━━━━╮</b>
<b>┃  {BRAND}</b>
<b>┃  📖 𝐂ᴏᴍᴍᴀɴᴅ 𝐂ᴇɴᴛᴇʀ</b>
<b>╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯</b>

<b>🎧 𝐏ʟᴀʏʙᴀᴄᴋ</b>
<code>/play &lt;song&gt;</code> • audio
<code>/vplay &lt;video&gt;</code> • video up to 720p/30fps cap
<code>/pause</code> <code>/resume</code> <code>/skip [N]</code> <code>/stop</code>
<code>/queue</code> <code>/now</code> <code>/clear</code> <code>/remove 2</code>
<code>/shuffle</code> <code>/loop</code> <code>/volume 0-200</code> <code>/mute</code>

<b>♾️ 𝐃ɪsᴄᴏᴠᴇʀʏ</b>
<code>/search song</code> • search &amp; select
<code>/playnext song</code> • queue next
<code>/discover topic</code> • fresh discovery
<code>/radio topic</code> • continuous discovery

<b>🎛️ 𝐅𝐗 𝐋ᴀʙ</b>
<code>/effect bass_boost</code> • 30+ presets
<code>/settings</code> <code>/features</code> <code>/health</code> <code>/stats</code>

<b>👑 𝐎ᴡɴᴇʀ 𝐙ᴏɴᴇ</b>
<code>/yourdaddy</code> • owner profile + attitude
<code>/approvegc</code> <code>/revoke_gc</code> <code>/clone</code> <code>/clones</code>

<blockquote>🔐 Group playback remains locked until owner approval.
⚡ Built for Telegram Voice Chats.
🚀 PRIME × BEATS • FEARLESS MODE</blockquote>"""

# Optional helpers used by existing callers in some versions.
def frame(title:str, lines:list[str], footer:bool=True)->str:
    tail="\n\n❏ ʀᴇsᴛᴀʀᴛ ʏᴏᴜʀ ʙᴏᴛ — ᴅᴏɴᴇ! ✅" if footer else ""
    return f"<b>╭━━━━━━━━━━━━━━━━━━━━╮</b>\n<b>┃ {style_text(title)}</b>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n{POWER}\n" + "\n".join(lines) + tail + f"\n\n{BRAND}"
