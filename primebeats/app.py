from __future__ import annotations
import asyncio, logging, time, inspect, secrets
from contextlib import suppress
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError
from pyrogram.types import Message, CallbackQuery, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from pytgcalls import PyTgCalls, filters as call_filters
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality, GroupCallParticipant
from .config import Config
from .state import PlayerStore, Track
from .youtube import resolve, resolve_playlist, search_results, duration, topic_seeds, discover_topic
from .ui import home_keyboard, player_keyboard, effects_keyboard, welcome, player_text, song_caption, thumbnail_url, help_text, links, esc, style_text
from .effects import EFFECTS
from .web import start_web
from .clone import CloneManager
from .approvals import ApprovalStore
from .library import LibraryStore
from .features import FEATURES, EFFECT_ALIASES

log=logging.getLogger("primebeats")

class StyledClient(Client):
    """Bot client that applies the FEARLESS typography to all normal bot text."""
    @staticmethod
    def _styled(value):
        return style_text(value) if isinstance(value, str) else value

    async def send_message(self, chat_id, text=None, *args, **kwargs):
        return await super().send_message(chat_id, self._styled(text), *args, **kwargs)

    async def edit_message_text(self, chat_id, message_id, text, *args, **kwargs):
        return await super().edit_message_text(chat_id, message_id, self._styled(text), *args, **kwargs)

    async def send_photo(self, chat_id, photo, caption=None, *args, **kwargs):
        return await super().send_photo(chat_id, photo, caption=self._styled(caption), *args, **kwargs)

async def maybe(value):
    return await value if inspect.isawaitable(value) else value

