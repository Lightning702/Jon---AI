from __future__ import annotations

import asyncio

import httpx

from app.services.settings_service import get_settings_service


class TelegramService:
    def __init__(self) -> None:
        self._offset = 0
        self._histories: dict[str, list[dict]] = {}
        self._chat_service = None

    def _token(self) -> str:
        return str(get_settings_service().get().get("telegram_bot_token", "")).strip()

    async def _api(self, method: str, payload: dict) -> None:
        token = self._token()
        if not token:
            return
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/{method}", json=payload
                )
        except Exception:
            pass

    async def send(self, chat_id: str | int, text: str) -> None:
        for start in range(0, max(len(text), 1), 3900):
            await self._api(
                "sendMessage",
                {"chat_id": chat_id, "text": text[start : start + 3900]},
            )

    async def _typing(self, chat_id: str | int) -> None:
        while True:
            await self._api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
            await asyncio.sleep(4)

    async def _answer(self, chat_id: str, text: str) -> str:
        from app.schemas import ChatIn, MessageIn
        from app.services.chat_service import ChatService

        if self._chat_service is None:
            self._chat_service = ChatService()
        history = self._histories.setdefault(chat_id, [])
        history.append({"role": "user", "content": text})
        del history[:-8]
        provider, model = get_settings_service().telegram_selection()
        payload = ChatIn(
            messages=[MessageIn(**m) for m in history],
            persist=False,
            tool_mode="allow",
            max_tokens=2048,
            provider=provider or None,
            model=model or None,
        )
        parts: list[str] = []
        tools: list[str] = []
        announced = 0
        async for event in self._chat_service.stream(payload):
            kind = event.get("type")
            if kind == "content":
                parts.append(event.get("delta") or "")
            elif kind == "tool" and event.get("status") == "running":
                if announced < 3:
                    announced += 1
                    summary = event.get("summary") or event.get("name") or "Aktion"
                    await self.send(chat_id, f"⚙️ {summary}")
            elif kind == "tool" and event.get("status") == "done":
                if event.get("ok") and event.get("name"):
                    tools.append(str(event["name"]))
            elif kind == "error":
                parts.append(f"[Fehler] {event.get('message', '')}")
        answer = "".join(parts).strip()
        if not answer and tools:
            answer = "Erledigt ✅ (" + ", ".join(dict.fromkeys(tools)) + ")"
        if not answer:
            answer = "Da kam leider keine Antwort zurück."
        history.append({"role": "assistant", "content": answer})
        del history[:-8]
        return answer

    async def _handle(self, chat_id: str, text: str) -> None:
        typing = asyncio.create_task(self._typing(chat_id))
        try:
            answer = await asyncio.wait_for(self._answer(chat_id, text), timeout=180)
        except asyncio.TimeoutError:
            answer = (
                "Das hat zu lange gedauert. Versuch es nochmal oder wähle am PC "
                "ein schnelleres Modell."
            )
        except Exception as exc:
            answer = f"Da ist etwas schiefgelaufen: {exc}"
        finally:
            typing.cancel()
        await self.send(chat_id, answer)

    async def poll_once(self) -> None:
        token = self._token()
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
            chat_id = (message.get("chat") or {}).get("id")
            text = (message.get("text") or "").strip()
            if not chat_id or not text:
                continue
            settings = get_settings_service()
            bound = str(settings.get().get("telegram_chat_id", "")).strip()
            if not bound:
                settings.update({"telegram_chat_id": str(chat_id)})
                await self.send(
                    chat_id,
                    "Verbunden! 🤝 Ich bin Jon und dieser Chat ist jetzt fest mit "
                    "deinem PC verknüpft. Schreib mir einfach, was ich tun soll.",
                )
                if text.startswith("/start"):
                    continue
                bound = str(chat_id)
            if str(chat_id) != bound:
                await self.send(chat_id, "Dieser Jon gehört schon jemand anderem. 🔒")
                continue
            if text.startswith("/start"):
                await self.send(
                    chat_id,
                    "Ich bin da. 👋 Schreib mir, was ich auf deinem PC tun soll "
                    "— zum Beispiel: Öffne YouTube · Spiel was Entspanntes · "
                    "Wie geht es meinem PC? · Hab ich neue Mails?\n\n"
                    "Mit /reset vergesse ich unser bisheriges Gespräch.",
                )
                continue
            if text.startswith("/reset"):
                self._histories.pop(str(chat_id), None)
                await self.send(chat_id, "Gespräch zurückgesetzt. 🧹")
                continue
            asyncio.create_task(self._handle(str(chat_id), text))


_service: TelegramService | None = None


def get_telegram_service() -> TelegramService:
    global _service
    if _service is None:
        _service = TelegramService()
    return _service
