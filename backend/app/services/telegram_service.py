from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx

from app.core.config import DATA_DIR
from app.services.settings_service import get_settings_service
from app.core.store import atomic_write_bytes, atomic_write_text
from app.core.fehler import leise
from app.core.logbook import logger as logbook_logger

HISTORY_FILE = DATA_DIR / "telegram_memory.json"
HISTORY_KEEP = 40
HISTORY_SEND = 12
ZEITLIMIT = 300
OLLAMA_LISTE = 12
MORNING_STATE_FILE = DATA_DIR / "telegram_morning.json"


_log = logbook_logger("telegram")


class TelegramService:
    def __init__(self) -> None:
        self._offset = 0
        self._histories: dict[str, list[dict]] = self._load_histories()
        self._chat_service = None
        self._voice_reply: set[str] = set()
        self._voice_off: set[str] = set()
        self._running: dict[str, list[asyncio.Task]] = {}
        self._last_morning = self._load_morning()
        self._pending_place: dict[str, str] = {}
        self._username = ""
        self._username_token = ""
        self._research_watch: dict[str, asyncio.Task] = {}
        self._last_home = 0.0
        self._stand: dict = {
            "letzte_abfrage": 0.0,
            "letzter_fehler": "",
            "fehler_zeit": 0.0,
            "updates": 0,
            "webhook_entfernt": 0.0,
            "gruppen": {},
        }

    def _fehler_merken(self, text: str) -> None:
        self._stand["letzter_fehler"] = str(text)[:400]
        self._stand["fehler_zeit"] = time.time()
        _log.warning("Telegram: %s", str(text)[:200])

    def _gruppe_merken(self, chat: dict, feld: str) -> None:
        chat_id = str(chat.get("id") or "")
        if not chat_id:
            return
        gruppen = self._stand["gruppen"]
        eintrag = gruppen.setdefault(
            chat_id,
            {
                "titel": str(chat.get("title") or ""),
                "gesehen": 0,
                "erwaehnt": 0,
                "geantwortet": 0,
                "zuletzt": 0.0,
            },
        )
        if chat.get("title"):
            eintrag["titel"] = str(chat["title"])
        eintrag[feld] = int(eintrag.get(feld, 0)) + 1
        eintrag["zuletzt"] = time.time()
        if len(gruppen) > 20:
            aeltester = min(gruppen, key=lambda k: gruppen[k].get("zuletzt", 0.0))
            gruppen.pop(aeltester, None)

    async def _webhook_loesen(self) -> None:
        token = self._token()
        if not token:
            return
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/deleteWebhook",
                    json={"drop_pending_updates": False},
                )
        except Exception as fehler:
            leise(fehler, "services/telegram_service")
            return
        self._stand["webhook_entfernt"] = time.time()
        _log.info("Telegram: Webhook entfernt, Jon holt die Nachrichten selbst")

    async def diagnose(self) -> dict:
        token = self._token()
        stand = {
            "token_gesetzt": bool(token),
            "bot": "",
            "bot_name": "",
            "gruppen_erlaubt": None,
            "liest_alles": None,
            "webhook": "",
            "webhook_fehler": "",
            "offene_updates": 0,
            "letzte_abfrage": self._stand["letzte_abfrage"],
            "letzter_fehler": self._stand["letzter_fehler"],
            "fehler_zeit": self._stand["fehler_zeit"],
            "updates": self._stand["updates"],
            "webhook_entfernt": self._stand["webhook_entfernt"],
            "gruppen": [
                {"chat_id": kennung, **werte}
                for kennung, werte in self._stand["gruppen"].items()
            ],
            "hinweise": [],
        }
        if not token:
            stand["hinweise"].append(
                "Es ist kein Bot-Token eingetragen. Auf diesem Geraet laeuft also "
                "kein Telegram-Bot - trag ihn unter Einstellungen -> Verbindungen "
                "ein (jedes Geraet braucht seinen eigenen Bot)."
            )
            return stand
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                mich = (
                    await client.get(f"https://api.telegram.org/bot{token}/getMe")
                ).json()
                haken = (
                    await client.get(
                        f"https://api.telegram.org/bot{token}/getWebhookInfo"
                    )
                ).json()
        except Exception as fehler:
            stand["hinweise"].append(f"Telegram ist nicht erreichbar: {fehler}")
            return stand
        if not mich.get("ok"):
            stand["hinweise"].append(
                "Telegram kennt diesen Token nicht (mehr): "
                + str(mich.get("description") or "")
            )
            return stand
        angaben = mich.get("result") or {}
        stand["bot"] = str(angaben.get("username") or "")
        stand["bot_name"] = str(angaben.get("first_name") or "")
        stand["gruppen_erlaubt"] = bool(angaben.get("can_join_groups"))
        stand["liest_alles"] = bool(angaben.get("can_read_all_group_messages"))
        haken_daten = (haken.get("result") or {}) if haken.get("ok") else {}
        stand["webhook"] = str(haken_daten.get("url") or "")
        stand["webhook_fehler"] = str(haken_daten.get("last_error_message") or "")
        stand["offene_updates"] = int(haken_daten.get("pending_update_count") or 0)
        if stand["webhook"]:
            stand["hinweise"].append(
                "Fuer diesen Bot ist ein Webhook eingetragen - solange der steht, "
                "bekommt Jon keine einzige Nachricht. Ich entferne ihn gleich; "
                "danach sollte der Bot wieder antworten."
            )
            await self._webhook_loesen()
        if stand["gruppen_erlaubt"] is False:
            stand["hinweise"].append(
                "Dieser Bot darf keinen Gruppen beitreten. Im BotFather: "
                "/setjoingroups -> Enable."
            )
        gesehen = sum(int(g.get("gesehen", 0)) for g in stand["gruppen"])
        erwaehnt = sum(int(g.get("erwaehnt", 0)) for g in stand["gruppen"])
        if not stand["gruppen"]:
            stand["hinweise"].append(
                "In Gruppen ist bei diesem Bot noch keine Nachricht angekommen. "
                "Meist liegt es am Privatsphaere-Modus: Aenderungen daran wirken "
                "erst, wenn der Bot neu zur Gruppe hinzugefuegt wird. Im BotFather "
                "/setprivacy -> Disable, dann den Bot aus der Gruppe nehmen und "
                "wieder hinzufuegen."
            )
        elif gesehen and not erwaehnt:
            stand["hinweise"].append(
                "Nachrichten kommen an, aber keine Erwaehnung von @"
                + (stand["bot"] or "botname")
                + ". In Gruppen antwortet Jon nur, wenn du ihn so ansprichst."
            )
        if not stand["hinweise"]:
            stand["hinweise"].append(
                "Alles in Ordnung: Der Bot ist erreichbar und holt seine "
                "Nachrichten selbst ab."
            )
        return stand

    def _load_histories(self) -> dict[str, list[dict]]:
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    str(key): value
                    for key, value in data.items()
                    if isinstance(value, list)
                }
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")
        return {}

    def _save_histories(self) -> None:
        try:
            atomic_write_text(HISTORY_FILE,
                json.dumps(self._histories, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")

    def _load_morning(self) -> str:
        try:
            return str(json.loads(MORNING_STATE_FILE.read_text(encoding="utf-8")).get("last", ""))
        except Exception:
            return ""

    def _save_morning(self, day: str) -> None:
        self._last_morning = day
        try:
            atomic_write_text(MORNING_STATE_FILE,
                json.dumps({"last": day}, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")

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
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")

    async def bot_username(self) -> str:
        token = self._token()
        if not token:
            return ""
        if token == self._username_token and self._username:
            return self._username
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe"
                )
                data = response.json()
        except Exception:
            return ""
        name = str(((data or {}).get("result") or {}).get("username") or "")
        if name:
            self._username = name
            self._username_token = token
        return name

    async def _handle_group_message(self, message: dict) -> None:
        from app.services.telegram_group_service import (
            FEHLER_ANTWORT,
            get_group_memory,
            group_answer,
            is_mentioned,
            strip_mention,
        )

        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = (message.get("text") or message.get("caption") or "").strip()
        self._gruppe_merken(chat, "gesehen")
        if not chat_id or not text or text.startswith("/"):
            return
        sender_info = message.get("from") or {}
        sender = str(
            sender_info.get("first_name") or sender_info.get("username") or "Jemand"
        ).strip()
        memory = get_group_memory()
        memory.record(chat_id, sender, text, message_id=message.get("message_id"))
        username = await self.bot_username()
        if not username:
            self._fehler_merken(
                "Der eigene Bot-Name ist unbekannt (getMe antwortet nicht) - "
                "deshalb erkenne ich Erwaehnungen in Gruppen nicht."
            )
            return
        if not is_mentioned(text, message.get("entities"), username):
            return
        self._gruppe_merken(chat, "erwaehnt")
        question = strip_mention(text, username) or "Hallo!"
        await self._api("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        provider, model = self.modellwahl()
        cards: list[dict] = []
        try:
            answer = await asyncio.wait_for(
                group_answer(
                    "papa",
                    username,
                    sender,
                    question,
                    transcript=memory.transcript(chat_id),
                    group=True,
                    partner_hint="dein Sohn Emil alias Mini Jon mit eigenem Bot",
                    provider=provider,
                    model=model,
                    slot="jon",
                    scope="gast",
                    source="telegram-gruppe",
                    cards=cards,
                ),
                timeout=ZEITLIMIT,
            )
        except Exception:
            answer = FEHLER_ANTWORT
        memory.record(chat_id, "Jon", answer, bot="jon")
        await self.send(chat_id, answer)
        await self.send_cards(chat_id, cards)
        self._gruppe_merken(chat, "geantwortet")

    async def send(self, chat_id: str | int, text: str) -> None:
        from app.services.text_format import ohne_tabellen

        text = ohne_tabellen(text)
        for start in range(0, max(len(text), 1), 3900):
            await self._api(
                "sendMessage",
                {"chat_id": chat_id, "text": text[start : start + 3900]},
            )

    async def send_location(self, chat_id: str | int, punkt: dict) -> None:
        await self._api(
            "sendVenue",
            {
                "chat_id": chat_id,
                "latitude": punkt["lat"],
                "longitude": punkt["lon"],
                "title": punkt.get("titel") or "Ort",
                "address": punkt.get("label")
                or f"{punkt['lat']:.5f}, {punkt['lon']:.5f}",
            },
        )

    async def send_media(self, chat_id: str | int, werk: dict) -> bool:
        token = self._token()
        pfad = Path(str(werk.get("pfad") or ""))
        if not token or not pfad.is_file():
            return False
        video = str(werk.get("art")) == "video"
        methode = "sendVideo" if video else "sendPhoto"
        feld = "video" if video else "photo"
        beschriftung = str(werk.get("prompt") or "")[:900]
        try:
            daten = await asyncio.to_thread(pfad.read_bytes)
            async with httpx.AsyncClient(timeout=120) as client:
                antwort = await client.post(
                    f"https://api.telegram.org/bot{token}/{methode}",
                    data={"chat_id": str(chat_id), "caption": beschriftung},
                    files={feld: (pfad.name, daten)},
                )
            if antwort.status_code < 400:
                return True
            async with httpx.AsyncClient(timeout=120) as client:
                antwort = await client.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={"chat_id": str(chat_id), "caption": beschriftung},
                    files={"document": (pfad.name, daten)},
                )
            return antwort.status_code < 400
        except Exception:
            return False

    async def live_bild_senden(
        self, chat_id: str | int, daten: bytes, beschriftung: str = ""
    ) -> int:
        token = self._token()
        if not token:
            return 0
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                antwort = await client.post(
                    f"https://api.telegram.org/bot{token}/sendPhoto",
                    data={"chat_id": str(chat_id), "caption": beschriftung[:900]},
                    files={"photo": ("live.jpg", daten, "image/jpeg")},
                )
            if antwort.status_code >= 400:
                return 0
            ergebnis = (antwort.json() or {}).get("result") or {}
            return int(ergebnis.get("message_id") or 0)
        except Exception:
            return 0

    async def live_bild_ersetzen(
        self, chat_id: str | int, nachricht_id: int, daten: bytes
    ) -> bool:
        token = self._token()
        if not token or not nachricht_id:
            return False
        medium = json.dumps(
            {"type": "photo", "media": "attach://live"}, ensure_ascii=False
        )
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                antwort = await client.post(
                    f"https://api.telegram.org/bot{token}/editMessageMedia",
                    data={
                        "chat_id": str(chat_id),
                        "message_id": str(int(nachricht_id)),
                        "media": medium,
                    },
                    files={"live": ("live.jpg", daten, "image/jpeg")},
                )
            return antwort.status_code < 400
        except Exception:
            return False

    async def live_geraet(self, chat_id: str, ziel: str, welcher: str = "alle") -> bool:
        from app.services.verbund_service import VerbundFehler, get_verbund_service

        verbund = get_verbund_service()
        try:
            eintrag = verbund.finden(ziel)
        except VerbundFehler:
            return False
        try:
            daten = await verbund.bildschirm(eintrag["id"], welcher)
        except VerbundFehler as fehler:
            await self.send(chat_id, f"{eintrag['name']}: {fehler} 🙈")
            return True
        await self.live_bild_senden(
            chat_id,
            daten,
            f"🖥️ {eintrag['name']} — gerade eben. Nochmal: /live {ziel}",
        )
        return True

    async def live_starten(self, chat_id: str, welcher: str = "alle") -> None:
        from app.services.live_service import LiveFehler, get_live_service

        dienst = get_live_service()
        try:
            stand = await asyncio.to_thread(dienst.starten, welcher, 3.0)
            daten = await asyncio.to_thread(dienst.aktuell)
        except LiveFehler as fehler:
            await self.send(chat_id, f"Das geht hier nicht: {fehler} 🙈")
            return
        namen = [m["name"] for m in stand.get("monitore", []) if m["id"] != "alle"]
        wo = " + ".join(namen) if namen else "Bildschirm"
        nachricht_id = await self.live_bild_senden(
            chat_id,
            daten,
            f"🔴 Live von {self._rechnername()} — {wo}. Das Bild aktualisiert sich "
            "hier laufend. /livestop beendet die Uebertragung.",
        )
        if not nachricht_id:
            await self.send(chat_id, "Ich konnte das Bild nicht schicken. 😕")
            return
        dienst.telegram_ziel(chat_id, nachricht_id)
        adressen = self._live_adressen(welcher)
        if adressen:
            await self.send(
                chat_id,
                "Fluessiger im Browser (im selben WLAN):"
                + chr(10)
                + chr(10).join(adressen),
            )

    async def live_stoppen(self, chat_id: str) -> None:
        from app.services.live_service import get_live_service

        dienst = get_live_service()
        dienst.telegram_los(chat_id)
        if not dienst.telegram_ziele():
            dienst.stoppen()
        await self.send(chat_id, "Uebertragung beendet. ⏹️")

    async def _geraete_text(self) -> str:
        from app.services.verbund_service import get_verbund_service

        geraete = get_verbund_service().geraete()
        if not geraete:
            return (
                "Hier haengt noch kein zweites Geraet dran. Am PC unter "
                "Einstellungen → Geräte im Verbund koppelst du zum Beispiel deinen "
                "Raspberry Pi dazu. 🔗"
            )
        zeilen = ["Deine Jon-Geraete:"]
        for g in geraete:
            wo = g.get("weg") or "noch nicht erreicht"
            zeilen.append(f"• {g['name']} — {g.get('version') or '?'} ({wo})")
        zeilen.append("")
        zeilen.append("Bildschirm ansehen: /live <Name> — fragen: schreib mir einfach.")
        return chr(10).join(zeilen)

    def _rechnername(self) -> str:
        from app.services.handy_service import get_handy_service

        return get_handy_service().kennung().get("name", "diesem Rechner")

    def _live_adressen(self, welcher: str) -> list[str]:
        from app.core.auth import get_token
        from app.core.config import get_settings
        from app.core.auth import lan_adressen

        settings = get_settings()
        if not settings.jon_lan:
            return []
        marke = get_token()
        return [
            f"http://{host}:{settings.port}/live?welcher={welcher}&token={marke}"
            for host in lan_adressen()[:2]
        ]

    async def send_datei(self, chat_id: str | int, datei: dict) -> bool:
        token = self._token()
        pfad = Path(str(datei.get("path") or ""))
        if not token or not pfad.is_file():
            return False
        if pfad.stat().st_size > 48 * 1024 * 1024:
            await self.send(
                chat_id,
                f"{pfad.name} ist mit {datei.get('sizeText', '')} zu gross fuer Telegram. "
                f"Sie liegt hier: {pfad.parent}",
            )
            return True
        art = str(datei.get("kind") or "")
        methode = "sendPhoto" if art == "bild" else "sendDocument"
        feld = "photo" if art == "bild" else "document"
        titel = str(datei.get("title") or pfad.stem)
        beschriftung = f"{titel} — liegt in {pfad.parent}"[:900]
        try:
            daten = await asyncio.to_thread(pfad.read_bytes)
            async with httpx.AsyncClient(timeout=180) as client:
                antwort = await client.post(
                    f"https://api.telegram.org/bot{token}/{methode}",
                    data={"chat_id": str(chat_id), "caption": beschriftung},
                    files={feld: (pfad.name, daten)},
                )
            if antwort.status_code < 400:
                return True
            async with httpx.AsyncClient(timeout=180) as client:
                antwort = await client.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={"chat_id": str(chat_id), "caption": beschriftung},
                    files={"document": (pfad.name, daten)},
                )
            return antwort.status_code < 400
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")
            return False

    @staticmethod
    def _karten_dateien(cards: list[dict]) -> list[dict]:
        dateien: list[dict] = []
        gesehen: set[str] = set()
        for karte in cards or []:
            if not isinstance(karte, dict) or karte.get("kind") != "datei":
                continue
            for eintrag in (karte.get("data") or {}).get("dateien") or []:
                pfad = str((eintrag or {}).get("path") or "")
                if pfad and pfad not in gesehen:
                    gesehen.add(pfad)
                    dateien.append(eintrag)
        return dateien

    async def send_cards(self, chat_id: str | int, cards: list[dict]) -> None:
        from app.services.telegram_extras import (
            map_links,
            map_points,
            research_ids,
            spawn_research_watch,
            studio_files,
        )

        for datei in self._karten_dateien(cards)[:6]:
            if not await self.send_datei(chat_id, datei):
                await self.send(
                    chat_id,
                    f"{datei.get('name', 'Die Datei')} ist fertig, liess sich aber "
                    f"nicht senden. Sie liegt hier: {datei.get('folder', '')}",
                )
        for werk in studio_files(cards):
            if not await self.send_media(chat_id, werk):
                await self.send(
                    chat_id, "Das Bild ist fertig, ließ sich aber nicht senden."
                )
        for punkt in map_points(cards):
            await self.send_location(chat_id, punkt)
        for link in map_links(cards):
            await self.send(chat_id, f"🗺️ Route zum Mitnehmen: {link}")
        for task_id in research_ids(cards):
            spawn_research_watch(
                task_id,
                lambda text, ziel=chat_id: self.send(ziel, text),
                self._research_watch,
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
            atomic_write_bytes(src, mp3)
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
            atomic_write_bytes(src, audio)
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

    async def _handle_location(
        self, chat_id: str, lat: float, lon: float, live: bool = False
    ) -> None:
        from app.services.location_service import get_location_service

        service = get_location_service()
        await self._remember_position(lat, lon, live)
        pending = self._pending_place.pop(chat_id, None)
        if pending and not live:
            service.add_place(chat_id, pending, lat, lon)
            await self.send(
                chat_id,
                f"📍 Gemerkt! „{pending}“ ist jetzt gespeichert. Sag z. B. "
                f"„Erinnere mich an Milch, wenn ich beim {pending} bin“.",
            )
            return
        triggered = service.check(chat_id, lat, lon)
        for text in triggered:
            await self.send(chat_id, f"📍 Du bist da! Denk an: {text}")
        if not live and not triggered:
            await self.send(
                chat_id,
                "📍 Standort übernommen. „Route zum nächsten Supermarkt“ geht "
                "jetzt von hier aus.",
            )

    async def _remember_position(self, lat: float, lon: float, live: bool) -> None:
        from app.services.maps import get_maps_service

        service = get_maps_service()
        now = time.monotonic()
        if live and now - self._last_home < 120.0:
            return
        try:
            aktuell = await service.home()
            if service.distance(aktuell[0], aktuell[1], lat, lon) < 120.0:
                self._last_home = now
                return
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")
        try:
            await service.set_home(lat, lon, "handy")
            self._last_home = now
        except Exception as _fehler:
            leise(_fehler, "services/telegram_service")

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
            "Befehle direkt aus, statt nachzufragen. "
            "Unterwegs hast du auch Jon Maps und Jon Deep Learning dabei: Fuer "
            "Orte, Wege und Entfernungen nutze maps — action='umgebung' mit einem "
            "Filter wie supermarkt, apotheke oder tankstelle, action='route' mit "
            "from='hier' und einem Filter oder Ladennamen als Ziel "
            "(to='supermarkt', to='Interspar'). 'hier' ist der zuletzt per "
            "Telegram geteilte Handy-Standort; fehlt er, bitte um das Teilen des "
            "Standorts. Zu jeder Karte bekommt der Nutzer automatisch einen Pin "
            "aufs Handy. Soll Jon etwas lernen oder recherchieren, starte "
            "deep_learning mit action='start' — das laeuft am PC weiter, und das "
            "Ergebnis landet hier im Chat, sobald es fertig ist."
        )
        return {"role": "system", "content": system}

    @staticmethod
    def modellwahl() -> tuple[str, str]:
        from app.core.config import get_settings, lebendes_modell
        from app.services.chat_service import grundmodell

        provider, model = get_settings_service().telegram_selection()
        settings = get_settings()
        provider = provider or settings.default_provider
        model = model or grundmodell(provider) or settings.emil_model
        return provider, lebendes_modell(model, provider)

    async def _modell_stand(self) -> str:
        from app.providers.registry import get_registry
        from app.services.chat_service import ollama_geeignet

        provider, model = self.modellwahl()
        eigene = str(get_settings_service().get().get("telegram_provider") or "")
        zeilen = [
            f"🧠 Telegram nutzt gerade {provider} · {model}"
            + ("" if eigene else " (wie Jon)")
        ]
        try:
            ollama = get_registry().get("ollama")
            modelle = (
                [m for m in await ollama.list_models() if ollama_geeignet(m)]
                if ollama.available()
                else []
            )
        except Exception:
            modelle = []
        if modelle:
            zeilen.append("")
            zeilen.append("Ollama-Modelle auf diesem Geraet:")
            zeilen.extend(f"• {m}" for m in modelle[:OLLAMA_LISTE])
        zeilen.append("")
        zeilen.append(
            "Wechseln: /modell ollama · /modell ollama <Modell> · "
            "/modell nvidia <Modell> · /modell auto = wieder wie Jon"
        )
        return "\n".join(zeilen)

    async def _anbieter_stand(self) -> str:
        from app.providers.registry import get_registry

        provider, model = self.modellwahl()
        eigene = str(get_settings_service().get().get("telegram_provider") or "")
        zeilen = [
            f"🔌 Telegram nutzt gerade {provider} · {model}"
            + ("" if eigene else " (wie Jon)"),
            "",
            "Verfuegbare Anbieter:",
        ]
        for name, anbieter in get_registry().all().items():
            try:
                da = anbieter.available()
            except Exception:
                da = False
            if da:
                zeilen.append(f"• {name}" + (" ✓" if name == provider else ""))
        zeilen.append("")
        zeilen.append(
            "Wechseln: /anbieter ollama · /anbieter nvidia · "
            "/anbieter auto = wieder wie Jon · Modell waehlen: /modell"
        )
        return "\n".join(zeilen)

    async def _anbieter_befehl(self, text: str) -> str:
        teile = text.split()[1:]
        if not teile:
            return await self._anbieter_stand()
        return await self._modell_befehl("/modell " + teile[0])

    async def _modell_befehl(self, text: str) -> str:
        from app.providers.base import ProviderError
        from app.providers.registry import get_registry
        from app.services.chat_service import grundmodell, ollama_geeignet

        teile = text.split()[1:]
        if not teile:
            return await self._modell_stand()
        settings = get_settings_service()
        registry = get_registry()
        wunsch = teile[0].strip().lower()
        if wunsch in ("auto", "jon", "standard", "normal", "reset"):
            settings.update({"telegram_provider": "", "telegram_model": ""})
            provider, model = self.modellwahl()
            return f"✅ Telegram folgt wieder Jon: {provider} · {model}"
        if wunsch in registry.all():
            provider = wunsch
            suche = " ".join(teile[1:]).strip()
        else:
            provider = self.modellwahl()[0]
            suche = " ".join(teile).strip()
        try:
            anbieter = registry.get(provider)
        except ProviderError:
            return f"Den Anbieter {provider} kenne ich nicht."
        if not anbieter.available():
            if provider == "ollama":
                return (
                    "Ollama ist auf diesem Geraet nicht eingerichtet. Schalte es "
                    "am PC unter Einstellungen → Ollama ein oder verbinde einen "
                    "freigegebenen Ollama-Server."
                )
            return f"Fuer {provider} ist kein API-Schluessel hinterlegt."
        try:
            modelle = await anbieter.list_models()
        except Exception:
            modelle = []
        if provider == "ollama":
            modelle = [m for m in modelle if ollama_geeignet(m)]
            if not modelle:
                return (
                    "Ollama antwortet nicht oder hat noch kein Modell. Starte "
                    "Ollama und lade ein Modell, z. B. mit: ollama pull gemma3"
                )
        if suche:
            klein = suche.lower()
            model = next((m for m in modelle if m.lower() == klein), "")
            if not model:
                model = next(
                    (m for m in modelle if m.lower().startswith(klein)), ""
                )
            if not model:
                model = next((m for m in modelle if klein in m.lower()), "")
            if not model and not modelle:
                model = suche
            if not model:
                auswahl = ", ".join(modelle[:OLLAMA_LISTE])
                return (
                    f"Das Modell {suche} gibt es bei {provider} nicht. "
                    f"Zur Wahl: {auswahl}"
                )
        else:
            model = grundmodell(provider)
            if modelle and model not in modelle:
                model = modelle[0]
        settings.update({"telegram_provider": provider, "telegram_model": model})
        hinweis = (
            " Jon antwortet hier jetzt lokal ueber Ollama - auch wenn er am PC "
            "eine API benutzt."
            if provider == "ollama"
            else ""
        )
        return f"✅ Telegram nutzt jetzt {provider} · {model}.{hinweis}"

    async def _answer(self, chat_id: str, text: str) -> tuple[str, list[dict]]:
        from app.schemas import ChatIn, MessageIn
        from app.services.chat_service import ChatService

        if self._chat_service is None:
            self._chat_service = ChatService()
        history = self._histories.setdefault(chat_id, [])
        history.append({"role": "user", "content": text})
        del history[:-HISTORY_KEEP]
        self._save_histories()
        provider, model = self.modellwahl()
        messages = [self._system_message(), *history[-HISTORY_SEND:]]
        payload = ChatIn(
            messages=[MessageIn(**m) for m in messages],
            persist=False,
            tool_mode="allow",
            max_tokens=2048,
            provider=provider,
            model=model,
            slot="emil",
            source="telegram",
        )
        parts: list[str] = []
        done_summaries: list[str] = []
        running_summaries: dict[str, str] = {}
        cards: list[dict] = []
        announced = 0
        async for event in self._chat_service.stream(payload):
            kind = event.get("type")
            card = event.get("card")
            if isinstance(card, dict) and card not in cards:
                cards.append(card)
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
        return answer, cards

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
        cards: list[dict] = []
        try:
            answer, cards = await asyncio.wait_for(
                self._answer(chat_id, text), timeout=ZEITLIMIT
            )
        except asyncio.CancelledError:
            typing.cancel()
            return
        except asyncio.TimeoutError:
            answer = (
                "Das hat zu lange gedauert. Versuch es nochmal oder wechsle mit "
                "/modell auf ein schnelleres Modell, z. B. /modell ollama."
            )
        except Exception as exc:
            answer = f"Da ist etwas schiefgelaufen: {exc}"
        finally:
            typing.cancel()
        wants_voice = (voice or chat_id in self._voice_reply) and chat_id not in self._voice_off
        if wants_voice:
            await self.send_voice(chat_id, answer)
        await self.send(chat_id, answer)
        await self.send_cards(chat_id, cards)

    def _launch(self, chat_id: str, text: str, voice: bool = False) -> None:
        laufend = [t for t in self._running.get(chat_id, []) if not t.done()]
        vorher = laufend[-1] if laufend else None
        task = asyncio.create_task(
            self._der_reihe_nach(vorher, len(laufend), chat_id, text, voice)
        )
        laufend.append(task)
        self._running[chat_id] = laufend

    async def _der_reihe_nach(
        self,
        vorher: asyncio.Task | None,
        wartend: int,
        chat_id: str,
        text: str,
        voice: bool,
    ) -> None:
        if vorher is not None:
            if wartend == 1:
                await self.send(
                    chat_id,
                    "⏳ Ich beantworte noch deine vorige Nachricht, danach komme "
                    "ich direkt zu dieser.",
                )
            await asyncio.wait({vorher})
        await self._handle(chat_id, text, voice)

    async def _cancel_running(self, chat_id: str) -> bool:
        laufend = [t for t in self._running.pop(chat_id, []) if not t.done()]
        for task in laufend:
            task.cancel()
        return bool(laufend)

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
        except Exception as fehler:
            self._fehler_merken(f"Abruf fehlgeschlagen: {fehler}")
            await asyncio.sleep(10)
            return
        if not data.get("ok"):
            grund = str(data.get("description") or "unbekannter Fehler")
            self._fehler_merken(grund)
            if "webhook" in grund.lower() or int(data.get("error_code") or 0) == 409:
                await self._webhook_loesen()
                await asyncio.sleep(2)
                return
            await asyncio.sleep(30)
            return
        self._stand["letzte_abfrage"] = time.time()
        self._stand["letzter_fehler"] = ""
        self._stand["updates"] += len(data.get("result", []))
        for update in data.get("result", []):
            self._offset = max(self._offset, int(update["update_id"]) + 1)
            edited = update.get("edited_message") or {}
            message = update.get("message") or edited or {}
            chat_id = (message.get("chat") or {}).get("id")
            if not chat_id:
                continue
            from app.services.telegram_group_service import GROUP_CHAT_TYPES

            if str((message.get("chat") or {}).get("type") or "") in GROUP_CHAT_TYPES:
                if not edited:
                    await self._handle_group_message(message)
                continue
            location = message.get("location") or message.get("venue", {}).get(
                "location"
            )
            if location:
                await self._handle_location(
                    str(chat_id),
                    float(location.get("latitude")),
                    float(location.get("longitude")),
                    live=bool(edited),
                )
                continue
            text = (message.get("text") or "").strip()
            voice_msg = message.get("voice") or message.get("audio")
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
                    "Schick mir gerne auch eine Sprachnachricht. Teile mir deinen "
                    "Standort (📎 → Standort), dann plane ich Routen ab hier — zum "
                    "Beispiel: Route zum nächsten Supermarkt.\n\n"
                    "Befehle: /live = ich zeige dir meine Bildschirme live · "
                    "/live <Geraet> = Bildschirm eines anderen Jon (z.B. /live pi) · "
                    "/geraete = alle verbundenen Geraete · "
                    "/anbieter = KI-Anbieter anzeigen oder wechseln (z.B. "
                    "/anbieter ollama) · /modell = Modell anzeigen oder "
                    "wechseln (z.B. /modell ollama gemma3) · "
                    "/livestop = Uebertragung beenden · /stimme = "
                    "ich antworte per Sprachnachricht · /endstimme = nur noch Text · "
                    "/lernen <Thema> = Tiefenrecherche starten · /lernstatus = Stand "
                    "der Recherche · /lernstop = abbrechen · /lernweiter = "
                    "fortsetzen · /stopp = laufende Aktion abbrechen · /reset = "
                    "Gespräch vergessen.",
                )
                continue
            if text.split()[0].lower() in ("/modell", "/model", "/ki"):
                await self.send(chat_id, await self._modell_befehl(text))
                continue
            if text.split()[0].lower() in ("/anbieter", "/provider"):
                await self.send(chat_id, await self._anbieter_befehl(text))
                continue
            if text.startswith("/geraete") or text.startswith("/geräte"):
                await self.send(chat_id, await self._geraete_text())
                continue
            if text.startswith("/live"):
                if text.startswith("/livestop"):
                    await self.live_stoppen(str(chat_id))
                    continue
                teile = text.split(maxsplit=1)
                wunsch = teile[1].strip() if len(teile) > 1 else ""
                if wunsch and wunsch not in ("alle", "1", "2", "3", "4"):
                    if await self.live_geraet(str(chat_id), wunsch):
                        continue
                await self.live_starten(str(chat_id), wunsch or "alle")
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
            from app.services.telegram_extras import (
                is_learn_command,
                research_command,
                spawn_research_watch,
            )

            if is_learn_command(text):
                ergebnis = await research_command(text)
                if ergebnis is not None:
                    antwort, task_id = ergebnis
                    await self.send(chat_id, antwort)
                    if task_id:
                        spawn_research_watch(
                            task_id,
                            lambda nachricht, ziel=chat_id: self.send(
                                ziel, nachricht
                            ),
                            self._research_watch,
                        )
                    continue
            low = text.lower()
            place_trigger = None
            for phrase in (
                "ort speichern",
                "neuer ort",
                "merk dir diesen ort als",
                "ort merken",
                "speicher den ort",
                "das ist mein",
                "das ist der",
                "das ist die",
                "das ist das",
            ):
                if low.startswith(phrase):
                    place_trigger = text[len(phrase):].strip(" :.-") or ""
                    break
            if place_trigger is not None:
                name = place_trigger or "Ort"
                self._pending_place[str(chat_id)] = name
                await self.send(
                    chat_id,
                    f"Alles klar. Teile mir jetzt deinen Standort (📎 → Standort), "
                    f"dann merke ich mir ihn als „{name}“.",
                )
                continue
            from app.services.location_service import (
                get_location_service,
                parse_geo_reminder,
            )

            geo = parse_geo_reminder(text)
            if geo:
                what, where = geo
                missing = get_location_service().add_reminder(
                    str(chat_id), what, where
                )
                if missing:
                    await self.send(
                        chat_id,
                        f"Ich merke mir: „{what}“ bei „{where}“. Den Ort „{where}“ "
                        f"kenne ich aber noch nicht — schreib „Ort speichern: {where}“ "
                        "und teile mir dann dort deinen Standort, dann kann ich dich "
                        "wirklich erinnern, wenn du da bist.",
                    )
                else:
                    await self.send(
                        chat_id,
                        f"📍 Erledigt! Ich erinnere dich an „{what}“, sobald du bei "
                        f"„{where}“ bist. Teile dazu unterwegs deinen Live-Standort.",
                    )
                continue
            if is_voice and len(text) > 200:
                text = (
                    "Ich habe dir eine längere Sprachnachricht geschickt. Hier die "
                    "wörtliche Transkription:\n\n" + text + "\n\nFasse sie mir in "
                    "wenigen kurzen Stichpunkten zusammen. Trage außerdem alle darin "
                    "genannten Termine, Aufgaben und Erinnerungen mit calendar_add in "
                    "meinen Kalender ein (date versteht heute/morgen/Wochentag) und "
                    "sag mir am Ende kurz, was du eingetragen hast."
                )
            self._launch(str(chat_id), text, voice=is_voice)


_service: TelegramService | None = None


def get_telegram_service() -> TelegramService:
    global _service
    if _service is None:
        _service = TelegramService()
    return _service
