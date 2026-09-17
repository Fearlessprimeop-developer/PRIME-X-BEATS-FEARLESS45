from __future__ import annotations
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .youtube import duration
from .effects import EFFECTS
import re, time, html

# FEARLESS signature typography requested by the owner.
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
    # Exact visual family: first letter bold, remaining lowercase letters small-cap.
    m=re.match(r"([^A-Za-z]*)([A-Za-z])(.*)$", word)
    if not m: return word
    pre, first, rest=m.groups()
    out=pre+_BOLD.get(first.upper(), first)
    for ch in rest:
        out += _SMALL.get(ch.lower(), ch) if ch.isalpha() else ch
    return out

def style_text(text:str)->str:
    """Apply FEARLESS typography while preserving HTML tags, entities and code blocks."""
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
        [InlineKeyboardButton("🟣 👑 𝐎ᴡɴᴇʀ",url="https://t.me/Prime_Fearless_45"),
         InlineKeyboardButton("🟢 💬 sᴜᴘᴘᴏʀᴛ",url="https://t.me/SPARK_X_NETWORK")],
        [InlineKeyboardButton("🟢 📢 𝐂ʜᴀɴɴᴇʟ",url="https://t.me/SPARK_X_NETWORK_OP"),
         InlineKeyboardButton("🔵 ⚡ 𝐎ғғɪᴄɪᴀʟ",url="https://t.me/Prime_Arrived")]
    ])

def home_keyboard(cfg):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 🎧 𝐏ʟᴀʏ",callback_data="help:play"),InlineKeyboardButton("🔵 📜 𝐐ᴜᴇᴜᴇ",callback_data="queue")],
        [InlineKeyboardButton("🟣 ▶️ 𝐍ᴏᴡ 𝐏ʟᴀʏɪɴɢ",callback_data="now"),InlineKeyboardButton("🟡 ♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ",callback_data="auto")],
        [InlineKeyboardButton("🟢 🎙️ 𝐒ᴛᴀʀᴛ 𝐕𝐂",callback_data="startvc")],
        [InlineKeyboardButton("🟡 ⏸️ 𝐏ᴀᴜsᴇ",callback_data="pause"),InlineKeyboardButton("🔵 ⏭️ 𝐒ᴋɪᴘ",callback_data="skip"),InlineKeyboardButton("🔴 ⏹️ sᴛᴏᴘ",callback_data="stop")],
        [InlineKeyboardButton("🟣 🔀 sʜᴜғғʟᴇ",callback_data="shuffle"),InlineKeyboardButton("🟡 🔁 𝐋ᴏᴏᴘ",callback_data="loop")],
        [InlineKeyboardButton("🔊 ᴠᴏʟ −",callback_data="voldown"),InlineKeyboardButton("🔊 ᴠᴏʟ +",callback_data="volup"),InlineKeyboardButton("🔇 ᴍᴜᴛᴇ",callback_data="mute")],
        [InlineKeyboardButton("🟣 🎛️ 𝐀ᴜᴅɪᴏ 𝐄ғғᴇᴄᴛs",callback_data="effects:0"),InlineKeyboardButton("🔵 📖 𝐇ᴇʟᴘ",callback_data="help"),InlineKeyboardButton("🟢 ⚡ 𝐏ɪɴɢ",callback_data="ping")],
        [InlineKeyboardButton("🟢 🌐 sᴜᴘᴘᴏʀᴛ & 𝐋ɪɴᴋs",callback_data="links")]
    ])