class PrimeBeats:
    def __init__(self):
        self.cfg=Config.from_env()
        self.store=PlayerStore(self.cfg.default_volume,self.cfg.autoplay_default)
        self.approvals=ApprovalStore()
        self.library=LibraryStore()
        self.bot=StyledClient("prime_x_beats_bot",api_id=self.cfg.api_id,api_hash=self.cfg.api_hash,bot_token=self.cfg.bot_token)
        self.assistant=Client("prime_x_beats_assistant",api_id=self.cfg.api_id,api_hash=self.cfg.api_hash,session_string=self.cfg.assistant_session)
        self.calls=PyTgCalls(self.assistant)
        self.clone=CloneManager(self.cfg.api_id,self.cfg.api_hash,self.cfg.owner_id)
        self.started=time.monotonic(); self._clone_waiting=set(); self._autoplay_tasks={}
        self.web_runner=None; self._search_cache={}; self._transitioning=set(); self._manual_stop_until={}; self._register()

    async def is_owner(self,m): return bool(m.from_user and m.from_user.id==self.cfg.owner_id)
    async def is_admin(self,m):
        if await self.is_owner(m):return True
        if not m.from_user:return False
        try:
            x=await self.bot.get_chat_member(m.chat.id,m.from_user.id)
            return x.status in (ChatMemberStatus.OWNER,ChatMemberStatus.ADMINISTRATOR)
        except RPCError:return False
    async def require_admin(self,m):
        if not await self.is_admin(m):
            await m.reply_text("🛡 <b>ADMIN ONLY</b>\nOnly group admins can control playback.");return False
        if not self.approvals.is_approved(m.chat.id):
            await m.reply_text(self.lock_message());return False
        return True
    def lock_message(self):
        return ("🔐 <b>PRIME × BEATS IS LOCKED</b>\n\n"
                "<blockquote>This bot was added here, but the main owner has not approved this chat yet.</blockquote>\n"
                "👑 <b>Owner:</b> @Prime_Fearless_45\n"
                "⚡ Ask the owner to approve this group with <code>/approvegc</code>.\n\n"
                "🛡 Playback and VC controls stay disabled until approval.")
    async def owner_only(self,m):
        if await self.is_owner(m):return True
        await m.reply_text("⛔ <b>OWNER ONLY</b>\nThis command can only be used by @Prime_Fearless_45.");return False

    @staticmethod
    def _is_group_or_channel(m) -> bool:
        """Accept Pyrogram/Pyrofork chat-type representations safely."""
        value=getattr(getattr(m, "chat", None), "type", None)
        value=getattr(value, "value", value)
        return str(value).lower() in {"group", "supergroup", "channel"}

    @staticmethod
    def _requester_name(user) -> str:
        """Plain requester text; avoids leaking Telegram tg://user HTML into captions."""
        if not user:
            return "Unknown"
        username = getattr(user, "username", None)
        if username:
            return "@" + username
        return getattr(user, "first_name", None) or "Unknown"

    def _make_media(self, track, video: bool, effect: str, speed: float = 1.0, start_at: float = 0.0):
        video=bool(video or getattr(track,"video",False))
        ff = self._audio_filter(effect, speed)
        ffmpeg = ""
        pre = f"-ss {max(0.0, float(start_at)):.3f}" if start_at > 0 else ""
        post = f"-af {ff}" if ff else ""
        if pre or post:
            ffmpeg = (pre + " -atmid " + post).strip()
        kwargs = {}
        if ffmpeg:
            kwargs["ffmpeg_parameters"] = ffmpeg
        if video:
            return MediaStream(track.stream_url, AudioQuality.HIGH, VideoQuality.HD_720p, **kwargs)
        kwargs["video_flags"] = MediaStream.Flags.IGNORE
        return MediaStream(track.stream_url, AudioQuality.HIGH, **kwargs)

    @staticmethod
    def _atempo_chain(value: float) -> str:
        """Build valid FFmpeg atempo stages (each stage must stay in 0.5..2.0)."""
        value=max(0.05,min(8.0,float(value)))
        parts=[]
        while value>2.0:
            parts.append("atempo=2.0"); value/=2.0
        while value<0.5:
            parts.append("atempo=0.5"); value/=0.5
        if abs(value-1.0)>0.0005: parts.append(f"atempo={value:.6f}")
        return ",".join(parts)

    def _audio_filter(self, effect: str, speed: float) -> str:
        base=EFFECTS.get(effect,("", ""))[1]
        if abs(speed-1.0)<0.0005:
            return base
        import re
        m=re.search(r"(?:^|,)atempo=([0-9.]+)", base)
        if m:
            old=float(m.group(1)); combined=old*float(speed)
            repl=self._atempo_chain(combined)
            base=re.sub(r"(?:^|,)atempo=[0-9.]+", lambda _: ("," if _.group(0).startswith(",") else "")+repl, base, count=1)
            return base
        extra=self._atempo_chain(speed)
        return f"{base},{extra}" if base and extra else (base or extra)

    async def _ensure_voice_chat(self, chat_id: int):
        """Create the group voice chat automatically using the assistant user account.

        Telegram only allows users (not Bot API identities) to create a group call, so
        the assistant session performs this operation. If a call already exists, that
        is treated as success and PyTgCalls will join it.
        """
        try:
            from pyrogram.raw.functions.phone import CreateGroupCall
            peer = await self.assistant.resolve_peer(chat_id)
            await self.assistant.invoke(
                CreateGroupCall(
                    peer=peer,
                    random_id=secrets.randbelow(2_147_483_647) + 1,  # Telegram TL `int` is signed 32-bit
                    title=f"{self.cfg.bot_name} • Music",
                )
            )
            log.info("voice chat created automatically: chat=%s", chat_id)
            return True
        except Exception as e:
            text = str(e).upper()
            if "GROUPCALL_ALREADY_EXISTS" in text:
                return True
            log.exception("could not create voice chat automatically: chat=%s", chat_id)
            raise

    async def stream(self,chat_id,track,video=False,effect=None,start_at:float=0.0,refresh=False):
        """Start a PyTgCalls stream. Reuse an already-resolved direct URL for fast first play."""
        p=self.store.get(chat_id)
        old_state=(p.current,p.paused,p.muted,p.video,p.effect,p.started_at)
        fresh=track
        if refresh or not getattr(track,"stream_url",None):
            fresh=await asyncio.wait_for(resolve(track.webpage_url,track.requested_by,video),timeout=35)
        await self._ensure_voice_chat(chat_id)
        video=bool(video or getattr(track,"video",False))
        effect_key=effect or getattr(p,"effect","normal")
        speed=float(getattr(p,"speed",1.0))
        ff=self._audio_filter(effect_key,speed)
        fresh.stream_url = fresh.stream_url or track.stream_url
        media=self._make_media(fresh,video,effect_key,speed,start_at)
        try:
            await asyncio.wait_for(maybe(self.calls.play(chat_id,media)), timeout=35)
            with suppress(Exception): await maybe(self.calls.change_volume_call(chat_id,p.volume))
        except Exception:
            # Do not leave the player pointing at a stream that never started.
            p.current,p.paused,p.muted,p.video,p.effect,p.started_at=old_state
            raise
        track.stream_url=fresh.stream_url; track.title=fresh.title; track.duration=fresh.duration; track.thumbnail=fresh.thumbnail
        track.video=bool(video)
        p.current=track; p.paused=False; p.muted=False; p.video=bool(video); p.effect=effect_key
        p.started_at=time.monotonic()-max(0.0,float(start_at))

    async def _restart_current(self,chat_id,position:float|None=None):
        """Rebuild the current media source without leaving the Telegram VC.

        PyTgCalls supports change_stream specifically for switching media without
        reconnecting the voice chat. Effects/seek/refresh use this path first.
        """
        p=self.store.get(chat_id)
        if not p.current: return False
        target=p.current
        pos=0.0 if position is None else max(0.0,float(position))
        if target.duration: pos=min(pos,max(0.0,target.duration-0.5))
        fresh=await asyncio.wait_for(resolve(target.webpage_url,target.requested_by,getattr(target,"video",p.video)),timeout=35)
        fresh.video=getattr(target,"video",p.video)
        media=self._make_media(fresh,getattr(target,"video",p.video),p.effect,float(getattr(p,"speed",1.0)),pos)
        change=getattr(self.calls,"change_stream",None)
        if change is not None:
            await asyncio.wait_for(maybe(change(chat_id,media)),timeout=35)
        else:
            # Compatibility fallback for older PyTgCalls builds. The VC may reconnect.
            await self.stream(chat_id,target,getattr(target,"video",p.video),p.effect,pos,refresh=False)
        target.stream_url=fresh.stream_url
        target.title=fresh.title; target.duration=fresh.duration; target.thumbnail=fresh.thumbnail
        p.started_at=time.monotonic()-pos
        return True

    async def _autofill(self, chat_id, minimum=8):
        p=self.store.get(chat_id)
        if not (p.autoplay and p.autoplay_topic):
            return 0
        if len(p.queue) >= minimum:
            return 0
        exclude={x.webpage_url.lower() for x in p.queue if x.webpage_url}
        exclude.update(x.webpage_url.lower() for x in p.history if x.webpage_url)
        if p.current and p.current.webpage_url:
            exclude.add(p.current.webpage_url.lower())
        exclude.update(p.autoplay_seen)
        found=await discover_topic(p.autoplay_topic,"♾ Autoplay",limit=max(12,minimum+4),exclude=exclude,round_no=p.autoplay_round)
        added=0
        for t in found:
            key=t.webpage_url.lower()
            if key in exclude or key in p.autoplay_seen:
                continue
            if len(p.queue)>=self.cfg.max_queue:
                break
            p.queue.append(t); p.autoplay_seen.add(key); added+=1
        p.autoplay_round += 1
        # Keep the discovery memory bounded; history remains the long-lived de-duplication layer.
        if len(p.autoplay_seen)>600:
            p.autoplay_seen=set(list(p.autoplay_seen)[-300:])
        return added

    async def play_next(self,chat_id):
        p=self.store.get(chat_id)
        async with p.lock:
            attempts=0
            while attempts<3:
                attempts+=1
                nxt=p.current if p.loop and p.current else p.next()
                if not nxt and p.autoplay and p.autoplay_topic:
                    await self._autofill(chat_id,minimum=2)
                    nxt=p.next()
                if not nxt:
                    p.current=None
                    with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)),timeout=5)
                    return False
                old=p.current
                if old and nxt is not old: p.remember(old)
                self._transitioning.add(chat_id)
                try:
                    # Intentional media transition. Ignore the stream_end event emitted
                    # by leave_call so it cannot race and start a second queued track.
                    if old is not None:
                        with suppress(Exception):
                            await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)), timeout=5)
                        await asyncio.sleep(0.20)
                    await asyncio.wait_for(self.stream(chat_id,nxt,getattr(nxt,"video",p.video),p.effect),timeout=45)
                    await self._announce_track(chat_id,nxt,p)
                    if p.autoplay and p.autoplay_topic and len(p.queue)<6:
                        old_task=self._autoplay_tasks.get(chat_id)
                        if not old_task or old_task.done():
                            self._autoplay_tasks[chat_id]=asyncio.create_task(self._autofill(chat_id,minimum=10))
                    return True
                except Exception:
                    log.exception("playback attempt %s failed for chat %s",attempts,chat_id)
                    p.current=None
                    if attempts>=3:
                        with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)),timeout=5)
                        return False
                finally:
                    self._transitioning.discard(chat_id)
            return False

    async def skip_tracks(self, chat_id, count=1):
        """Skip `count` tracks total: current track counts as #1.
        Any remaining queue after the skipped tracks continues normally.
        """
        p=self.store.get(chat_id)
        count=max(1,int(count))
        async with p.lock:
            if not p.current:
                return False, 0
            # Current track is #1. Drop additional queued tracks requested by the user.
            dropped=0
            while dropped < count-1 and p.queue:
                skipped=p.queue.pop(0)
                p.remember(skipped)
                dropped += 1
            self._transitioning.add(chat_id)
            try:
                old=p.current
                p.remember(old)
                p.current=None
                with suppress(Exception):
                    await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)), timeout=5)
                await asyncio.sleep(0.20)
                # Start the next queued/autoplay track. play_next has its own lock, so
                # call the internal implementation directly here to avoid lock nesting.
                return await self._play_next_unlocked(chat_id), dropped + 1
            finally:
                self._transitioning.discard(chat_id)

    async def _play_next_unlocked(self, chat_id):
        p=self.store.get(chat_id)
        attempts=0
        while attempts<3:
            attempts+=1
            nxt=p.next()
            if not nxt and p.autoplay and p.autoplay_topic:
                await self._autofill(chat_id,minimum=2)
                nxt=p.next()
            if not nxt:
                p.current=None
                with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)),timeout=5)
                return False
            self._transitioning.add(chat_id)
            try:
                await asyncio.wait_for(self.stream(chat_id,nxt,getattr(nxt,"video",p.video),p.effect),timeout=45)
                await self._announce_track(chat_id,nxt,p)
                if p.autoplay and p.autoplay_topic and len(p.queue)<6:
                    task=self._autoplay_tasks.get(chat_id)
                    if not task or task.done():
                        self._autoplay_tasks[chat_id]=asyncio.create_task(self._autofill(chat_id,minimum=10))
                return True
            except Exception:
                log.exception("skip-next playback attempt %s failed for chat %s",attempts,chat_id)
                p.current=None
                if attempts>=3:
                    with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)),timeout=5)
                    return False
            finally:
                self._transitioning.discard(chat_id)
        return False

    async def _announce_track(self, chat_id, track, player=None):
        """Send one clean thumbnail-first Now Playing card."""
        p=player or self.store.get(chat_id)
        # Use the dedicated song caption instead of the old live-player block.
        # This prevents duplicated sections and guarantees real newline characters.
        caption=song_caption(track,p,heading="NOW PLAYING")
        thumb=thumbnail_url(track)
        if thumb:
            track.thumbnail=thumb
        try:
            if thumb:
                return await self.bot.send_photo(
                    chat_id,thumb,caption=caption,reply_markup=player_keyboard()
                )
            return await self.bot.send_message(
                chat_id,caption,reply_markup=player_keyboard()
            )
        except Exception:
            # If Telegram rejects the remote thumbnail, keep the same clean caption.
            return await self.bot.send_message(
                chat_id,caption,reply_markup=player_keyboard()
            )

    async def handle_play(self,m,query,video=False):
        if not query:
            await m.reply_text(f"🎧 <b>Usage:</b> <code>/{'vplay' if video else 'play'} &lt;song or YouTube URL&gt;</code>");return
        msg=await m.reply_text("<b>╭━━〔 ⚡ PRIME SEARCH 〕━━╮</b>\n┃ 🔎 Searching YouTube...\n┃ 🧠 Resolving direct media...\n┃ 🎙 Auto-starting Voice Chat...\n┃ 🚀 Preparing VC stream...\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")
        try:
            track=await asyncio.wait_for(resolve(query,self._requester_name(m.from_user),video),timeout=40)
            track.video=bool(video)
            await msg.edit_text(f"<b>╭━━〔 ⚡ PRIME × BEATS 〕━━╮</b>\n┃ 🎵 <b>{track.title[:80]}</b>\n┃ 🎙 Voice Chat: <b>STARTING</b>\n┃ ⚡ Assistant: <b>CONNECTING</b>\n┃ 🚀 Stream: <b>READY</b>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")
            p=self.store.get(m.chat.id)
            # Serialize concurrent play requests for this chat so two commands cannot
            # both observe an empty player and race the native VC engine.
            async with p.lock:
                if p.current:
                    pos=p.add(track,self.cfg.max_queue)
                    await msg.edit_text(f"📥 <b>QUEUED</b>\n\n🎵 {track.title}\n📍 Position: <code>{pos}</code>",reply_markup=player_keyboard());return
                await asyncio.wait_for(self.stream(m.chat.id,track,video,p.effect), timeout=45)
            await msg.delete()
            await self._announce_track(m.chat.id,track,p)
        except Exception as e:
            log.exception("play failed: chat=%s query=%r",m.chat.id,query)
            safe=esc(str(e))[:500]
            await msg.edit_text("⚝ 𝐅ᴇᴀʀʟᴇss ꭗ 𝐌ᴜsɪᴄ ᯤ\n\n🚀 ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ\n❏ <b>ᴘʟᴀʏʙᴀᴄᴋ ғᴀɪʟᴇᴅ</b>\n\n<code>"+safe+"</code>\n\n<blockquote>PRIME × BEATS could not start the assistant stream. Check Render logs for the full traceback.</blockquote>")

    async def reapply_effect(self,chat_id,effect):
        p=self.store.get(chat_id)
        if not p.current:return False
        # Re-resolve the current track and restart cleanly; this avoids in-place stream-switch races.
        track=p.current
        with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat_id)), timeout=5)
        await asyncio.sleep(.25)
        return await asyncio.wait_for(self.stream(chat_id,track,p.video,effect), timeout=45)

    def _register(self):
        @self.bot.on_message(filters.command("start"))
        async def start(_,m): await m.reply_text(welcome(self.cfg,m.from_user.first_name if m.from_user else "there"),reply_markup=home_keyboard(self.cfg))
        @self.bot.on_message(filters.command(["help","commands"]))
        async def help_cmd(_,m): await m.reply_text(help_text(self.cfg.bot_name),reply_markup=home_keyboard(self.cfg))
        @self.bot.on_message(filters.new_chat_members)
        async def added(_,m):
            me=await self.bot.get_me()
            if any(getattr(u,"id",None)==me.id for u in (m.new_chat_members or [])):
                await m.reply_text(self.lock_message(),reply_markup=links(self.cfg))
        @self.bot.on_message(filters.command("approvegc"))
        async def approve(_,m):
            if not await self.owner_only(m):return
            if not self._is_group_or_channel(m):
                await m.reply_text("Use <code>/approvegc</code> inside the group/channel to approve it.");return
            await self.approvals.approve(m.chat.id)
            await m.reply_text("⚝ <b>𝐆ʀᴏᴜᴘ 𝐀ᴘᴘʀᴏᴠᴇᴅ</b> ⚝\n\n🚀 PRIME × BEATS is now unlocked <b>permanently</b> for this chat.\n🎧 Playback • 🎥 Video • ♾ Autoplay • 🎛 Effects are enabled.\n\n🛡 <b>Owner approval is required only once.</b>\n🔓 Use <code>/revoke_gc</code> only if you want to lock it again.")
        @self.bot.on_message(filters.command("revoke_gc"))
        async def revoke(_,m):
            if not await self.owner_only(m):return
            if not self._is_group_or_channel(m):
                await m.reply_text("Use <code>/revoke_gc</code> inside the group/channel.");return
            await self.approvals.revoke(m.chat.id)
            await m.reply_text("🔒 <b>GROUP LOCKED AGAIN.</b>\n\n⚡ Run <code>/approvegc</code> again to unlock it.")
        @self.bot.on_message(filters.command("joinvc"))
        async def joinvc(_,m):
            if not await self.require_admin(m): return
            status=await m.reply_text("<b>╭━━〔 🎙 PRIME VC 〕━━╮</b>\n┃ ⚡ Assistant is starting the Voice Chat...\n┃ 🔐 Checking admin access...\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")
            try:
                await self._ensure_voice_chat(m.chat.id)
                await status.edit_text("<b>╭━━〔 🟢 PRIME VC ONLINE 〕━━╮</b>\n┃ 🎙 Voice Chat: <b>ACTIVE</b>\n┃ 🤖 Assistant: <b>READY</b>\n┃ 🎧 Use <code>/play song</code>\n┃ 🎥 Use <code>/vplay video</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>",reply_markup=player_keyboard())
            except Exception as e:
                log.exception("joinvc failed: chat=%s",m.chat.id)
                await status.edit_text("❌ <b>Could not start Voice Chat</b>\n\n<code>"+esc(str(e))[:500]+"</code>")

        @self.bot.on_message(filters.command("play"))
        async def play(_,m):
            if not self._is_group_or_channel(m): await m.reply_text("❌ Add me to a group or channel first.");return
            if not await self.require_admin(m):return
            q=m.text.split(maxsplit=1)[1] if len(m.text.split(maxsplit=1))>1 else ""
            await self.handle_play(m,q,False)
        @self.bot.on_message(filters.command("vplay"))
        async def vplay(_,m):
            if not self._is_group_or_channel(m):await m.reply_text("❌ Use /vplay in a group/channel.");return
            if not await self.require_admin(m):return
            q=m.text.split(maxsplit=1)[1] if len(m.text.split(maxsplit=1))>1 else ""
            await self.handle_play(m,q,True)
        @self.bot.on_message(filters.command("playlist"))
        async def playlist(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1))>1 else ""
            if not arg:
                await m.reply_text("📚 <b>PLAYLIST IMPORT</b>\nUse <code>/playlist &lt;YouTube playlist URL&gt;</code>")
                return
            status=await m.reply_text("📚 <b>IMPORTING PLAYLIST...</b>\n⚡ Reading track list...\n🧠 Applying queue protection...")
            try:
                items=await resolve_playlist(arg,self._requester_name(m.from_user),self.cfg.playlist_limit)
                p=self.store.get(m.chat.id); added=0
                for t in items:
                    if len(p.queue)>=self.cfg.max_queue: break
                    key=(t.webpage_url or "").lower()
                    if not key: continue
                    if p.current and (p.current.webpage_url or "").lower()==key: continue
                    if any((x.webpage_url or "").lower()==key for x in p.queue): continue
                    p.queue.append(t); added+=1
                if not p.current and p.queue:
                    await self.play_next(m.chat.id)
                await status.edit_text(f"📚 <b>PLAYLIST IMPORTED</b>\n\n📥 Added: <code>{added}</code>\n📜 Queue: <code>{len(p.queue)}</code>\n🛡 Limit: <code>{self.cfg.playlist_limit}</code>",reply_markup=player_keyboard())
            except Exception as e:
                log.warning("playlist import failed: %s",e)
                await status.edit_text("❌ <b>Playlist import failed.</b>\nCheck the URL, playlist visibility, or try a smaller playlist.")

        @self.bot.on_message(filters.command("autoplay"))
        async def autoplay(_,m):
            if not await self.require_admin(m):return
            arg=m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1))>1 else ""
            p=self.store.get(m.chat.id)
            if arg.lower() in {"off","disable"}:p.autoplay=False;p.autoplay_topic="";await m.reply_text("⛔ <b>AUTOPLAY OFF</b>");return
            if arg.lower() in {"on","enable"}:p.autoplay=True;await m.reply_text("♾️ <b>AUTOPLAY ON</b>");return
            if arg.lower()=="next":
                if p.autoplay_topic: await self.play_next(m.chat.id); await m.reply_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
                else: await m.reply_text("Set a topic first: <code>/autoplay Romantic Hindi Songs</code>")
                return
            if not arg:await m.reply_text("♾️ <b>Usage:</b> <code>/autoplay Romantic Hindi Songs</code>");return
            p.autoplay=True;p.autoplay_topic=arg[:120];p.autoplay_round=0;p.autoplay_seen.clear()
            # Prime a real discovery queue: curated anchors + live YouTube search results.
            added=await self._autofill(m.chat.id,minimum=12)
            if not p.current: await self.play_next(m.chat.id)
            await m.reply_text(
                f"♾️ <b>AUTOPLAY ∞ DISCOVERY</b>\n"
                f"🎯 Topic: <code>{arg[:120]}</code>\n"
                f"📡 Fresh discoveries queued: <code>{added}</code>\n"
                "🧠 Mode: <code>CURATED + LIVE SEARCH</code>\n"
                "♾️ Engine: <code>CONTINUOUS DISCOVERY</code>\n\n"
                "<blockquote>Autoplay keeps discovering more matching songs as the queue runs. It is not limited to the built-in seed list.</blockquote>",
                reply_markup=player_keyboard())
        @self.bot.on_message(filters.command("effect"))
        async def effect(_,m):
            if not await self.require_admin(m):return
            key=m.text.split(maxsplit=1)[1].strip().lower() if len(m.text.split(maxsplit=1))>1 else ""
            if key not in EFFECTS: await m.reply_text("🎛 Open effects with <code>/effects</code>.");return
            p=self.store.get(m.chat.id); old_effect=p.effect; p.effect=key
            if p.current:
                try:
                    pos=max(0.0,time.monotonic()-p.started_at); await self._restart_current(m.chat.id,pos)
                except Exception:
                    p.effect=old_effect
                    with suppress(Exception): await self._restart_current(m.chat.id,pos)
                    await m.reply_text("⚠️ <b>Effect could not be applied.</b> Previous effect restored."); return
            await m.reply_text(f"🎛 <b>Effect:</b> {EFFECTS[key][0]}",reply_markup=player_keyboard())
        @self.bot.on_message(filters.command("effects"))
        async def effects(_,m):await m.reply_text("<b>🎛 AUDIO EFFECT LAB</b>\n\nChoose a preset:",reply_markup=effects_keyboard(0))
        async def control(m,action):
            if not await self.require_admin(m):return
            p=self.store.get(m.chat.id)
            try:
                if action=="pause":await maybe(self.calls.pause(m.chat.id));p.paused=True
                elif action=="resume":await maybe(self.calls.resume(m.chat.id));p.paused=False
                elif action=="skip":
                    ok, skipped = await self.skip_tracks(m.chat.id, 1)
                    if not ok:
                        await m.reply_text("⏭ <b>Nothing is playing.</b>")
                        return
                elif action=="stop":
                    # Full playback shutdown: cancel discovery, stop the current media,
                    # clear pending queue, disable autoplay, and leave the VC.
                    task=self._autoplay_tasks.pop(m.chat.id,None)
                    if task and not task.done():
                        task.cancel()
                        with suppress(asyncio.CancelledError): await task
                    self._manual_stop_until[m.chat.id]=time.monotonic()+5.0
                    p.clear(); p.current=None; p.autoplay=False; p.autoplay_topic=""; p.autoplay_seen.clear()
                    with suppress(Exception):
                        await asyncio.wait_for(maybe(self.calls.leave_call(m.chat.id)), timeout=5)
                elif action=="shuffle":p.shuffle()
                elif action=="loop":p.loop=not p.loop
                elif action=="mute":await maybe(self.calls.mute(m.chat.id));p.muted=True
                elif action=="unmute":await maybe(self.calls.unmute(m.chat.id));p.muted=False
                elif action=="voldown":p.volume=max(0,p.volume-10);await maybe(self.calls.change_volume_call(m.chat.id,p.volume))
                elif action=="volup":p.volume=min(200,p.volume+10);await maybe(self.calls.change_volume_call(m.chat.id,p.volume))
                elif action=="clear":p.clear()
                await m.reply_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
            except Exception as e:
                log.warning("control %s: %s",action,e)
                await m.reply_text("⚠️ <b>VC unavailable.</b> Check that the assistant is in the VC and has <b>Manage Video Chats</b> permission.")
        @self.bot.on_message(filters.command("skip"))
        async def skip_command(_,m):
            if not await self.require_admin(m): return
            parts=m.text.split()
            count=1
            if len(parts)>1:
                try:
                    count=int(parts[1])
                except Exception:
                    await m.reply_text("⏭ Use <code>/skip</code> or <code>/skip 6</code> (also: <code>/skip 6 songs</code>).")
                    return
            if count<1 or count>100:
                await m.reply_text("⏭ Skip count must be between <code>1</code> and <code>100</code>.")
                return
            ok, skipped=await self.skip_tracks(m.chat.id,count)
            if not ok:
                await m.reply_text("⏭ <b>Nothing is playing.</b>")
                return
            p=self.store.get(m.chat.id)
            await m.reply_text(f"⏭ <b>SKIPPED {skipped} SONG{'' if skipped==1 else 'S'}</b>\n\n" + (player_text(p,self.cfg.bot_name) if p.current else "📭 Queue finished."), reply_markup=player_keyboard())

        @self.bot.on_message(filters.command("stopsong"))
        async def stopsong(_,m):
            if not await self.require_admin(m): return
            p=self.store.get(m.chat.id)
            if not p.current:
                await m.reply_text("⏹ <b>No song is currently playing.</b>")
                return
            # Set the guard BEFORE leaving the call. Telegram/PyTgCalls may emit
            # stream_end for the intentional stop; that event must not auto-play queue.
            self._manual_stop_until[m.chat.id]=time.monotonic()+5.0
            stopped=p.current.title
            p.remember(p.current)
            p.current=None
            p.paused=False
            with suppress(Exception):
                await asyncio.wait_for(maybe(self.calls.leave_call(m.chat.id)),timeout=5)
            await m.reply_text(f"⏹ <b>SONG STOPPED</b>\n\n🎵 {esc(stopped)}\n📥 Queue kept: <code>{len(p.queue)}</code>\n♾️ Autoplay: <code>{'ON' if p.autoplay else 'OFF'}</code>\n\n▶️ Use <code>/play song</code> to start playback again.",reply_markup=player_keyboard())

        for cmd,action in [("pause","pause"),("resume","resume"),("stop","stop"),("shuffle","shuffle"),("loop","loop"),("mute","mute"),("unmute","unmute"),("voldown","voldown"),("volup","volup"),("clear","clear"),("clearqueue","clear")]:
            async def handler(_,m,a=action): await control(m,a)
            self.bot.on_message(filters.command(cmd))(handler)
        @self.bot.on_message(filters.command("queue"))
        async def queue(_,m):
            p=self.store.get(m.chat.id)
            if not p.queue:await m.reply_text(player_text(p,self.cfg.bot_name)+"\n\n📭 <b>Queue empty.</b>");return
            lines=[f"<code>{i:02}</code> • {x.title[:70]} • <code>{duration(x.duration)}</code>" for i,x in enumerate(p.queue[:30],1)]
            await m.reply_text("<b>📜 QUEUE</b>\n\n"+"\n".join(lines),reply_markup=player_keyboard())
        @self.bot.on_message(filters.command("now"))
        async def now(_,m):await m.reply_text(player_text(self.store.get(m.chat.id),self.cfg.bot_name),reply_markup=player_keyboard())
        @self.bot.on_message(filters.command("volume"))
        async def volume(_,m):
            if not await self.require_admin(m):return
            try:v=max(0,min(200,int(m.text.split(maxsplit=1)[1])))
            except Exception:await m.reply_text("🔊 <code>/volume 0-200</code>");return
            p=self.store.get(m.chat.id);p.volume=v
            with suppress(Exception):await maybe(self.calls.change_volume_call(m.chat.id,v))
            await m.reply_text(f"🔊 Volume: <code>{v}%</code>")
        @self.bot.on_message(filters.command("remove"))
        async def remove(_,m):
            if not await self.require_admin(m):return
            p=self.store.get(m.chat.id)
            try:i=int(m.text.split(maxsplit=1)[1])-1; t=p.queue.pop(i)
            except Exception:await m.reply_text("📍 <code>/remove 2</code>");return
            await m.reply_text(f"🗑 Removed: <b>{t.title}</b>")
        @self.bot.on_message(filters.command("jump"))
        async def jump(_,m):
            if not await self.require_admin(m):return
            try:i=int(m.text.split(maxsplit=1)[1])-1
            except Exception:await m.reply_text("📍 <code>/jump 3</code>");return
            p=self.store.get(m.chat.id)
            if not 0<=i<len(p.queue):await m.reply_text("❌ Invalid queue position.");return
            p.queue.insert(0,p.queue.pop(i))
            with suppress(Exception):await asyncio.wait_for(maybe(self.calls.leave_call(m.chat.id)), timeout=5)
            await self.play_next(m.chat.id)
        @self.bot.on_message(filters.command("history"))
        async def history(_,m):
            p=self.store.get(m.chat.id);await m.reply_text("<b>📚 HISTORY</b>\n\n"+("\n".join(f"{i}. {x.title[:80]}" for i,x in enumerate(p.history[:15],1)) if p.history else "Empty."))
        @self.bot.on_message(filters.command(["previous","prev","back","replay"]))
        async def previous(_,m):
            if not await self.require_admin(m): return
            p=self.store.get(m.chat.id)
            if not p.history:
                if p.current:
                    target=p.current
                else:
                    await m.reply_text("📚 <b>No previous track available.</b>"); return
            else:
                target=p.history[0]
            try:
                with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(m.chat.id)), timeout=5)
                await asyncio.wait_for(self.stream(m.chat.id,target,getattr(target,"video",p.video),p.effect), timeout=45)
                if p.history and p.history[0] is target:
                    p.history.pop(0)
                await m.reply_text("⏮ <b>PREVIOUS TRACK</b>\n\n"+player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
            except Exception:
                await m.reply_text("⚠️ Could not replay the previous track. Previous history was preserved.")

        @self.bot.on_message(filters.command(["autostatus","autoplaystatus"]))
        async def autostatus(_,m):
            p=self.store.get(m.chat.id)
            await m.reply_text(f"<b>♾ AUTOPLAY STATUS</b>\n\n🟢 Enabled: <code>{'YES' if p.autoplay else 'NO'}</code>\n🎯 Topic: <code>{p.autoplay_topic or 'None'}</code>\n🔎 Discovery round: <code>{p.autoplay_round}</code>\n📥 Queue: <code>{len(p.queue)}</code>\n🧠 Seen: <code>{len(p.autoplay_seen)}</code>",reply_markup=player_keyboard())

        @self.bot.on_message(filters.command(["songinfo","info"]))
        async def songinfo(_,m):
            p=self.store.get(m.chat.id)
            if not p.current:
                await m.reply_text("🎵 <b>No track is playing.</b>"); return
            t=p.current
            await m.reply_text(f"<b>🎵 TRACK INFO</b>\n\n📝 <b>{esc(t.title)}</b>\n⏱ <code>{duration(t.duration)}</code>\n🎚 Mode: <code>{'VIDEO' if t.video else 'AUDIO'}</code>\n🎛 FX: <code>{esc(p.effect)}</code>\n⚡ Speed: <code>{p.speed:.2f}x</code>\n👤 Requested by: {esc(t.requested_by)}\n🔗 <code>{esc(t.webpage_url)}</code>")

        @self.bot.on_message(filters.command(["random","randombest"]))
        async def random_song(_,m):
            if not await self.require_admin(m): return
            p=self.store.get(m.chat.id); p.autoplay=True; p.autoplay_topic="random music"; p.autoplay_round+=1
            added=await self._autofill(m.chat.id,minimum=1)
            if not p.current: await self.play_next(m.chat.id)
            else: await self.play_next(m.chat.id)
            await m.reply_text(f"🎲 <b>RANDOM DISCOVERY</b>\n📥 Fresh tracks: <code>{added}</code>",reply_markup=player_keyboard())

        @self.bot.on_message(filters.command(["clearhistory","historyclear"]))
        async def clearhistory(_,m):
            if not await self.require_admin(m): return
            p=self.store.get(m.chat.id); p.history.clear(); p.autoplay_seen.clear();
            await m.reply_text("🧹 <b>HISTORY CLEARED</b>\n🧠 Autoplay discovery memory reset.")

        @self.bot.on_message(filters.command(["queueinfo","qinfo"]))
        async def queueinfo(_,m):
            p=self.store.get(m.chat.id)
            await m.reply_text(f"📜 <b>QUEUE INFO</b>\n\n🎵 Current: <code>{'YES' if p.current else 'NO'}</code>\n📚 Pending: <code>{len(p.queue)}</code>\n🧠 History: <code>{len(p.history)}</code>\n♾ Autoplay: <code>{'ON' if p.autoplay else 'OFF'}</code>\n🎯 Topic: <code>{p.autoplay_topic or 'None'}</code>\n🎥 Mode: <code>{'VIDEO' if p.video else 'AUDIO'}</code>",reply_markup=player_keyboard())

        @self.bot.on_message(filters.command("reorder"))
        async def reorder(_,m):
            if not await self.require_admin(m): return
            try:
                a,b=[int(x)-1 for x in m.text.split(maxsplit=1)[1].split()[:2]]
                p=self.store.get(m.chat.id)
                if not (0<=a<len(p.queue) and 0<=b<len(p.queue)): raise ValueError
                item=p.queue.pop(a); p.queue.insert(b,item)
                await m.reply_text(f"↔️ <b>QUEUE REORDERED</b>\n<code>{a+1}</code> → <code>{b+1}</code>")
            except Exception:
                await m.reply_text("↔️ Use <code>/reorder 5 2</code>")

        @self.bot.on_message(filters.command(["mode","playmode"]))
        async def mode(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip().lower() if len(m.text.split(maxsplit=1))>1 else ""
            p=self.store.get(m.chat.id)
            if arg in {"audio","music"}: p.video=False
            elif arg in {"video","v"}: p.video=True
            else:
                await m.reply_text("🎚 Use <code>/mode audio</code> or <code>/mode video</code>"); return
            if p.current: p.current.video=p.video
            await m.reply_text(f"🎚 <b>PLAY MODE:</b> <code>{'VIDEO' if p.video else 'AUDIO'}</code>")

        @self.bot.on_message(filters.command(["trending","top","charts","mix","nonstop"]))
        async def discovery_shortcut(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1))>1 else ""
            cmd=m.command[0].lower()
            topic=arg or ({"trending":"trending songs","top":"top songs","charts":"music charts","mix":"best music mix","nonstop":"nonstop music"}.get(cmd,"music"))
            p=self.store.get(m.chat.id); p.autoplay=True; p.autoplay_topic=topic[:120]
            added=await self._autofill(m.chat.id,minimum=12)
            if not p.current: await self.play_next(m.chat.id)
            await m.reply_text(f"📡 <b>{cmd.upper()} DISCOVERY ONLINE</b>\n\n🎯 <code>{topic[:120]}</code>\n📥 Fresh tracks: <code>{added}</code>\n♾ <code>CONTINUOUS</code>",reply_markup=player_keyboard())

        @self.bot.on_message(filters.command("stats"))
        async def stats(_,m):
            p=self.store.get(m.chat.id)
            await m.reply_text(f"<b>⚡ PRIME STATS</b>\n\n🎧 Current: <code>{'YES' if p.current else 'NO'}</code>\n📚 Queue: <code>{len(p.queue)}</code>\n♾ Auto: <code>{'ON' if p.autoplay else 'OFF'}</code>\n🎛 FX: <code>{p.effect}</code>\n🔊 Volume: <code>{p.volume}%</code>\n⏱ Uptime: <code>{int(time.monotonic()-self.started)}s</code>")
        @self.bot.on_message(filters.command("ping"))
        async def ping(_,m):
            t=time.perf_counter();x=await m.reply_text("⚡ <b>PING...</b>");ms=(time.perf_counter()-t)*1000
            await x.edit_text(f"<b>╭━━〔 ⚡ PRIME PING 〕━━╮</b>\n┃ 🛰 Telegram: <code>{ms:.0f} ms</code>\n┃ 🟢 Engine: <code>ONLINE</code>\n┃ ⏱ Uptime: <code>{int(time.monotonic()-self.started)}s</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")
        @self.bot.on_message(filters.command("health"))
        async def health(_,m):await m.reply_text("🟢 <b>PRIME × BEATS HEALTHY</b>\n\n⚡ Bot: ONLINE\n🎙 Assistant: CONFIGURED\n🎧 Engine: READY")
        @self.bot.on_message(filters.command("settings"))
        async def settings(_,m):
            p=self.store.get(m.chat.id);await m.reply_text(f"<b>⚙ SETTINGS</b>\n\n🔐 Approved: <code>{'YES' if self.approvals.is_approved(m.chat.id) else 'NO'}</code>\n♾ Auto: <code>{'ON' if p.autoplay else 'OFF'}</code>\n🎯 Topic: <code>{p.autoplay_topic or 'None'}</code>\n🎛 FX: <code>{p.effect}</code>\n🔊 Volume: <code>{p.volume}%</code>")
        @self.bot.on_message(filters.command("announce"))
        async def announce(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip().lower() if len(m.text.split(maxsplit=1))>1 else "toggle"
            p=self.store.get(m.chat.id)
            if arg in {"on","enable"}: p.announce=True
            elif arg in {"off","disable"}: p.announce=False
            else: p.announce=not p.announce
            await m.reply_text(f"📣 <b>VC ANNOUNCEMENTS:</b> <code>{'ON' if p.announce else 'OFF'}</code>")

        @self.bot.on_message(filters.command("autoleave"))
        async def autoleave(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip().lower() if len(m.text.split(maxsplit=1))>1 else "toggle"
            p=self.store.get(m.chat.id)
            if arg in {"on","enable"}: p.auto_leave=True
            elif arg in {"off","disable"}: p.auto_leave=False
            else: p.auto_leave=not p.auto_leave
            await m.reply_text(f"🚪 <b>AUTO-LEAVE:</b> <code>{'ON' if p.auto_leave else 'OFF'}</code>\n<i>Leaves when playback has no queue/topic.</i>")

        @self.bot.on_message(filters.command(["seek","seekback"]))
        async def seek(_,m):
            if not await self.require_admin(m): return
            try: secs=int(m.text.split(maxsplit=1)[1])
            except Exception:
                await m.reply_text("⏱ Use <code>/seek 30</code> or <code>/seekback 20</code>."); return
            p=self.store.get(m.chat.id)
            if not p.current:
                await m.reply_text("⏱ <b>No track is playing.</b>"); return
            if m.command[0].lower()=="seekback": secs=-abs(secs)
            try:
                current=max(0.0,time.monotonic()-p.started_at); target=max(0.0,current+secs)
                await self._restart_current(m.chat.id,target)
                await m.reply_text(f"⏱ <b>SEEKED</b> <code>{secs:+d}s</code>\n📍 Position: <code>{int(target)}s</code>",reply_markup=player_keyboard())
            except Exception:
                await m.reply_text("⚠️ <b>Seek failed.</b> The previous stream state was protected.")
        @self.bot.on_message(filters.command("speed"))
        async def speed(_,m):
            if not await self.require_admin(m): return
            try: val=float(m.text.split(maxsplit=1)[1])
            except Exception:
                await m.reply_text("⚡ Use <code>/speed 1.10</code>.")
                return
            if not 0.5 <= val <= 2.0:
                await m.reply_text("⚡ Speed range: <code>0.50</code>–<code>2.00</code>.")
                return
            p=self.store.get(m.chat.id); old_speed=p.speed; p.speed=val
            try:
                if p.current:
                    pos=max(0.0,time.monotonic()-p.started_at); await self._restart_current(m.chat.id,pos)
                await m.reply_text(f"⚡ <b>Speed:</b> <code>{val:.2f}x</code>\n🟢 Applied with a clean stream restart.",reply_markup=player_keyboard())
            except Exception:
                p.speed=old_speed
                if p.current:
                    with suppress(Exception): await self._restart_current(m.chat.id,pos)
                await m.reply_text(f"⚠️ Speed change failed. Previous speed <code>{old_speed:.2f}x</code> restored.")
        @self.bot.on_message(filters.command("clone"))
        async def clone(_,m):
            if not await self.owner_only(m):return
            await m.reply_text("⚝ 𝐅ᴇᴀʀʟᴇss ꭗ 𝐌ᴜsɪᴄ ᯤ\n\n🚀 ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ\n❏ 🧬 <b>ᴄʟᴏɴᴇ sᴇᴛᴜᴘ</b>\n\nSend the <b>Bot API token</b> in this private chat only.\n⚠️ Never post a token in a group. The bot never asks for your phone number or Telegram login OTP.")
            self._clone_waiting.add(m.from_user.id)
        @self.bot.on_message(filters.private & filters.text & ~filters.command("clone"))
        async def private_text(_,m):
            if m.from_user and m.from_user.id==self.cfg.owner_id and m.from_user.id in self._clone_waiting:
                token=m.text.strip();self._clone_waiting.discard(m.from_user.id)
                with suppress(Exception): await m.delete()
                try:
                    me=await self.clone.create(token)
                    await m.reply_text(f"⚝ 𝐅ᴇᴀʀʟᴇss ꭗ 𝐌ᴜsɪᴄ ᯤ\n\n🚀 ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ\n❏ 🧬 <b>ᴄʟᴏɴᴇ ᴏɴʟɪɴᴇ</b>\n\n🤖 @{me.username or me.first_name}\n🟢 Status: <code>ONLINE</code>")
                except Exception:await m.reply_text("⚝ 𝐅ᴇᴀʀʟᴇss ꭗ 𝐌ᴜsɪᴄ ᯤ\n🚀 ᴘᴏᴡᴇʀғᴜʟ • ғᴀsᴛ • sᴛᴀʙʟᴇ\n❏ ❌ ᴄʟᴏɴᴇ ғᴀɪʟᴇᴅ — ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴛᴏᴋᴇɴ.")
        @self.bot.on_message(filters.command("clones"))
        async def clones(_,m):
            if await self.owner_only(m):await m.reply_text(f"🧬 Running clones: <code>{len(self.clone.clients)}</code>")

        # ──────────────────────────────────────────────────────────────
        # OMEGA HARDENED POWER LAYER: library, discovery, dashboards and aliases.
        # These handlers are intentionally small and reuse the stable core.
        # ──────────────────────────────────────────────────────────────
        @self.bot.on_message(filters.command(["version","ver"]))
        async def version(_,m):
            await m.reply_text(f"<b>⚡ PRIME × BEATS</b>\n\n🧬 Build: <code>FEARLESS FINAL HARDENED</code>\n🎛 Effects: <code>{len(EFFECTS)}+</code>\n🧩 Capability matrix: <code>{len(FEATURES)}+</code>\n🎧 Audio: <code>HIGH</code>\n🎥 Video: <code>HD 720p</code>\n🛡 Recovery: <code>RETRY + TIMEOUT + SAFE RESTART</code>",reply_markup=links(self.cfg))
        @self.bot.on_message(filters.command("owner"))
        async def owner(_,m): await m.reply_text("👑 <b>MAIN OWNER</b>\n\n@Prime_Fearless_45\n<code>7915543522</code>",reply_markup=links(self.cfg))
        @self.bot.on_message(filters.command("support"))
        async def support(_,m): await m.reply_text("🛰 <b>PRIME SUPPORT</b>\n\n💬 @SPARK_X_NETWORK\n📢 @SPARK_X_NETWORK_OP\n⚡ @Prime_Arrived",reply_markup=links(self.cfg))

        @self.bot.on_message(filters.command("features"))
        async def features(_,m):
            total=len(FEATURES)
            await m.reply_text(
                f"<b>╭━━〔 ⚡ PRIME × BEATS V8 〕━━╮</b>\n"
                f"┃ 🧬 Feature Matrix: <code>{total}+</code>\n"
                "┃ 🎧 Audio • 🎥 Video • 🎛 FX\n"
                "┃ ♾ Smart Autoplay • 🧠 Queue\n"
                "┃ 🛡 Owner Approval • 🔐 Security\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"+
                "\n".join(f"<code>{i:03}</code> • {x}" for i,x in enumerate(FEATURES,1)),
                reply_markup=home_keyboard(self.cfg))

        @self.bot.on_message(filters.command("about"))
        async def about(_,m):
            await m.reply_text(
                f"<b>⚝ {self.cfg.bot_name}</b>\n\n"
                "<blockquote>⚡ A high-performance Telegram VC music engine built around Pyrogram + PyTgCalls + yt-dlp.</blockquote>\n"
                f"🧬 Build: <code>FEARLESS FINAL HARDENED</code>\n🎛 FX: <code>{len(EFFECTS)}+</code>\n🧩 Features: <code>{len(FEATURES)}+</code>\n"
                "🎥 Video: <code>HD 720p profile</code>\n🔐 Approval: <code>OWNER GATED</code>\n\n"
                "👑 Owner: @Prime_Fearless_45", reply_markup=links(self.cfg))

        @self.bot.on_message(filters.command("uptime"))
        async def uptime(_,m):
            sec=int(time.monotonic()-self.started); d,rem=divmod(sec,86400); h,rem=divmod(rem,3600); mi,se=divmod(rem,60)
            await m.reply_text(f"<b>⏱ PRIME UPTIME</b>\n\n<code>{d}d {h:02}h {mi:02}m {se:02}s</code>\n🟢 Engine: <code>ONLINE</code>")

        @self.bot.on_message(filters.command("id"))
        async def ids(_,m):
            await m.reply_text(f"🪪 <b>ID PANEL</b>\n\n👤 User: <code>{m.from_user.id if m.from_user else 'N/A'}</code>\n💬 Chat: <code>{m.chat.id}</code>")

        @self.bot.on_message(filters.command("search"))
        async def search(_,m):
            q=m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1))>1 else ""
            if not q: await m.reply_text("🔎 <code>/search song name</code>"); return
            x=await m.reply_text("🔎 <b>SEARCHING...</b>\n🧠 Ranking fresh results...")
            try:
                entries=await search_results(q,8)
                if not entries:
                    await x.edit_text("❌ <b>No results.</b> Try another search phrase."); return
                key=secrets.token_urlsafe(9).replace("-","_").replace("/","_")
                now_ms=time.time()*1000
                self._search_cache[key]=(now_ms,entries)
                self._search_cache={k:v for k,v in self._search_cache.items() if now_ms-v[0]<300000}
                if len(self._search_cache)>64:
                    oldest=sorted(self._search_cache.items(),key=lambda item:item[1][0])[:len(self._search_cache)-64]
                    for old_key,_ in oldest: self._search_cache.pop(old_key,None)
                rows=[]
                for i,e in enumerate(entries,1):
                    title=(e.get("title") or "Unknown")[:48]
                    rows.append([InlineKeyboardButton(f"▶ {i:02} • {title}",callback_data=f"searchplay:{key}:{i-1}")])
                rows.append([InlineKeyboardButton("✕ Close",callback_data="searchclose")])
                await x.edit_text(f"<b>╭━━〔 🔎 PRIME SEARCH 〕━━╮</b>\n┃ Query: <code>{q[:80]}</code>\n┃ Results: <code>{len(entries)}</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>\n\nTap a result to queue/play it.",reply_markup=InlineKeyboardMarkup(rows))
            except Exception:
                await x.edit_text("❌ <b>Search failed.</b> Try again in a moment.")

        @self.bot.on_message(filters.command("discover"))
        async def discover(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1))>1 else ""
            if not arg:
                await m.reply_text("🔎 <code>/discover Romantic Hindi Songs</code>"); return
            p=self.store.get(m.chat.id); p.autoplay=True; p.autoplay_topic=arg[:120]
            added=await self._autofill(m.chat.id,minimum=12)
            await m.reply_text(f"📡 <b>DISCOVERY COMPLETE</b>\n\n🎯 <code>{arg[:120]}</code>\n📥 Added: <code>{added}</code>\n♾️ Autoplay: <code>ON</code>",reply_markup=player_keyboard())

        @self.bot.on_message(filters.command("fav"))
        async def fav(_,m):
            p=self.store.get(m.chat.id)
            if not p.current: await m.reply_text("⭐ Nothing is playing to save."); return
            await self.library.favorite(m.from_user.id,p.current)
            await m.reply_text(f"⭐ <b>SAVED TO FAVORITES</b>\n\n🎵 {p.current.title}")

        @self.bot.on_message(filters.command("unfav"))
        async def unfav(_,m):
            p=self.store.get(m.chat.id)
            if not p.current: await m.reply_text("⭐ Nothing is playing."); return
            await self.library.unfavorite(m.from_user.id,p.current.webpage_url)
            await m.reply_text("🗑 <b>REMOVED FROM FAVORITES</b>")

        @self.bot.on_message(filters.command(["favs","favorites"]))
        async def favs(_,m):
            arr=self.library.favorites(m.from_user.id)
            if not arr: await m.reply_text("⭐ <b>FAVORITES EMPTY</b>\nUse <code>/fav</code> while a song is playing."); return
            await m.reply_text("<b>⭐ FAVORITES</b>\n\n"+"\n".join(f"<code>{i:02}</code> • {x.get('title','Unknown')[:70]}" for i,x in enumerate(arr[:30],1)))

        @self.bot.on_message(filters.command("save"))
        async def save_playlist(_,m):
            if not await self.require_admin(m): return
            p=self.store.get(m.chat.id)
            if not p.current: await m.reply_text("💾 Nothing is playing."); return
            parts=m.text.split(maxsplit=1); name=parts[1].strip() if len(parts)>1 else "My Playlist"
            await self.library.playlist_add(m.from_user.id,name,p.current)
            await m.reply_text(f"💾 <b>PLAYLIST SAVED</b>\n📁 <code>{name[:40]}</code>\n🎵 {p.current.title}")

        @self.bot.on_message(filters.command(["playlists","pls"]))
        async def playlists(_,m):
            pls=self.library.playlists(m.from_user.id)
            if not pls: await m.reply_text("📁 <b>NO PLAYLISTS</b>\nUse <code>/save MyPlaylist</code> while playing."); return
            await m.reply_text("<b>📁 YOUR PLAYLISTS</b>\n\n"+"\n".join(f"• <code>{k}</code> — {len(v)} track(s)" for k,v in pls.items()))

        @self.bot.on_message(filters.command("library"))
        async def library(_,m):
            arr=self.library.favorites(m.from_user.id); pls=self.library.playlists(m.from_user.id)
            await m.reply_text(f"<b>🗃 PERSONAL LIBRARY</b>\n\n⭐ Favorites: <code>{len(arr)}</code>\n📁 Playlists: <code>{len(pls)}</code>")

        @self.bot.on_message(filters.command("menu"))
        async def menu(_,m): await m.reply_text(welcome(self.cfg,m.from_user.first_name if m.from_user else "there"),reply_markup=home_keyboard(self.cfg))

        @self.bot.on_message(filters.command(["radio","autoplayradio"]))
        async def radio(_,m):
            if not await self.require_admin(m): return
            arg=m.text.split(maxsplit=1)[1].strip() if len(m.text.split(maxsplit=1))>1 else ""
            if not arg:
                await m.reply_text("📻 <b>RADIO MODE</b>\nUse <code>/radio Romantic Hindi Songs</code>"); return
            p=self.store.get(m.chat.id); p.autoplay=True; p.autoplay_topic=arg[:120]; p.autoplay_round=0; p.autoplay_seen.clear()
            p.queue.clear(); added=await self._autofill(m.chat.id,minimum=12)
            if not p.current: await self.play_next(m.chat.id)
            await m.reply_text(f"📻 <b>PRIME RADIO ONLINE</b>\n\n🎯 <code>{arg[:120]}</code>\n📡 Discoveries: <code>{added}</code>\n♾️ <code>CONTINUOUS</code>",reply_markup=player_keyboard())

        # Effect aliases: /nightcore, /bassboost, /8d, /lofi, etc.
        for alias,key in EFFECT_ALIASES.items():
            if alias == "radio": alias = "radiofx"
            async def fx_alias(_,m,a=alias,k=key):
                if not await self.require_admin(m): return
                p=self.store.get(m.chat.id); old_effect=p.effect; p.effect=k
                try:
                    if p.current:
                        pos=max(0.0,time.monotonic()-p.started_at); await self._restart_current(m.chat.id,pos)
                    await m.reply_text(f"🎛 <b>{EFFECTS[k][0]}</b>\n🟢 Effect applied.",reply_markup=player_keyboard())
                except Exception:
                    p.effect=old_effect
                    if p.current:
                        with suppress(Exception): await self._restart_current(m.chat.id,pos)
                    await m.reply_text("⚠️ Effect failed. Previous effect restored.")
            self.bot.on_message(filters.command(alias))(fx_alias)

        # Stable convenience aliases for core playback commands.
        for alias,target in {"yt":"play","song":"play","music":"play","video":"vplay","next":"skip","repeat":"loop"}.items():
            async def alias_handler(_,m,t=target):
                if t in {"play","vplay"}:
                    if not await self.require_admin(m): return
                    q=m.text.split(maxsplit=1)[1] if len(m.text.split(maxsplit=1))>1 else ""
                    await self.handle_play(m,q,t=="vplay")
                    return
                # route control aliases through the same permission-checked core
                await control(m,t)
            self.bot.on_message(filters.command(alias))(alias_handler)
        @self.bot.on_inline_query()
        async def inline_search(_,q):
            text=(q.query or "").strip()
            if not text:
                await q.answer([],cache_time=2,is_personal=True,switch_pm_text="Open PRIME × BEATS",switch_pm_parameter="start")
                return
            try:
                entries=await asyncio.to_thread(lambda: __import__('yt_dlp').YoutubeDL({"quiet":True,"no_warnings":True,"extract_flat":True,"skip_download":True,"noplaylist":True}).extract_info("ytsearch8:"+text,download=False).get("entries") or [])
                results=[]
                for i,x in enumerate(entries[:8]):
                    title=(x.get("title") or "Unknown")[:120]
                    results.append(InlineQueryResultArticle(
                        id=str(i)+":"+(x.get("id") or str(i)),title="🎵 "+title,
                        description="PRIME × BEATS • tap to send /play",input_message_content=InputTextMessageContent("/play "+title)))
                await q.answer(results,cache_time=10,is_personal=False)
            except Exception:
                await q.answer([],cache_time=2,is_personal=True)

        @self.bot.on_callback_query()
        async def callbacks(_,q):
            data=q.data or "";chat=q.message.chat.id;p=self.store.get(chat)
            if data=="searchclose":
                await q.message.delete(); return
            elif data.startswith("searchplay:"):
                if not await self.callback_admin(q): return
                try:
                    _,key,idx=data.split(":",2); cached=self._search_cache.get(key);
                    if not cached or time.time()*1000-cached[0] >= 300000: raise ValueError("expired search")
                    entry=cached[1][int(idx)]
                    url=entry.get("webpage_url") or entry.get("url")
                    track=await resolve(url,self._requester_name(q.from_user),False)
                    track.video=False
                    if p.current:
                        pos=p.add(track,self.cfg.max_queue); await q.answer(f"Queued at #{pos}")
                    else:
                        await asyncio.wait_for(self.stream(chat,track,False,p.effect), timeout=45); await q.answer("Playing ⚡")
                    await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
                except Exception:
                    await q.answer("Could not play that result",show_alert=True)
            elif data=="ping":
                t=time.perf_counter(); await q.answer(f"Telegram callback: {(time.perf_counter()-t)*1000:.0f} ms ⚡")
            elif data=="startvc":
                if not await self.callback_admin(q):return
                try:
                    await self._ensure_voice_chat(chat)
                    await q.answer("Voice Chat is online ⚡")
                    await q.message.edit_text("<b>╭━━〔 🟢 PRIME VC ONLINE 〕━━╮</b>\n┃ 🎙 Assistant is connected\n┃ 🎧 Ready for /play\n┃ 🎥 Ready for /vplay\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>",reply_markup=player_keyboard())
                except Exception as e:
                    log.exception("startvc callback failed: chat=%s",chat)
                    await q.answer("Could not start Voice Chat",show_alert=True)
            elif data=="help":await q.message.edit_text(help_text(self.cfg.bot_name),reply_markup=home_keyboard(self.cfg))
            elif data=="help:play":await q.answer("Use /play <song name>",show_alert=True)
            elif data=="now":await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard()); await q.answer("Player refreshed ⚡")
            elif data=="queue":await q.answer("\n".join(f"{i}. {x.title[:45]}" for i,x in enumerate(p.queue[:10],1)) or "Queue empty",show_alert=True)
            elif data=="links":await q.message.edit_text(welcome(self.cfg,q.from_user.first_name),reply_markup=links(self.cfg))
            elif data=="effects:0" or data.startswith("effects:"):
                page=int(data.split(":")[1]);await q.message.edit_text("<b>🎛 AUDIO EFFECT LAB</b>\n\nChoose a preset:",reply_markup=effects_keyboard(page))
            elif data.startswith("effect:"):
                if not await self.callback_admin(q):return
                key=data.split(":",1)[1]
                if key not in EFFECTS:await q.answer("Unknown effect",show_alert=True);return
                old_effect=p.effect; p.effect=key
                if p.current:
                    try:
                        pos=max(0.0,time.monotonic()-p.started_at)
                        await self._restart_current(chat,pos)
                    except Exception:
                        p.effect=old_effect
                        with suppress(Exception): await self._restart_current(chat,pos)
                        await q.answer("Effect failed; previous effect restored.",show_alert=True);return
                await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard());await q.answer(f"{EFFECTS[key][0]} applied")
            elif data=="auto":
                if not await self.callback_admin(q):return
                p.autoplay=not p.autoplay
                if p.autoplay and p.autoplay_topic and len(p.queue)<6:
                    self._autoplay_tasks[chat]=asyncio.create_task(self._autofill(chat,minimum=10))
                await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard());await q.answer("Autoplay updated")
            elif data=="refresh":
                if not await self.callback_admin(q):return
                if p.current:
                    try:
                        pos=max(0.0,time.monotonic()-p.started_at)
                        await self._restart_current(chat,pos)
                        await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
                        await q.answer("Stream refreshed ⚡")
                    except Exception:await q.answer("Refresh failed",show_alert=True)
                else: await q.answer("Nothing is playing",show_alert=True)
            elif data.startswith("seek:"):
                if not await self.callback_admin(q):return
                try:
                    delta=float(data.split(":",1)[1])
                    if not p.current: raise ValueError
                    current=max(0.0,time.monotonic()-p.started_at)
                    target=max(0.0,current+delta)
                    await self._restart_current(chat,target)
                    await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
                    await q.answer(f"Seeked {delta:+.0f}s ⚡")
                except Exception:
                    await q.answer("Seek failed; stream was kept safe.",show_alert=True)
            elif data=="favorite":
                if not await self.callback_admin(q): return
                if not p.current: await q.answer("Nothing is playing",show_alert=True); return
                await self.library.favorite(q.from_user.id,p.current)
                await q.answer("⭐ Saved to your favorites")
            elif data=="mode":
                if not await self.callback_admin(q): return
                p.video=not p.video
                if p.current:
                    p.current.video=p.video
                await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
                await q.answer(f"Mode set to {'VIDEO' if p.video else 'AUDIO'} • applies on next track")
            elif data=="previous":
                if not await self.callback_admin(q): return
                if not p.history: await q.answer("No previous track",show_alert=True); return
                target=p.history[0]
                try:
                    with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat)), timeout=5)
                    await asyncio.wait_for(self.stream(chat,target,getattr(target,"video",p.video),p.effect), timeout=45)
                    if p.history and p.history[0] is target:
                        p.history.pop(0)
                    await q.message.edit_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
                    await q.answer("Previous track ⚡")
                except Exception:
                    await q.answer("Could not play previous track; history preserved.",show_alert=True)
            elif data in {"pause","resume","skip","stop","shuffle","loop","mute","voldown","volup","clear"}:
                if not await self.callback_admin(q):return
                fake=type("M",(),{"chat":q.message.chat,"from_user":q.from_user,"reply_text":q.message.reply_text})()
                await self._control_callback(fake,data,p)
                with suppress(Exception):await q.answer("Updated ⚡")
            else:
                with suppress(Exception): await q.answer("Unknown or expired control.",show_alert=True)
        # Native PyTgCalls events: natural stream end + participant join/leave.
        try:
            @self.calls.on_update(call_filters.stream_end())
            async def _stream_end_handler(_, update):
                chat=update.chat_id
                # Ignore end events caused by /stopsong, /stop, skip, or an intentional
                # media transition. Only a genuine natural end should advance the queue.
                if chat in self._transitioning:
                    return
                if time.monotonic() < self._manual_stop_until.get(chat,0.0):
                    return
                p=self.store.get(chat)
                if not p.current:
                    return
                finished=p.current
                p.remember(finished)
                p.current=None
                # Natural completion ALWAYS consumes the next queued song first.
                # Autoplay discovery is only used when the explicit queue is empty.
                try:
                    if p.queue:
                        await self.play_next(chat)
                    elif p.autoplay and p.autoplay_topic:
                        await self.play_next(chat)
                    elif p.auto_leave:
                        with suppress(Exception): await asyncio.wait_for(maybe(self.calls.leave_call(chat)),timeout=5)
                except Exception:
                    log.exception("natural stream-end advance failed for chat %s",chat)

            @self.calls.on_update(call_filters.call_participant(GroupCallParticipant.Action.JOINED))
            async def _participant_joined(_, update):
                with suppress(Exception):
                    p=self.store.get(update.chat_id)
                    if not p.announce: return
                    u=await self.bot.get_users(update.participant.user_id)
                    await self.bot.send_message(update.chat_id,
                        f"<b>╭━━〔 🟢 VC JOIN 〕━━╮</b>\n┃ 👤 {u.mention}\n┃ 🎧 <code>Welcome to PRIME × BEATS</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")

            @self.calls.on_update(call_filters.call_participant(GroupCallParticipant.Action.LEFT))
            async def _participant_left(_, update):
                with suppress(Exception):
                    p=self.store.get(update.chat_id)
                    if not p.announce: return
                    u=await self.bot.get_users(update.participant.user_id)
                    await self.bot.send_message(update.chat_id,
                        f"<b>╭━━〔 🔴 VC LEAVE 〕━━╮</b>\n┃ 👤 {u.mention}\n┃ 💫 <code>Thanks for vibing with us</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")
        except Exception as e:
            log.warning("PyTgCalls event registration unavailable: %s", e)

        # VC start service notification
        @self.bot.on_message(filters.service)
        async def vc_service(_,m):
            if getattr(m,"video_chat_started",None) is not None:
                await m.reply_text("<b>╭━━〔 🟢 VC ONLINE 〕━━╮</b>\n┃ ⚡ PRIME × BEATS detected the Voice Chat\n┃ 🎧 <code>/play &lt;song&gt;</code>\n┃ 🎥 <code>/vplay &lt;video&gt;</code>\n┃ ♾️ <code>/autoplay &lt;topic&gt;</code>\n<b>╰━━━━━━━━━━━━━━━━━━━━╯</b>")
            elif getattr(m,"video_chat_ended",None) is not None:
                await m.reply_text("<b>🔴 VOICE CHAT ENDED</b>\n\n🧹 Playback session closed safely.\n♾ Autoplay will resume when a new VC is started and a queue/topic remains.")
    async def _control_callback(self,m,action,p):
        chat=m.chat.id
        if action=="pause":await maybe(self.calls.pause(chat));p.paused=True
        elif action=="resume":await maybe(self.calls.resume(chat));p.paused=False
        elif action=="skip":
            await self.skip_tracks(chat,1)
        elif action=="stop":
            # Full playback shutdown for the inline control as well.
            task=self._autoplay_tasks.pop(chat,None)
            if task and not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError): await task
            self._manual_stop_until[chat]=time.monotonic()+5.0
            p.clear(); p.current=None; p.autoplay=False; p.autoplay_topic=""; p.autoplay_seen.clear()
            with suppress(Exception):
                await asyncio.wait_for(maybe(self.calls.leave_call(chat)), timeout=5)
        elif action=="shuffle":p.shuffle()
        elif action=="loop":p.loop=not p.loop
        elif action=="mute":await maybe(self.calls.mute(chat));p.muted=True
        elif action=="volup":p.volume=min(200,p.volume+10);await maybe(self.calls.change_volume_call(chat,p.volume))
        elif action=="voldown":p.volume=max(0,p.volume-10);await maybe(self.calls.change_volume_call(chat,p.volume))
        elif action=="clear":p.clear()
        await m.reply_text(player_text(p,self.cfg.bot_name),reply_markup=player_keyboard())
    async def callback_admin(self,q):
        if q.from_user.id==self.cfg.owner_id:return self.approvals.is_approved(q.message.chat.id)
        try:
            x=await self.bot.get_chat_member(q.message.chat.id,q.from_user.id)
            ok=x.status in (ChatMemberStatus.OWNER,ChatMemberStatus.ADMINISTRATOR)
        except RPCError:ok=False
        if not ok:await q.answer("Admin rights required.",show_alert=True);return False
        if not self.approvals.is_approved(q.message.chat.id):await q.answer("Owner approval required.",show_alert=True);return False
        return True
    async def run(self):
        await self.bot.start();await self.assistant.start()
        try:
            me=await self.assistant.get_me()
            log.info("assistant connected: id=%s username=@%s name=%s",me.id,me.username or "",me.first_name or "")
            if int(me.id)!=8547061213:
                log.error("ASSISTANT_SESSION belongs to a different Telegram account: expected 8547061213, got %s",me.id)
        except Exception:
            log.exception("could not verify assistant identity")
        with suppress(Exception):await maybe(self.calls.start())
        self.web_runner=await start_web(self.cfg.port,self.bot)
        log.info("PRIME × BEATS FEARLESS FINAL HARDENED online")
        await asyncio.Event().wait()
    async def shutdown(self):
        with suppress(Exception):await self.clone.stop_all()
        with suppress(Exception):await maybe(self.calls.stop())
        with suppress(Exception):await self.assistant.stop()
        with suppress(Exception):await self.bot.stop()
        if self.web_runner:await self.web_runner.cleanup()
