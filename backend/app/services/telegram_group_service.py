from __future__ import annotations

import asyncio
import json
import re
import threading

import httpx

from app.core.config import DATA_DIR

GROUPS_FILE = DATA_DIR / "telegram_groups.json"
GROUP_CHAT_TYPES = {"group", "supergroup"}
GROUP_KEEP = 80
GROUP_CONTEXT_LIMIT = 30
ANSWER_TIMEOUT = 120
FEHLER_ANTWORT = "Puh, da ist gerade etwas schiefgelaufen. Frag mich gleich nochmal."


class GroupMemory:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, list[dict]] = self._load()

    def _load(self) -> dict[str, list[dict]]:
        try:
            data = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    str(key): value
                    for key, value in data.items()
                    if isinstance(value, list)
                }
        except Exception:
            pass
        return {}

    def _save(self) -> None:
        try:
            GROUPS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def record(
        self,
        chat_id: str | int,
        sender: str,
        text: str,
        message_id: int | None = None,
        bot: str = "",
    ) -> bool:
        text = str(text or "").strip()
        if not text:
            return False
        with self._lock:
            entries = self._data.setdefault(str(chat_id), [])
            if message_id is not None and any(
                entry.get("message_id") == message_id for entry in entries
            ):
                return False
            entry: dict = {"sender": str(sender or "Jemand"), "text": text[:2000]}
            if message_id is not None:
                entry["message_id"] = message_id
            if bot:
                entry["bot"] = bot
            entries.append(entry)
            del entries[:-GROUP_KEEP]
            self._save()
            return True

    def transcript(self, chat_id: str | int, limit: int = GROUP_CONTEXT_LIMIT) -> str:
        with self._lock:
            entries = list(self._data.get(str(chat_id), []))[-limit:]
        return "\n".join(f"{e.get('sender', '?')}: {e.get('text', '')}" for e in entries)


_memory: GroupMemory | None = None


def get_group_memory() -> GroupMemory:
    global _memory
    if _memory is None:
        _memory = GroupMemory()
    return _memory


def is_mentioned(text: str, entities: list | None, username: str) -> bool:
    if not username or not text:
        return False
    needle = "@" + username.lower()
    for entity in entities or []:
        if entity.get("type") == "mention":
            offset = int(entity.get("offset", 0))
            length = int(entity.get("length", 0))
            if text[offset : offset + length].lower() == needle:
                return True
    return needle in text.lower()


def strip_mention(text: str, username: str) -> str:
    if not username:
        return text.strip()
    pattern = re.compile(re.escape("@" + username) + r"[,.;:]?", re.IGNORECASE)
    return re.sub(r"\s+", " ", pattern.sub(" ", text)).strip(" ,;:—-")


async def group_answer(
    variant: str,
    username: str,
    sender: str,
    question: str,
    transcript: str = "",
    group: bool = True,
    partner_hint: str = "",
    provider: str = "",
    model: str = "",
    slot: str = "jon",
) -> str:
    from app.services.llm import complete
    from app.services.persona_service import get_persona_service

    system = get_persona_service().persona_block(include_memory=False, variant=variant)
    if group:
        system += (
            f"\n\nDU BIST GERADE ALS @{username} IN EINER TELEGRAM-GRUPPE. "
            "Du liest alle Nachrichten der Gruppe mit und kennst den Verlauf. "
            "Du antwortest aber NUR, wenn dich jemand mit deinem @-Namen erwaehnt "
            "- die aktuelle Nachricht ist so eine. In der Gruppe sind mehrere "
            "Menschen und eventuell auch andere Bots aktiv"
            + (f" (zum Beispiel {partner_hint})" if partner_hint else "")
            + ". Wird jemand anderes angesprochen, mischst du dich nicht ein. "
            "Antworte kurz (hoechstens 4 Saetze), locker und passend zum Verlauf "
            "und sprich die Person bei Bedarf mit Namen an. Kein Markdown, keine "
            "Tabellen. Du kannst hier KEINE Aktionen am PC ausfuehren - biete "
            "das nicht an."
        )
    else:
        system += (
            f"\n\nDu chattest gerade privat mit {sender} auf Telegram. "
            "Antworte kurz und natuerlich, kein Markdown, keine Tabellen. "
            "Du kannst hier keine Aktionen am PC ausfuehren."
        )
    user = ""
    if transcript:
        user += f"Bisheriger Gespraechsverlauf:\n{transcript}\n\n"
    user += f"Neue Nachricht von {sender} an dich: {question}"
    answer = await complete(
        system,
        user,
        provider=provider or None,
        model=model or None,
        max_tokens=700,
        temperature=0.8,
        slot=slot,
    )
    return answer.strip() or "Hm, dazu faellt mir gerade nichts ein."