def player_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟡 ⏸️ 𝐏ᴀᴜsᴇ",callback_data="pause"),InlineKeyboardButton("🟢 ▶️ 𝐑ᴇsᴜᴍᴇ",callback_data="resume"),InlineKeyboardButton("🔵 ⏭️ 𝐒ᴋɪᴘ",callback_data="skip"),InlineKeyboardButton("🔴 ⏹️ sᴛᴏᴘ",callback_data="stop")],
        [InlineKeyboardButton("⏪ −20s",callback_data="seek:-20"),InlineKeyboardButton("🔵 🔄 𝐑ᴇғʀᴇsʜ",callback_data="refresh"),InlineKeyboardButton("+20s ⏩",callback_data="seek:20")],
        [InlineKeyboardButton("🟣 ⏮️ 𝐏ʀᴇᴠ",callback_data="previous"),InlineKeyboardButton("🔵 📜 𝐐ᴜᴇᴜᴇ",callback_data="queue"),InlineKeyboardButton("🟣 🔀 sʜᴜғғʟᴇ",callback_data="shuffle")],
        [InlineKeyboardButton("🟡 🔁 𝐋ᴏᴏᴘ",callback_data="loop"),InlineKeyboardButton("🟢 ⭐ 𝐅ᴀᴠ",callback_data="favorite"),InlineKeyboardButton("🔵 🎚️ 𝐌ᴏᴅᴇ",callback_data="mode")],
        [InlineKeyboardButton("🟣 🎛️ 𝐀ᴜᴅɪᴏ 𝐄ғғᴇᴄᴛs",callback_data="effects:0")],
        [InlineKeyboardButton("🟡 ♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ",callback_data="auto"),InlineKeyboardButton("🔉 −",callback_data="voldown"),InlineKeyboardButton("🔊 +",callback_data="volup")],
        [InlineKeyboardButton("🔴 🧹 𝐂ʟᴇᴀʀ",callback_data="clear"),InlineKeyboardButton("🟢 ⚡ 𝐏ɪɴɢ",callback_data="ping")]
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
        "<b>┃ 🎛 39+ 𝐀ᴜᴅɪᴏ 𝐅𝐗 • 𝐒ᴍᴀʀᴛ 𝐐ᴜᴇᴜᴇ</b>\n"
        f"<b>┃ 👤 𝐖ᴇʟᴄᴏᴍᴇ, {esc(user)}</b>\n"
        "<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        f"<blockquote>{POWER}\n❏ ʙᴜɪʟᴛ ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs ᯤ\n{DONE}</blockquote>\n\n"
        "<b>🚀 𝐐ᴜɪᴄᴋ sᴛᴀʀᴛ</b>\n<code>/approvegc</code> • 𝐎ᴡɴᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ\n<code>/play O Maahi</code>\n<code>/vplay music video</code>\n<code>/autoplay Romantic Hindi Songs</code>\n<code>/radio Romantic Hindi Songs</code> • ᴄᴏɴᴛɪɴᴜᴏᴜs ᴅɪsᴄᴏᴠᴇʀʏ\n<code>/discover topic</code> • ғɪʟʟ ғʀᴇsʜ ʀᴇsᴜʟᴛs"
    )

def progress_bar(p, width=14):
    if not p.current or not p.current.duration or not p.started_at: return "LIVE"
    elapsed=max(0,int(time.monotonic()-p.started_at)); elapsed=min(elapsed,int(p.current.duration))
    ratio=min(1,elapsed/max(1,p.current.duration)); filled=int(width*ratio)
    return "━"*filled+"●"+"─"*(width-filled)+f" {elapsed//60}:{elapsed%60:02d}/{duration(p.current.duration)}"

def requester_markup(value):
    """Render a clean clickable Telegram user mention.

    The stored value may come from an older player state and can therefore be
    either a normal username/name or an HTML mention. Normalize both forms so
    the chat shows only the display name while the name itself remains clickable.
    """
    if not value:
        return "Unknown"

    text=str(value).strip()
    if not text:
        return "Unknown"

    # Accept both correctly quoted and older unquoted tg://user anchors.
    raw=html.unescape(text)
    match=re.fullmatch(r'<a\s+href=["\']?tg://user\?id=(\d+)["\']?[^>]*>(.*?)</a>',raw,flags=re.I|re.S)
    if match:
        uid,display=match.groups()
        # The visible part is always the user's display name, never @username.
        display=re.sub(r'<[^>]+>','',html.unescape(display)).strip() or "User"
        return f'<a href="tg://user?id={uid}">{esc(display)}</a>'

    # If a previous version stored an escaped anchor, recover it instead of
    # exposing literal <a href=...> markup in the player message.
    escaped=html.unescape(text)
    match=re.fullmatch(r'<a\s+href=["\']?tg://user\?id=(\d+)["\']?[^>]*>(.*?)</a>',escaped,flags=re.I|re.S)
    if match:
        uid,display=match.groups()
        display=re.sub(r'<[^>]+>','',html.unescape(display)).strip() or "User"
        return f'<a href="tg://user?id={uid}">{esc(display)}</a>'

    return esc(text)

