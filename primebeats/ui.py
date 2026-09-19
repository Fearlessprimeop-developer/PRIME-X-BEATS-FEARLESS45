from __future__ import annotations
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .youtube import duration
from .effects import EFFECTS
import re, time, html

BRAND = "⚝ 𝐅ᴇᴀʀʟᴇss × 𝐌ᴜsɪᴄ ᯤ"
SUB = "⚡ ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ • ᴘʀᴏ"
OWNER = "👑 @Prime_Fearless_45"

_SMALL = str.maketrans({
    "a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ғ","g":"ɢ","h":"ʜ","i":"ɪ","j":"ᴊ","k":"ᴋ","l":"ʟ","m":"ᴍ",
    "n":"ɴ","o":"ᴏ","p":"ᴘ","q":"ǫ","r":"ʀ","s":"s","t":"ᴛ","u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x","y":"ʏ","z":"ᴢ"
})
_BOLD = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ","𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"))

def esc(s:str)->str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _word_style(word:str)->str:
    m=re.match(r"([^A-Za-z]*)([A-Za-z])(.*)$",word)
    if not m: return word
    pre,first,rest=m.groups()
    out=pre+_BOLD.get(first.upper(),first)
    for ch in rest:
        out += _SMALL.get(ch.lower(),ch) if ch.isalpha() else ch
    return out

def style_text(text:str)->str:
    """Apply light FEARLESS typography without corrupting HTML/code."""
    if not text: return text
    parts=re.split(
        r'(<code>.*?</code>|<pre>.*?</pre>|https?://\S+|t\.me/\S+|<[^>]+>|&(?:amp|lt|gt|quot|#\d+);)',
        text,flags=re.S|re.I
    )
    out=[]
    for part in parts:
        low=part.lower()
        protected=(
            (low.startswith("<code>") and low.endswith("</code>")) or
            (low.startswith("<pre>") and low.endswith("</pre>")) or
            (part.startswith("<") and part.endswith(">")) or
            (low.startswith("&") and low.endswith(";")) or
            low.startswith(("http://","https://","t.me/"))
        )
        out.append(part if protected else re.sub(
            r"[A-Za-z][A-Za-z'’+×/-]*",
            lambda m:_word_style(m.group(0)),part
        ))
    return "".join(out)

def _top(title:str,icon:str="✦")->str:
    return f"<b>{icon} {style_text(title)}</b>\n<blockquote>{SUB}</blockquote>"

def links(cfg):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Owner",url="https://t.me/Prime_Fearless_45"),
         InlineKeyboardButton("💬 Support",url="https://t.me/SPARK_X_NETWORK")],
        [InlineKeyboardButton("📢 Channel",url="https://t.me/SPARK_X_NETWORK_OP"),
         InlineKeyboardButton("⚡ Official",url="https://t.me/Prime_Arrived")],
        [InlineKeyboardButton("🔥 Your Daddy",callback_data="yourdaddy"),
         InlineKeyboardButton("◀️ Main Menu",callback_data="help")]
    ])

def home_keyboard(cfg):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 PLAY",callback_data="help:play"),
         InlineKeyboardButton("🎥 VPLAY",callback_data="help:vplay")],
        [InlineKeyboardButton("▶️ NOW PLAYING",callback_data="now"),
         InlineKeyboardButton("📜 QUEUE",callback_data="queue")],
        [InlineKeyboardButton("⏸ PAUSE",callback_data="pause"),
         InlineKeyboardButton("⏭ SKIP",callback_data="skip"),
         InlineKeyboardButton("⏹ STOP",callback_data="stop")],
        [InlineKeyboardButton("🔀 SHUFFLE",callback_data="shuffle"),
         InlineKeyboardButton("🔁 LOOP",callback_data="loop"),
         InlineKeyboardButton("♾ AUTO",callback_data="auto")],
        [InlineKeyboardButton("🔊 VOL −",callback_data="voldown"),
         InlineKeyboardButton("🔊 VOL +",callback_data="volup"),
         InlineKeyboardButton("🔇 MUTE",callback_data="mute")],
        [InlineKeyboardButton("🎛 FX LAB",callback_data="effects:0"),
         InlineKeyboardButton("📖 HELP",callback_data="help"),
         InlineKeyboardButton("⚡ PING",callback_data="ping")],
        [InlineKeyboardButton("👑 YOUR DADDY",callback_data="yourdaddy"),
         InlineKeyboardButton("🌐 LINKS",callback_data="links")]
    ])