class GroupBot:
    key = "bot"
    display_name = "Bot"
    persona_variant = "papa"
    slot = "jon"
    token_setting = ""
    partner_hint = ""

    def __init__(self) -> None:
        self._offset = 0
        self._username = ""
        self._username_token = ""

    def token(self) -> str:
        from app.services.settings_service import get_settings_service

        return str(get_settings_service().get().get(self.token_setting, "")).strip()

    def selection(self) -> tuple[str, str]:
        from app.services.settings_service import get_settings_service

        return get_settings_service().telegram_selection()

    async def _api(
        self,
        method: str,
        payload: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict:
        token = self.token()
        if not token:
            return {}
        url = f"https://api.telegram.org/bot{token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                if data or files:
                    response = await client.post(url, data=data, files=files)
                else:
                    response = await client.post(url, json=payload or {})
                return response.json()
        except Exception:
            return {}

    async def username(self) -> str:
        token = self.token()
        if not token:
            return ""
        if token == self._username_token and self._username:
            return self._username
        result = await self._api("getMe")
        name = str(((result or {}).get("result") or {}).get("username") or "")
        if name:
            self._username = name
            self._username_token = token
        return name

    async def send(self, chat_id: str | int, text: str) -> None:
        for start in range(0, max(len(text), 1), 3900):
            await self._api(
                "sendMessage",
                {"chat_id": chat_id, "text": text[start : start + 3900]},
            )

    async def send_animation(
        self, chat_id: str | int, path, caption: str = ""
    ) -> None:
        try:
            raw = path.read_bytes()
        except Exception:
            await self.send(chat_id, caption or "😴")
            return
        result = await self._api(
            "sendAnimation",
            data={"chat_id": str(chat_id), "caption": caption[:1000]},
            files={"animation": (path.name, raw, "image/gif")},
        )
        if not result.get("ok"):
            await self.send(chat_id, caption or "😴")

    async def handle_command(self, chat_id: str, command: str, is_group: bool) -> bool:
        return False

    async def blocked_reply(self, chat_id: str) -> bool:
        return False

    async def answer(
        self, chat_id: str, sender: str, question: str, transcript: str, is_group: bool
    ) -> str:
        provider, model = self.selection()
        return await group_answer(
            self.persona_variant,
            await self.username(),
            sender,
            question,
            transcript=transcript,
            group=is_group,
            partner_hint=self.partner_hint,
            provider=provider,
            model=model,
            slot=self.slot,
        )

    async def _respond(
        self, chat_id: str, sender: str, question: str, transcript: str, is_group: bool
    ) -> None:
        if await self.blocked_reply(chat_id):
            return
        await self._api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        try:
            answer = await asyncio.wait_for(
                self.answer(chat_id, sender, question, transcript, is_group),
                timeout=ANSWER_TIMEOUT,
            )
        except Exception:
            answer = FEHLER_ANTWORT
        get_group_memory().record(chat_id, self.display_name, answer, bot=self.key)
        await self.send(chat_id, answer)

    async def handle_message(self, message: dict) -> None:
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        if not chat_id:
            return
        text = (message.get("text") or message.get("caption") or "").strip()
        if not text:
            return
        sender_info = message.get("from") or {}
        sender = str(
            sender_info.get("first_name") or sender_info.get("username") or "Jemand"
        ).strip()
        is_group = str(chat.get("type") or "") in GROUP_CHAT_TYPES
        username = await self.username()
        if text.startswith("/"):
            command = text.split()[0]
            if "@" in command:
                command, target = command.split("@", 1)
                if username and target.lower() != username.lower():
                    return
            if await self.handle_command(chat_id, command.lower(), is_group):
                return
            if is_group:
                return
        if is_group:
            get_group_memory().record(
                chat_id, sender, text, message_id=message.get("message_id")
            )
            if not username or not is_mentioned(
                text, message.get("entities"), username
            ):
                return
            question = strip_mention(text, username) or "Hallo!"
        else:
            get_group_memory().record(
                chat_id, sender, text, message_id=message.get("message_id")
            )
            question = text
        transcript = get_group_memory().transcript(chat_id)
        await self._respond(chat_id, sender, question, transcript, is_group)

    async def poll_once(self) -> None:
        token = self.token()
        if not token:
            await asyncio.sleep(5)
            return
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"timeout": 25, "offset": self._offset},
                )
                data = response.json()
        except Exception:
            await asyncio.sleep(10)
            return
        if not data.get("ok"):
            await asyncio.sleep(30)
            return
        for update in data.get("result", []):
            self._offset = max(self._offset, int(update["update_id"]) + 1)
            message = update.get("message") or {}
            if message:
                try:
                    await self.handle_message(message)
                except Exception:
                    continue