def player_text(p,name):
    auto=f"ON • {esc(p.autoplay_topic)}" if p.autoplay and p.autoplay_topic else ("ON" if p.autoplay else "OFF")
    effect=getattr(p,"effect","normal"); effect_name=EFFECTS.get(effect,("Normal",""))[0]
    if not p.current:
        return (f"<b>╭━━〔 {BRAND} 〕━━╮</b>\n"
                f"┃ 🟢 <b>𝐏ʟᴀʏᴇʀ 𝐑ᴇᴀᴅʏ</b>\n┃ ♾️ 𝐀ᴜᴛᴏ: <code>{auto}</code>\n"
                f"┃ 🎛 𝐅𝐗: <code>{esc(effect_name)}</code>\n┃ ⚡ sᴘᴇᴇᴅ: <code>{getattr(p,'speed',1.0):.2f}x</code>\n"
                f"┃ 📚 𝐐ᴜᴇᴜᴇ: <code>{len(p.queue)}</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n\n{POWER}")
    t=p.current; mode="🎥 𝐕ɪᴅᴇᴏ" if getattr(p,"video",False) else "🎧 𝐀ᴜᴅɪᴏ"; state="⏸️ 𝐏ᴀᴜsᴇᴅ" if p.paused else "▶️ 𝐏ʟᴀʏɪɴɢ"
    return f"<b>╭━━〔 {BRAND} 〕━━╮</b>\n┃ {state} • {mode}\n┃ 🎵 <b>{esc(t.title)}</b>\n┃ ⏱ <code>{progress_bar(p)}</code>\n┃ 👤 {requester_markup(t.requested_by)}\n┃ 🔊 <code>{p.volume}%</code> • 📚 <code>{len(p.queue)}</code>\n┃ 🎛 {esc(effect_name)}\n┃ 🔁 𝐋ᴏᴏᴘ: <code>{'ON' if p.loop else 'OFF'}</code> • ♾️ 𝐀ᴜᴛᴏ: <code>{auto}</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n\n{POWER}"

def help_text(name):
    return f"""<b>{BRAND}</b>\n\n{POWER}\n\n<b>🎧 𝐏ʟᴀʏʙᴀᴄᴋ</b>\n<code>/play</code> <code>/vplay</code> <code>/pause</code> <code>/resume</code> <code>/nleft</code> <code>/skip [N]</code> <code>/stopsong</code> <code>/stop</code>\n<code>/queue [page]</code> <code>/now</code> <code>/nowplaying</code> <code>/clear</code> <code>/clearqueue</code> <code>/remove 2</code> <code>/jump 3</code>\n<code>/shuffle</code> <code>/loop</code> <code>/looptrack</code> <code>/loopqueue</code> <code>/loopoff</code> <code>/volume 0-200</code> <code>/mute</code> <code>/unmute</code>\n\n<b>♾️ 𝐀ᴜᴛᴏᴘʟᴀʏ</b>\n<code>/autoplay Romantic Hindi Songs</code>\n<code>/radio Romantic Hindi Songs</code> • ᴄᴏɴᴛɪɴᴜᴏᴜs ᴅɪsᴄᴏᴠᴇʀʏ\n<code>/discover topic</code> • ғɪʟʟ ғʀᴇsʜ ʀᴇsᴜʟᴛs\n\n<b>🎛 𝐄ғғᴇᴄᴛs</b>\n<code>/effect bass_boost</code> • 30+ ᴘʀᴇsᴇᴛs\n\n<b>🛠 𝐃ɪsᴄᴏᴠᴇʀʏ & 𝐓ᴏᴏʟs</b>\n<code>/search song</code> <code>/playnext song</code> <code>/lyrics song</code> <code>/discover topic</code> <code>/radio topic</code>\n<code>/ping</code> <code>/stats</code> <code>/history</code> <code>/health</code> <code>/settings</code> <code>/features</code>\n\n<b>👑 𝐎ᴡɴᴇʀ</b>\n<code>/approvegc</code> <code>/revoke_gc</code> <code>/clone</code> <code>/clones</code>\n\n<blockquote>🛡 ᴘʟᴀʏʙᴀᴄᴋ ɪs ʟᴏᴄᴋᴇᴅ ᴜɴᴛɪʟ ᴛʜᴇ ᴍᴀɪɴ ᴏᴡɴᴇʀ ᴀᴘᴘʀᴏᴠᴇs ᴛʜᴇ ɢʀᴏᴜᴘ.\n⚡ ᴀᴜᴛᴏᴘʟᴀʏ ᴜsᴇs ᴄᴜʀᴀᴛᴇᴅ + ʟɪᴠᴇ ᴅɪsᴄᴏᴠᴇʀʏ ᴀɴᴅ ᴋᴇᴇᴘs ʀᴇғɪʟʟɪɴɢ ᴛʜᴇ ǫᴜᴇᴜᴇ.\n\n{DONE}</blockquote>"""