def player_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏸ PAUSE",callback_data="pause"),
         InlineKeyboardButton("▶️ RESUME",callback_data="resume"),
         InlineKeyboardButton("⏭ SKIP",callback_data="skip"),
         InlineKeyboardButton("⏹ STOP",callback_data="stop")],
        [InlineKeyboardButton("⏪ 20s",callback_data="seek:-20"),
         InlineKeyboardButton("🔄 REFRESH",callback_data="refresh"),
         InlineKeyboardButton("20s ⏩",callback_data="seek:20")],
        [InlineKeyboardButton("⏮ PREV",callback_data="previous"),
         InlineKeyboardButton("📜 QUEUE",callback_data="queue"),
         InlineKeyboardButton("🔀 SHUFFLE",callback_data="shuffle")],
        [InlineKeyboardButton("🔁 LOOP",callback_data="loop"),
         InlineKeyboardButton("⭐ FAV",callback_data="favorite"),
         InlineKeyboardButton("🎚 MODE",callback_data="mode")],
        [InlineKeyboardButton("🎛 FX LAB",callback_data="effects:0"),
         InlineKeyboardButton("♾ AUTO",callback_data="auto"),
         InlineKeyboardButton("⚡ PING",callback_data="ping")],
        [InlineKeyboardButton("🔊 −",callback_data="voldown"),
         InlineKeyboardButton("🔊 +",callback_data="volup"),
         InlineKeyboardButton("🧹 CLEAR",callback_data="clear")],
        [InlineKeyboardButton("👑 YOUR DADDY",callback_data="yourdaddy")]
    ])