class MiniJonBot(GroupBot):
    key = "mini_jon"
    display_name = "Mini Jon"
    persona_variant = "junior"
    slot = "emil"
    token_setting = "mini_jon_bot_token"
    partner_hint = "dein Papa Jon mit seinem eigenen Bot"

    async def handle_command(self, chat_id: str, command: str, is_group: bool) -> bool:
        from app.services.mini_jon_service import get_mini_jon_service

        service = get_mini_jon_service()
        if command in ("/schlafen", "/schlaf"):
            service.set_status("schlaeft")
            await self.send_sleep(
                chat_id,
                "Pssst … Mini Jon ist eingeschlafen. 😴 Mit /aufwachen weckst du ihn wieder.",
            )
            return True
        if command in ("/aufwachen", "/aufstehen", "/wach"):
            was_sleeping = service.is_sleeping()
            service.set_status("wach")
            if was_sleeping:
                await self.send(
                    chat_id,
                    "Uaaah … *gaehnt und reibt sich die Augen* … Ich bin wach! 🌞 Was gibt's?",
                )
            else:
                await self.send(chat_id, "Ich bin doch schon wach! 😄")
            return True
        if command == "/start":
            await self.send(
                chat_id,
                "Hallo, ich bin Mini Jon! 👋 In Gruppen lese ich mit und antworte, "
                "wenn du mich mit @" + (await self.username() or "…") + " ansprichst. "
                "Mit /schlafen schicke ich mich ins Bett, mit /aufwachen bin ich "
                "wieder da.",
            )
            return True
        return False

    async def blocked_reply(self, chat_id: str) -> bool:
        from app.services.mini_jon_service import get_mini_jon_service

        if not get_mini_jon_service().is_sleeping():
            return False
        await self.send_sleep(
            chat_id,
            "😴 Mini Jon schlaeft gerade tief und fest … Weck ihn mit /aufwachen.",
        )
        return True

    async def send_sleep(self, chat_id: str, caption: str) -> None:
        from app.services.mini_jon_service import get_mini_jon_service

        path = await asyncio.to_thread(get_mini_jon_service().sleep_animation)
        if path is not None:
            await self.send_animation(chat_id, path, caption)
        else:
            await self.send(chat_id, caption)


_bots: list[GroupBot] | None = None


def get_group_bots() -> list[GroupBot]:
    global _bots
    if _bots is None:
        _bots = [MiniJonBot()]
    return _bots
