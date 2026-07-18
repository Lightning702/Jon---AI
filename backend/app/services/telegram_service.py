from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import httpx

from app.core.config import DATA_DIR
from app.services.settings_service import get_settings_service

HISTORY_FILE = DATA_DIR / "telegram_memory.json"
HISTORY_KEEP = 40
HISTORY_SEND = 12
MORNING_STATE_FILE = DATA_DIR / "telegram_morning.json"


class TelegramService:
    def __init__(self) -> None:
        self._offset = 0
        self._histories: dict[str, list[dict]] = self._load_histories()
        self._chat_service = None
        self._voice_reply: set[str] = set()
        self._voice_off: set[str] = set()
        self._running: dict[str, asyncio.Task] = {}
        self._last_morning = self._load_morning()

    def _load_histories(self) -> dict[str, list[dict]]:
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    str(key): value
                    for key, value in data.items()
                    if isinstance(value, list)
                }
        except Exception:
            pass
        return {}

    def _save_histories(self) -> None:
        try:
            HISTORY_FILE.write_text(
                json.dumps(self._histories, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load_morning(self) -> str:
        try:
            return str(json.loads(MORNING_STATE_FILE.read_text(encoding="utf-8")).get("last", ""))
        except Exception:
            return ""

    def _save_morning(self, day: str) -> None:
        self._last_morning = day
        try:
            MORNING_STATE_FILE.write_text(
                json.dumps({"last": day}, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

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

    async def send_voice(self, chat_id: str | int, text: str) -> bool:
        token = self._token()
        if not token:
            return False
        try:
            from app.services.voice_service import synthesize_speech

            mp3 = await synthesize_speech(text[:1200], rate="+6%")
            if not mp3:
                return False
            ogg = await asyncio.to_thread(self._to_ogg, mp3)
            if ogg is None:
                return False
            async with httpx.AsyncClient(timeout=45) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendVoice",
                    data={"chat_id": str(chat_id)},
                    files={"voice": ("jon.ogg", ogg, "audio/ogg")},
                )
            return True
        except Exception:
            return False

    def _to_ogg(self, mp3: bytes) -> bytes | None:
        import shutil

        if not shutil.which("ffmpeg"):
            return None
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.mp3"
            dst = Path(tmp) / "out.ogg"
            src.write_bytes(mp3)
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(src),
                    "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1",
                    str(dst),
                ],
                capture_output=True,
            )
            if result.returncode != 0 or not dst.exists():
                return None
            return dst.read_bytes()

    async def _transcribe(self, file_id: str) -> str:
        token = self._token()
        if not token:
            return ""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                info = await client.get(
                    f"https://api.telegram.org/bot{token}/getFile",
                    params={"file_id": file_id},
                )
                file_path = info.json()["result"]["file_path"]
                audio = await client.get(
                    f"https://api.telegram.org/file/bot{token}/{file_path}"
                )
                raw = audio.content
        except Exception:
            return ""
        wav = await asyncio.to_thread(self._to_wav, raw)
        if wav is None:
            return ""
        try:
            from app.services.voice_service import VoiceService

            return await asyncio.to_thread(VoiceService().transcribe_wav, wav, "de-DE")
        except Exception:
            return ""

    def _to_wav(self, audio: bytes) -> bytes | None:
        import shutil

        if not shutil.which("ffmpeg"):
            return None
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.ogg"
            dst = Path(tmp) / "out.wav"
            src.write_bytes(audio)
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
                capture_output=True,
            )
            if result.returncode != 0 or not dst.exists():
                return None
            return dst.read_bytes()

    async def _analyze_photo(self, file_id: str, name: str, mime: str) -> str:
        import base64

        token = self._token()
        if not token:
            return ""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                info = await client.get(
                    f"https://api.telegram.org/bot{token}/getFile",
                    params={"file_id": file_id},
                )
                file_path = info.json()["result"]["file_path"]
                image = await client.get(
                    f"https://api.telegram.org/file/bot{token}/{file_path}"
                )
                raw = image.content
        except Exception:
            return ""
        from app.services.attachment_service import get_attachment_service

        result = await get_attachment_service().extract(
            name, mime, base64.b64encode(raw).decode("ascii")
        )
        if "error" in result:
            return ""
        return str(result.get("content", ""))

    async def _typing(self, chat_id: str | int) -> None:
        while True:
            await self._api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
            await asyncio.sleep(4)

    def _system_message(self) -> dict:
        from app.services.persona_service import get_persona_service

        system = self._chat_service._system_prompt()
        memory = get_persona_service().read_memory_file(max_chars=6000).strip()
        if memory and memory[:400] not in system:
            system += "\n\nDEIN PERSOENLICHES GEDAECHTNIS (MEMORY.md):\n" + memory
        system += (
            "\n\nDu antwortest gerade ueber Telegram auf dem Handy des Nutzers. "
            "Halte Antworten kompakt und gut lesbar ohne Markdown-Tabellen. "
            "Du steuerst dabei wirklich seinen PC zuhause: Sagt er z. B. "
            "'schreibe hallo', rufe keyboard_type mit dem Text auf. Sagt er "
            "'linksklicke' oder 'klick', rufe mouse_click OHNE x und y auf - "
            "dann wird an der aktuellen Mausposition geklickt, ohne die Maus zu "
            "bewegen. Uebergib x/y nur, wenn er ein konkretes Ziel nennt. "
            "keyboard_press drueckt einzelne Tasten, keyboard_hotkey "
            "Kombinationen, screenshot zeigt dir den Bildschirm. Fuehre solche "
            "Befehle direkt aus, statt nachzufragen."
        )
        return {"role": "system", "content": system}

    async def _answer(self, chat_id: str, text: str) -> str:
        from app.core.config import get_settings
        from app.schemas import ChatIn, MessageIn
        from app.services.chat_service import ChatService

        if self._chat_service is None:
            self._chat_service = ChatService()
        history = self._histories.setdefault(chat_id, [])
        history.append({"role": "user", "content": text})
        del history[:-HISTORY_KEEP]
        self._save_histories()
        provider, model = get_settings_service().telegram_selection()
        settings = get_settings()
        messages = [self._system_message(), *history[-HISTORY_SEND:]]
        payload = ChatIn(
            messages=[MessageIn(**m) for m in messages],
            persist=False,
            tool_mode="allow",
            max_tokens=2048,
            provider=provider or settings.default_provider,
            model=model or settings.emil_model,
            slot="emil",
            source="telegram",
        )
        parts: list[str] = []
        done_summaries: list[str] = []
        running_summaries: dict[str, str] = {}
        announced = 0
        async for event in self._chat_service.stream(payload):
            kind = event.get("type")
            if kind == "content":
                parts.append(event.get("delta") or "")
            elif kind == "tool" and event.get("status") == "running":
                summary = event.get("summary") or event.get("name") or "Aktion"
                if event.get("name"):
                    running_summaries[str(event["name"])] = str(summary)
                if announced < 3:
                    announced += 1
                    await self.send(chat_id, f"⚙️ {summary}")
            elif kind == "tool" and event.get("status") == "done":
                if event.get("ok") and event.get("name"):
                    name = str(event["name"])
                    done_summaries.append(running_summaries.get(name, name))
            elif kind == "error":
                parts.append(f"[Fehler] {event.get('message', '')}")
        answer = "".join(parts).strip()
        executed = list(dict.fromkeys(done_summaries))
        if not answer and executed:
            answer = "Erledigt ✅"
        if not answer:
            answer = "Da kam leider keine Antwort zurück."
        history.append({"role": "assistant", "content": answer})
        del history[:-HISTORY_KEEP]
        self._save_histories()
        if executed:
            report = "\n".join(f"• {s}" for s in executed[:8])
            answer = f"{answer}\n\n✅ Ausgeführte Befehle:\n{report}"
        return answer

    def _direct_control(self, text: str) -> str | None:
        raw = text.strip()
        low = raw.lower().strip(" .!?")
        if not low:
            return None
        from app.services.automation_service import AutomationService

        auto = AutomationService()

        def log(tool: str, args: dict, result: str) -> None:
            from app.services.action_log_service import log_action

            log_action("telegram", tool, args, result, ok="error" not in result)

        try:
            for trigger in ("schreibe ", "schreib ", "tippe ", "tipp ", "type "):
                if low.startswith(trigger):
                    payload = raw[len(trigger):].strip().strip('"').strip("'")
                    if not payload:
                        return None
                    auto.keyboard_type(payload, False)
                    log("keyboard_type", {"text": payload}, "ok")
                    return f"⌨️ Geschrieben: {payload}"
            for trigger in ("drücke ", "druecke ", "drück ", "drueck ", "taste "):
                if low.startswith(trigger):
                    key = low[len(trigger):].strip().replace("die ", "").replace(
                        "-taste", ""
                    ).strip()
                    key = {
                        "eingabe": "enter",
                        "eingabetaste": "enter",
                        "zurück": "backspace",
                        "zurueck": "backspace",
                        "leertaste": "space",
                        "leer": "space",
                        "escape": "esc",
                        "hoch": "up",
                        "runter": "down",
                        "rechts": "right",
                        "links": "left",
                    }.get(key, key)
                    if not key:
                        return None
                    auto.keyboard_press(key, 1)
                    log("keyboard_press", {"key": key}, "ok")
                    return f"⌨️ Taste gedrückt: {key}"
            if low in ("enter", "eingabe", "bestätigen", "bestaetigen", "senden"):
                auto.keyboard_press("enter", 1)
                log("keyboard_press", {"key": "enter"}, "ok")
                return "⌨️ Enter gedrückt"
            if low in (
                "doppelklick",
                "doppel klick",
                "doppelklicke",
                "doppelt klicken",
                "doppelklicken",
            ):
                auto.mouse_click(None, None, "left", 2)
                log("mouse_click", {"clicks": 2}, "ok")
                return "🖱️ Doppelklick"
            if any(
                low == v or low.startswith(v + " ")
                for v in (
                    "rechtsklick",
                    "rechts klick",
                    "rechtsklicke",
                    "rechtsklicken",
                    "rechte maustaste",
                )
            ):
                auto.mouse_click(None, None, "right", 1)
                log("mouse_click", {"button": "right"}, "ok")
                return "🖱️ Rechtsklick"
            if any(
                low == v or low.startswith(v + " ")
                for v in (
                    "klick",
                    "klicke",
                    "klick mal",
                    "klicken",
                    "linksklick",
                    "links klick",
                    "linksklicke",
                    "linksklicken",
                    "mausklick",
                    "click",
                    "drauf klicken",
                    "drauf klick",
                )
            ):
                auto.mouse_click(None, None, "left", 1)
                log("mouse_click", {"button": "left"}, "ok")
                return "🖱️ Linksklick (an aktueller Mausposition)"
            if any(
                w in low
                for w in ("scroll", "scrolle", "runterscrollen", "hochscrollen")
            ):
                down = not any(w in low for w in ("hoch", "oben", "up"))
                auto.mouse_scroll(-600 if down else 600)
                log("mouse_scroll", {"down": down}, "ok")
                return "🖱️ Gescrollt " + ("runter" if down else "hoch")
        except Exception as exc:
            return f"Das ging nicht: {exc}"
        return None

    async def _handle(self, chat_id: str, text: str, voice: bool = False) -> None:
        direct = await asyncio.to_thread(self._direct_control, text)
        if direct is not None:
            history = self._histories.setdefault(chat_id, [])
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": direct})
            del history[:-HISTORY_KEEP]
            self._save_histories()
            wants_voice = (
                voice or chat_id in self._voice_reply
            ) and chat_id not in self._voice_off
            if wants_voice:
                await self.send_voice(chat_id, direct)
            else:
                await self.send(chat_id, direct)
            return
        typing = asyncio.create_task(self._typing(chat_id))
        try:
            answer = await asyncio.wait_for(self._answer(chat_id, text), timeout=180)
        except asyncio.CancelledError:
            typing.cancel()
            return
        except asyncio.TimeoutError:
            answer = (
                "Das hat zu lange gedauert. Versuch es nochmal oder wähle am PC "
                "ein schnelleres Modell."
            )
        except Exception as exc:
            answer = f"Da ist etwas schiefgelaufen: {exc}"
        finally:
            typing.cancel()
        wants_voice = (voice or chat_id in self._voice_reply) and chat_id not in self._voice_off
        if wants_voice:
            await self.send_voice(chat_id, answer)
        await self.send(chat_id, answer)

    def _launch(self, chat_id: str, text: str, voice: bool = False) -> None:
        old = self._running.get(chat_id)
        if old and not old.done():
            old.cancel()
        task = asyncio.create_task(self._handle(chat_id, text, voice))
        self._running[chat_id] = task

    async def _cancel_running(self, chat_id: str) -> bool:
        task = self._running.get(chat_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def _morning_calendar(self, now: datetime) -> dict:
        from datetime import timedelta

        try:
            from app.services.calendar_service import get_calendar_service

            service = get_calendar_service()
        except Exception:
            return {"heute": [], "morgen_erinnerungen": []}
        today = now.strftime("%Y-%m-%d")
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        def slim(e: dict) -> dict:
            return {
                "titel": e.get("titel", ""),
                "zeit": e.get("zeit", ""),
                "typ": e.get("typ", "termin"),
                "quelle": e.get("quelle", ""),
            }

        try:
            heute = [
                slim(e)
                for e in service.merged(start=today, days=1)
                if e.get("datum") == today and not e.get("erledigt")
            ]
        except Exception:
            heute = []
        try:
            morgen = [
                slim(e)
                for e in service.merged(start=tomorrow, days=1)
                if e.get("datum") == tomorrow
                and not e.get("erledigt")
                and (e.get("typ") == "erinnerung" or e.get("quelle") == "erinnerung")
            ]
        except Exception:
            morgen = []
        return {"heute": heute, "morgen_erinnerungen": morgen}

    def _morning_fallback(self, cal: dict) -> str:
        parts = ["Guten Morgen, Felix! Ich wünsche dir einen richtig guten Start in den Tag."]
        if cal["heute"]:
            eintraege = ", ".join(
                (f"{e['zeit']} Uhr {e['titel']}" if e["zeit"] else e["titel"])
                for e in cal["heute"][:6]
            )
            parts.append(f"Heute steht an: {eintraege}.")
        if cal["morgen_erinnerungen"]:
            morgen = ", ".join(e["titel"] for e in cal["morgen_erinnerungen"][:6])
            parts.append(f"Und denk schon mal an morgen: {morgen}.")
        return " ".join(parts)

    async def morning_tick(self) -> None:
        data = get_settings_service().get()
        if not data.get("telegram_morning", False):
            return
        chat_id = str(data.get("telegram_chat_id", "")).strip()
        if not chat_id or not self._token():
            return
        target = str(data.get("telegram_morning_time", "07:30")).strip() or "07:30"
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if self._last_morning == today or now.strftime("%H:%M") < target:
            return
        self._save_morning(today)
        cal = self._morning_calendar(now)
        try:
            from app.services.show_service import _today_data
            from app.services.llm import complete

            payload = {"tagesdaten": _today_data(), "kalender": cal}
            context = json.dumps(payload, ensure_ascii=False)
            text = await complete(
                "Du bist Jon und sprichst dem Nutzer Felix eine persönliche "
                "Guten-Morgen-Sprachnachricht auf sein Handy. Kurz (4-7 Sätze), warm, "
                "natürlich gesprochen: begrüße ihn, nenne das Wetter. Zähle dann die "
                "heutigen Termine, Tasks und Erinnerungen aus kalender.heute mit Uhrzeit "
                "auf, falls vorhanden. Gibt es Einträge in kalender.morgen_erinnerungen, "
                "erinnere ihn zusätzlich freundlich schon heute daran, dass diese "
                "Erinnerung morgen ansteht. Wünsche einen guten Start. Nutze nur echte "
                "Daten, erfinde nichts. Kein Markdown, keine Aufzählung mit Strichen.",
                f"Heutige Daten:\n{context}",
                max_tokens=500,
                temperature=0.8,
            )
        except Exception:
            text = self._morning_fallback(cal)
        text = text.strip() or self._morning_fallback(cal)
        spoke = await self.send_voice(chat_id, text)
        await self.send(chat_id, "🌅 " + text)

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
            voice_msg = message.get("voice") or message.get("audio")
            if not chat_id:
                continue
            is_voice = False
            if not text and voice_msg and voice_msg.get("file_id"):
                await self._api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
                text = (await self._transcribe(voice_msg["file_id"])).strip()
                is_voice = True
                if not text:
                    await self.send(
                        chat_id,
                        "Ich konnte die Sprachnachricht leider nicht verstehen. "
                        "Versuch es nochmal oder schreib mir.",
                    )
                    continue
            photo = message.get("photo") or []
            doc = message.get("document") or {}
            image_file = None
            image_mime = "image/jpeg"
            image_name = "foto.jpg"
            if photo:
                image_file = photo[-1].get("file_id")
            elif (
                str(doc.get("mime_type", "")).startswith("image/")
                and doc.get("file_id")
            ):
                image_file = doc["file_id"]
                image_mime = str(doc["mime_type"])
                image_name = str(doc.get("file_name") or "bild.png")
            if not text and image_file:
                await self._api(
                    "sendChatAction", {"chat_id": chat_id, "action": "typing"}
                )
                beschreibung = await self._analyze_photo(
                    image_file, image_name, image_mime
                )
                if not beschreibung:
                    await self.send(
                        chat_id,
                        "Ich konnte das Bild leider nicht analysieren - "
                        "dafuer brauche ich einen Anbieter mit Vision-Modell "
                        "(z. B. NVIDIA oder OpenAI).",
                    )
                    continue
                caption = (message.get("caption") or "").strip()
                text = (
                    "Ich habe dir ein Foto geschickt. Das ist darauf zu sehen "
                    f"(automatische Bildanalyse): {beschreibung}"
                )
                if caption:
                    text += f"\n\nMeine Frage dazu: {caption}"
                else:
                    text += (
                        "\n\nSag mir kurz, was du siehst und was dir auffaellt."
                    )
            if not text:
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
                    "Ich bin da. 👋 Schreib oder sprich mir, was ich auf deinem PC "
                    "tun soll — zum Beispiel: Öffne YouTube · Spiel was Entspanntes · "
                    "Wie geht es meinem PC? · Hab ich neue Mails?\n\n"
                    "Schick mir gerne auch eine Sprachnachricht. Befehle: /stimme = "
                    "ich antworte per Sprachnachricht · /endstimme = nur noch Text · "
                    "/stopp = laufende Aktion abbrechen · /reset = Gespräch vergessen.",
                )
                continue
            if text.startswith("/reset"):
                self._histories.pop(str(chat_id), None)
                self._save_histories()
                await self.send(chat_id, "Gespräch zurückgesetzt. 🧹")
                continue
            if text.startswith("/stopp") or text.startswith("/stop"):
                stopped = await self._cancel_running(str(chat_id))
                await self.send(
                    chat_id,
                    "Abgebrochen. ⛔" if stopped else "Gerade läuft nichts, alles ruhig. 👍",
                )
                continue
            if text.startswith("/endstimme"):
                self._voice_off.add(str(chat_id))
                self._voice_reply.discard(str(chat_id))
                await self.send(chat_id, "Okay, keine Sprachnachrichten mehr — nur noch Text. 💬")
                continue
            if text.startswith("/stimme") or text.startswith("/voice"):
                self._voice_off.discard(str(chat_id))
                self._voice_reply.add(str(chat_id))
                await self.send(
                    chat_id, "Alles klar, ich antworte dir jetzt als Sprachnachricht. 🎙️"
                )
                continue
            self._launch(str(chat_id), text, voice=is_voice)


_service: TelegramService | None = None


def get_telegram_service() -> TelegramService:
    global _service
    if _service is None:
        _service = TelegramService()
    return _service