def effects_keyboard(page=0):
    keys=list(EFFECTS.items()); per=10
    chunk=keys[page*per:(page+1)*per]; rows=[]
    for i in range(0,len(chunk),2):
        rows.append([
            InlineKeyboardButton(f"🎛 {label}",callback_data=f"effect:{k}")
            for k,(label,_) in chunk[i:i+2]
        ])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("◀️ PREV",callback_data=f"effects:{page-1}"))
    if (page+1)*per<len(keys): nav.append(InlineKeyboardButton("NEXT ▶️",callback_data=f"effects:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("◀️ BACK TO PLAYER",callback_data="now")])
    return InlineKeyboardMarkup(rows)

def welcome(cfg,user):
    name=esc(user or "there")
    return (
        f"{_top('PRIME × BEATS • MUSIC','⚝')}\n\n"
        f"<b>⚡ {esc(cfg.bot_name)}</b>\n"
        f"👤 Welcome, <b>{name}</b>\n\n"
        "<b>┌─ ENGINE STATUS</b>\n"
        "│ 🟢 Audio engine online\n"
        "│ 🔵 Video engine • SD 480p output\n"
        "│ 🟣 Smart queue + autoplay\n"
        f"│ 🟡 {len(EFFECTS)}+ audio effects\n"
        "<b>└────────────────</b>\n\n"
        "<b>🚀 QUICK START</b>\n"
        "<code>/play O Maahi</code>\n"
        "<code>/vplay music video</code>\n"
        "<code>/search song name</code>\n"
        "<code>/autoplay Romantic Hindi Songs</code>\n"
        "<code>/yourdaddy</code>\n\n"
        f"<blockquote>{OWNER}\n🛡 Group playback requires owner approval.</blockquote>"
    )

def progress_bar(p,width=12):
    if not p.current or not p.current.duration or not p.started_at: return "LIVE"
    elapsed=max(0,int(time.monotonic()-p.started_at))
    elapsed=min(elapsed,int(p.current.duration))
    ratio=min(1,elapsed/max(1,p.current.duration))
    filled=int(width*ratio)
    return "━"*filled+"●"+"─"*(width-filled)+f"  {elapsed//60}:{elapsed%60:02d} / {duration(p.current.duration)}"

def requester_markup(value):
    if not value: return "Unknown"
    raw=html.unescape(str(value).strip())
    match=re.fullmatch(r'<a\s+href=["\']?tg://user\?id=(\d+)["\']?[^>]*>(.*?)</a>',raw,flags=re.I|re.S)
    if match:
        uid,display=match.groups()
        display=re.sub(r"<[^>]+>","",html.unescape(display)).strip() or "User"
        return f'<a href="tg://user?id={uid}">{esc(display)}</a>'
    return esc(raw)

def player_text(p,name):
    auto=f"ON • {esc(p.autoplay_topic)}" if p.autoplay and p.autoplay_topic else ("ON" if p.autoplay else "OFF")
    effect=esc(EFFECTS.get(getattr(p,"effect","normal"),("Normal",""))[0])
    if not p.current:
        return (
            f"{_top('PLAYER • READY','⚡')}\n\n"
            "<b>🟢 ENGINE ONLINE</b>\n"
            f"🎛 FX  <code>{effect}</code>\n"
            f"⚡ SPEED  <code>{getattr(p,'speed',1.0):.2f}x</code>\n"
            f"📚 QUEUE  <code>{len(p.queue)}</code>\n"
            f"♾ AUTO  <code>{auto}</code>\n\n"
            f"<blockquote>{OWNER}\n🎧 Use /play or /vplay to start.</blockquote>\n"
            f"<b>{BRAND}</b>"
        )
    t=p.current
    mode="🎥 VIDEO • SD 480p" if getattr(p,"video",False) else "🎧 AUDIO • HQ"
    state="⏸ PAUSED" if p.paused else "▶️ PLAYING"
    return (
        f"{_top(f'{state} • {mode}','⚡')}\n\n"
        f"🎵 <b>{esc(t.title)}</b>\n"
        f"⏱ <code>{progress_bar(p)}</code>\n"
        f"👤 <b>REQUESTED BY</b> • {requester_markup(t.requested_by)}\n\n"
        f"🔊 <b>{p.volume}%</b>   📚 <b>{len(p.queue)}</b>\n"
        f"🎛 <b>{effect}</b>   ⚡ <b>{getattr(p,'speed',1.0):.2f}x</b>\n"
        f"🔁 LOOP <b>{'ON' if p.loop else 'OFF'}</b>   ♾ AUTO <b>{auto}</b>\n\n"
        "<blockquote>⚡ PRIME ENGINE\nᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ</blockquote>\n"
        f"<b>{BRAND}</b>"
    )

def help_text(name):
    return (
        f"{_top('COMMAND CENTER','📖')}\n\n"
        "<b>🎧 PLAYBACK</b>\n"
        "<code>/play</code> • <code>/vplay</code> • <code>/pause</code> • <code>/resume</code>\n"
        "<code>/skip [N]</code> • <code>/stop</code> • <code>/stopsong</code>\n"
        "<code>/queue</code> • <code>/now</code> • <code>/clear</code> • <code>/remove N</code>\n"
        "<code>/shuffle</code> • <code>/loop</code> • <code>/volume 0-200</code>\n\n"
        "<b>🔎 DISCOVERY</b>\n"
        "<code>/search song</code> • <code>/lyrics song</code>\n"
        "<code>/autoplay topic</code> • <code>/radio topic</code> • <code>/discover topic</code>\n\n"
        "<b>🎛 FX / TOOLS</b>\n"
        "<code>/effect bass_boost</code> • <code>/ping</code> • <code>/stats</code>\n"
        "<code>/history</code> • <code>/health</code> • <code>/settings</code> • <code>/features</code>\n\n"
        "<b>👑 OWNER</b>\n"
        "<code>/yourdaddy</code> • <code>/approvegc</code> • <code>/revoke_gc</code> • <code>/clone</code>\n\n"
        f"<blockquote>{OWNER}\n🛡 Group playback remains owner-approved.</blockquote>"
    )
