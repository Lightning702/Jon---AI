from __future__ import annotations

import asyncio
import json
import logging
import secrets
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta

from app.core.config import DATA_DIR

log = logging.getLogger("jon.phone")

CALLS_FILE = DATA_DIR / "phone_calls.json"
LOG_FILE = DATA_DIR / "phone_log.json"
KEEP_LOGS = 100
STATES = (
    "scheduled",
    "calling",
    "ringing",
    "active",
    "completed",
    "missed",
    "rejected",
    "failed",
    "cancelled",
)
WEEKDAYS = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}


def local_zone():
    from zoneinfo import ZoneInfo

    from app.services.settings_service import get_settings_service

    try:
        name = get_settings_service().get().get("phone_timezone", "")
    except Exception:
        name = ""
    for candidate in (name, "Europe/Vienna"):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except Exception:
            continue
    return datetime.now().astimezone().tzinfo


def now_local() -> datetime:
    return datetime.now(local_zone())


def parse_when(value: str, base: datetime | None = None) -> datetime:
    from zoneinfo import ZoneInfo

    text = str(value or "").strip()
    if not text:
        raise ValueError("Es fehlt die Zeitangabe fuer den Anruf.")
    base = base or now_local()
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=local_zone())
        return parsed
    except ValueError:
        pass
    lowered = text.lower()
    relative = _parse_relative(lowered, base)
    if relative:
        return relative
    absolute = _parse_absolute(lowered, base)
    if absolute:
        return absolute
    raise ValueError(
        f"Ich konnte '{value}' nicht als Zeitpunkt verstehen. Sag zum Beispiel "
        "'in 10 Minuten', 'heute um 18 Uhr' oder 'morgen um 9'."
    )


def _parse_relative(text: str, base: datetime) -> datetime | None:
    import re

    if text in ("jetzt", "sofort", "gleich"):
        return base + timedelta(seconds=5)
    words = {
        "einer": 1,
        "einem": 1,
        "eine": 1,
        "ein": 1,
        "zwei": 2,
        "drei": 3,
        "vier": 4,
        "fuenf": 5,
        "fünf": 5,
        "zehn": 10,
        "viertel": 15,
        "halben": 30,
        "halbe": 30,
    }
    match = re.search(
        r"in\s+(?:(\d+)|(" + "|".join(words) + r"))?\s*"
        r"(sekunde|sekunden|minute|minuten|min|stunde|stunden|std|tag|tagen)",
        text,
    )
    if not match:
        return None
    if match.group(1):
        amount = int(match.group(1))
    elif match.group(2):
        amount = words[match.group(2)]
    else:
        amount = 1
    unit = match.group(3)
    if unit.startswith("sekunde"):
        return base + timedelta(seconds=amount)
    if unit.startswith(("minute", "min")):
        return base + timedelta(minutes=amount)
    if unit.startswith(("stunde", "std")):
        return base + timedelta(hours=amount)
    return base + timedelta(days=amount)


def _parse_absolute(text: str, base: datetime) -> datetime | None:
    import re

    day = base.date()
    shifted = False
    if "übermorgen" in text or "uebermorgen" in text:
        day = day + timedelta(days=2)
        shifted = True
    elif "morgen" in text:
        day = day + timedelta(days=1)
        shifted = True
    elif "heute" in text:
        shifted = True
    else:
        for name, index in WEEKDAYS.items():
            if name in text:
                delta = (index - base.weekday()) % 7
                if delta == 0 or "nächsten" in text or "naechsten" in text:
                    delta = delta or 7
                day = day + timedelta(days=delta)
                shifted = True
                break
    date_match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})?", text)
    if date_match:
        year = int(date_match.group(3) or base.year)
        day = day.replace(
            year=year, month=int(date_match.group(2)), day=int(date_match.group(1))
        )
        shifted = True
    time_match = re.search(r"(\d{1,2})[:.](\d{2})", text)
    hour = minute = None
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
    else:
        hour_match = re.search(r"(?:um\s+)?(\d{1,2})\s*uhr", text)
        if hour_match:
            hour, minute = int(hour_match.group(1)), 0
    if hour is None:
        if not shifted:
            return None
        hour, minute = 9, 0
    if hour > 23 or minute > 59:
        raise ValueError(f"'{hour}:{minute:02d}' ist keine gueltige Uhrzeit.")
    result = datetime.combine(day, datetime.min.time()).replace(
        hour=hour, minute=minute, tzinfo=local_zone()
    )
    if result <= base and not shifted:
        result = result + timedelta(days=1)
    return result


def next_occurrence(rule: str, after: datetime) -> datetime | None:
    text = str(rule or "").strip().lower()
    if not text or text == "einmal":
        return None
    if text in ("täglich", "taeglich", "daily"):
        return after + timedelta(days=1)
    if text in ("wöchentlich", "woechentlich", "weekly"):
        return after + timedelta(days=7)
    for name, index in WEEKDAYS.items():
        if name in text:
            delta = (index - after.weekday()) % 7 or 7
            return after + timedelta(days=delta)
    if "werktag" in text:
        step = 1
        candidate = after + timedelta(days=step)
        while candidate.weekday() >= 5:
            candidate = candidate + timedelta(days=1)
        return candidate
    return None


def _port_holder(port: int) -> str:
    if sys.platform != "win32":
        return ""
    script = (
        f"$p = (Get-NetUDPEndpoint -LocalPort {port} -ErrorAction SilentlyContinue |"
        " Select-Object -First 1).OwningProcess; "
        "if ($p) { $pr = Get-Process -Id $p -ErrorAction SilentlyContinue; "
        "if ($pr) { \"$($pr.ProcessName) (PID $p)\" } }"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def firewall_command(port: int = 5060) -> str:
    inner = (
        "New-NetFirewallRule -DisplayName 'Jon Telefon (SIP)' "
        f"-Direction Inbound -Protocol UDP -LocalPort {port} -Action Allow "
        "-Profile Any; "
        "New-NetFirewallRule -DisplayName 'Jon Telefon (RTP)' "
        "-Direction Inbound -Protocol UDP -LocalPort 16384-32768 -Action Allow "
        "-Profile Any"
    )
    return (
        "Start-Process powershell -Verb RunAs -ArgumentList "
        f"'-NoProfile','-Command',\"{inner}\""
    )


class PhoneService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._calls: list[dict] = self._load(CALLS_FILE)
        self._logs: list[dict] = self._load(LOG_FILE)
        self._stack = None
        self._active = None
        self._status = "offline"
        self._error = ""
        self._starting = False

    def _load(self, path) -> list[dict]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                return []
        return []

    def _save(self, path, data) -> None:
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            log.warning("Telefondaten liessen sich nicht speichern: %s", exc)

    def settings(self) -> dict:
        from app.services.settings_service import get_settings_service

        return get_settings_service().get()

    def enabled(self) -> bool:
        return bool(self.settings().get("phone_enabled", False))

    def ensure_credentials(self) -> dict:
        from app.services.settings_service import get_settings_service

        service = get_settings_service()
        data = service.get()
        changed = {}
        if not data.get("phone_sip_user"):
            changed["phone_sip_user"] = "jon-phone"
        if not data.get("phone_sip_password"):
            changed["phone_sip_password"] = secrets.token_urlsafe(18)
        if changed:
            data = service.update(changed)
        return data

    async def start(self) -> None:
        if self._stack is not None or self._starting:
            return
        if not self.enabled():
            self._status = "disabled"
            return
        self._starting = True
        try:
            from app.services.phone.stack import SipStack

            data = self.ensure_credentials()
            stack = SipStack(
                username=data.get("phone_sip_user", "jon-phone"),
                password=data.get("phone_sip_password", ""),
                host=data.get("phone_bind_host", "0.0.0.0"),
                port=int(data.get("phone_sip_port", 5060) or 5060),
                realm=data.get("phone_sip_realm", "jon") or "jon",
                advertise=data.get("phone_advertise_host", ""),
            )
            stack.accept_incoming = bool(data.get("phone_accept_incoming", True))
            stack.on_incoming = self._handle_incoming
            await stack.start()
            self._stack = stack
            self._status = "waiting"
            self._error = ""
        except OSError as exc:
            port = self.settings().get("phone_sip_port", 5060)
            holder = _port_holder(int(port or 5060))
            self._error = (
                f"SIP-Port {port} ist belegt oder gesperrt: {exc}."
                + (
                    f" Er gehoert gerade {holder}. Meist ist das ein alter "
                    "Jon-Prozess, der nach dem Schliessen noch laeuft."
                    if holder
                    else ""
                )
            )
            self._status = "error"
        except Exception as exc:
            self._error = str(exc)
            self._status = "error"
        finally:
            self._starting = False

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.stop()
            self._stack = None
        self._status = "offline"

    async def restart(self) -> None:
        await self.stop()
        await self.start()

    def local_ip(self) -> str:
        from app.services.phone.netinfo import best_address

        if self._stack is not None:
            return self._stack.local_ip()
        return best_address(self.settings().get("phone_advertise_host", ""))

    def addresses(self) -> list[dict]:
        from app.services.phone.netinfo import describe, interfaces

        pinned = self.settings().get("phone_advertise_host", "")
        chosen = self.local_ip()
        items = [
            {
                "ip": "",
                "label": "Automatisch - passend zum Anrufer (WLAN oder Tailscale)",
                "kind": "auto",
                "usable": True,
                "selected": not pinned,
            }
        ]
        items.extend(
            {
                "ip": entry["ip"],
                "label": describe(entry),
                "kind": entry["kind"],
                "usable": entry["usable"],
                "selected": bool(pinned) and entry["ip"] == chosen,
            }
            for entry in interfaces()
            if entry["score"] > -100
        )
        return items

    def firewall_state(self) -> dict:
        if sys.platform != "win32":
            return {"ok": True, "detail": "nur unter Windows relevant"}
        port = int(self.settings().get("phone_sip_port", 5060) or 5060)
        script = (
            "$r = Get-NetFirewallRule -DisplayName 'Jon Telefon*' "
            "-ErrorAction SilentlyContinue; "
            "if ($r) { 'ja' } else { 'nein' }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            exists = result.stdout.decode("utf-8", "replace").strip() == "ja"
        except Exception:
            return {"ok": True, "detail": "liess sich nicht pruefen"}
        if exists:
            return {"ok": True, "detail": f"Regel fuer UDP {port} vorhanden"}
        return {
            "ok": False,
            "detail": (
                f"Keine Firewallregel fuer UDP {port}. Ohne sie blockt Windows die "
                "Anmeldung deines Handys stillschweigend."
            ),
            "fix": firewall_command(port),
            "fix_hint": (
                "In PowerShell einfuegen und Enter druecken. Windows fragt einmal "
                "nach Administratorrechten - das ist noetig, ein normales Fenster "
                "bekommt 'Zugriff verweigert'."
            ),
        }

    def status(self) -> dict:
        data = self.settings()
        binding = self._stack.binding if self._stack else None
        recognizer = self._recognizer_state()
        return {
            "enabled": bool(data.get("phone_enabled", False)),
            "running": self._stack is not None,
            "status": self._status,
            "error": self._error or (self._stack.last_error if self._stack else ""),
            "sip_user": data.get("phone_sip_user", ""),
            "sip_port": int(data.get("phone_sip_port", 5060) or 5060),
            "realm": data.get("phone_sip_realm", "jon"),
            "server": self.local_ip(),
            "timezone": data.get("phone_timezone", "Europe/Vienna"),
            "device": {
                "registered": binding is not None,
                "contact": str(binding.contact) if binding else "",
                "user_agent": binding.user_agent if binding else "",
                "source": f"{binding.source[0]}:{binding.source[1]}" if binding else "",
                "expires_in": int(binding.expires_at - time.time()) if binding else 0,
                "transport": binding.transport if binding else "",
            },
            "attempts": self._stack.attempts() if self._stack else [],
            "recognizer": recognizer,
            "ffmpeg": self._ffmpeg_state(),
            "active_call": self.active_call(),
            "scheduled": len([c for c in self._calls if c["status"] == "scheduled"]),
        }

    def _recognizer_state(self) -> dict:
        from app.services.phone.conversation import load_recognizer, recognizer_error

        ready = load_recognizer() is not None
        return {"ready": ready, "error": "" if ready else recognizer_error()}

    def _ffmpeg_state(self) -> dict:
        from app.services.phone.audio import have_ffmpeg

        ok = have_ffmpeg()
        return {
            "ready": ok,
            "error": "" if ok else "ffmpeg fehlt - Jon kann am Telefon nicht sprechen.",
        }

    def diagnostics(self) -> dict:
        status = self.status()
        firewall = self.firewall_state()
        addresses = self.addresses()
        chosen = next((a for a in addresses if a["selected"]), None)
        address_ok = bool(chosen and chosen["kind"] in ("lan", "mesh", "auto"))
        if chosen and chosen["kind"] == "vpn":
            address_detail = (
                f"Jon sagt {chosen['ip']} an - das ist ein VPN-Tunnel, den dein Handy "
                "im WLAN nicht erreicht. Waehle unten die WLAN-Adresse."
            )
        elif chosen and chosen["kind"] == "virtual":
            address_detail = (
                f"Jon sagt {chosen['ip']} an - das ist ein virtueller Adapter. "
                "Waehle unten die WLAN-Adresse."
            )
        elif chosen and chosen["kind"] == "auto":
            address_detail = (
                "Automatisch - Jon nennt jedem Anrufer die Adresse, ueber die er "
                f"ihn erreicht (im Heimnetz {self.local_ip()})."
            )
        elif chosen:
            address_detail = f"{chosen['ip']} - {chosen['label']}"
        else:
            address_detail = "Keine brauchbare Netzwerkadresse gefunden."
        checks = [
            {
                "name": "SIP-Dienst",
                "ok": status["running"],
                "detail": status["error"] or f"laeuft auf Port {status['sip_port']}",
            },
            {
                "name": "Serveradresse",
                "ok": address_ok,
                "detail": address_detail,
            },
            {
                "name": "Firewall",
                "ok": firewall["ok"],
                "detail": firewall["detail"],
                "fix": firewall.get("fix", ""),
            },
            {
                "name": "Telefon angemeldet",
                "ok": status["device"]["registered"],
                "detail": self._device_detail(status),
            },
            {
                "name": "Spracherkennung",
                "ok": status["recognizer"]["ready"],
                "detail": status["recognizer"]["error"] or "faster-whisper bereit",
            },
            {
                "name": "Sprachausgabe",
                "ok": status["ffmpeg"]["ready"],
                "detail": status["ffmpeg"]["error"] or "edge-tts und ffmpeg bereit",
            },
            {
                "name": "Sprachmodell",
                "ok": True,
                "detail": "nutzt Jons eingestellten Anbieter",
            },
            {
                "name": "Zeitplan",
                "ok": True,
                "detail": f"{status['scheduled']} Anrufe geplant",
            },
        ]
        mesh = [a for a in addresses if a["kind"] == "mesh"]
        checks.append(
            {
                "name": "Von unterwegs erreichbar",
                "ok": bool(mesh),
                "detail": (
                    f"ueber {mesh[0]['ip']} ({mesh[0]['label']})"
                    if mesh
                    else "Nur im Heimnetz. Fuer Mobilfunk Tailscale einrichten - "
                    "siehe docs/TELEFON.md."
                ),
            }
        )
        return {
            "ready": all(c["ok"] for c in checks if c["name"] != "Von unterwegs erreichbar"),
            "checks": checks,
            "addresses": addresses,
        }

    def _device_detail(self, status: dict) -> str:
        device = status["device"]
        if device["registered"]:
            return f"{device['contact']} ueber {device['transport'].upper()}"
        attempts = status.get("attempts") or []
        if not attempts:
            return (
                "Noch kein Versuch angekommen. Jon sieht dein Handy gar nicht - "
                "pruefe Netzwerk, Serveradresse und Firewall."
            )
        newest = attempts[0]
        return (
            f"Letzter Versuch von {newest['source']} ueber "
            f"{newest['transport'].upper()}: {newest['detail']}"
        )

    def active_call(self) -> dict | None:
        call = self._active
        if call is None:
            return None
        return {
            "id": call.get("id", ""),
            "status": call.get("status", ""),
            "reason": call.get("reason", ""),
            "started_at": call.get("started_at", ""),
            "duration": call.get("duration", 0),
        }

    def schedule(
        self,
        when: str,
        message: str = "",
        reason: str = "",
        recurrence: str = "",
        duration: int = 600,
    ) -> dict:
        moment = parse_when(when)
        if moment < now_local() - timedelta(minutes=1):
            raise ValueError(
                f"{moment.strftime('%d.%m.%Y %H:%M')} liegt in der Vergangenheit."
            )
        item = {
            "id": uuid.uuid4().hex[:12],
            "scheduled_at": moment.isoformat(),
            "timezone": str(moment.tzinfo),
            "reason": reason.strip(),
            "message": message.strip(),
            "status": "scheduled",
            "recurrence": recurrence.strip(),
            "duration": max(int(duration or 600), 30),
            "created_at": now_local().isoformat(timespec="seconds"),
            "started_at": "",
            "answered_at": "",
            "ended_at": "",
            "attempts": 0,
        }
        with self._lock:
            self._calls.append(item)
            self._save(CALLS_FILE, self._calls)
        return item

    def list(self, include_done: bool = False) -> list[dict]:
        with self._lock:
            items = list(self._calls)
        if not include_done:
            items = [c for c in items if c["status"] == "scheduled"]
        return sorted(items, key=lambda c: c["scheduled_at"])

    def get(self, call_id: str) -> dict | None:
        with self._lock:
            return next((dict(c) for c in self._calls if c["id"] == call_id), None)

    def find(self, hint: str) -> dict | None:
        text = str(hint or "").strip().lower()
        items = self.list()
        if not items:
            return None
        if not text:
            return items[0]
        for call in items:
            if call["id"].startswith(text):
                return call
        for call in items:
            haystack = f"{call['reason']} {call['message']}".lower()
            if text and text in haystack:
                return call
        for call in items:
            moment = datetime.fromisoformat(call["scheduled_at"])
            for pattern in (
                moment.strftime("%H:%M"),
                moment.strftime("%H"),
                moment.strftime("%d.%m."),
            ):
                if pattern and pattern in text:
                    return call
        return None

    def cancel(self, call_id: str) -> bool:
        with self._lock:
            for call in self._calls:
                if call["id"] == call_id and call["status"] == "scheduled":
                    call["status"] = "cancelled"
                    self._save(CALLS_FILE, self._calls)
                    return True
        return False

    def update(
        self,
        call_id: str,
        when: str = "",
        message: str = "",
        reason: str = "",
        recurrence: str = "",
    ) -> dict | None:
        with self._lock:
            call = next((c for c in self._calls if c["id"] == call_id), None)
            if call is None or call["status"] != "scheduled":
                return None
            if when:
                moment = parse_when(when)
                call["scheduled_at"] = moment.isoformat()
                call["timezone"] = str(moment.tzinfo)
            if message:
                call["message"] = message.strip()
            if reason:
                call["reason"] = reason.strip()
            if recurrence:
                call["recurrence"] = recurrence.strip()
            self._save(CALLS_FILE, self._calls)
            return dict(call)

    def due(self) -> list[dict]:
        now = now_local()
        ready: list[dict] = []
        with self._lock:
            for call in self._calls:
                if call["status"] != "scheduled":
                    continue
                try:
                    moment = datetime.fromisoformat(call["scheduled_at"])
                except ValueError:
                    continue
                if moment <= now:
                    ready.append(dict(call))
        return ready

    def _finish(self, call_id: str, status: str, reason: str, duration: float) -> None:
        with self._lock:
            call = next((c for c in self._calls if c["id"] == call_id), None)
            if call is None:
                return
            call["status"] = status
            call["reason"] = reason
            call["ended_at"] = now_local().isoformat(timespec="seconds")
            call["duration"] = int(duration)
            if status in ("completed", "missed", "rejected", "failed"):
                following = next_occurrence(
                    call.get("recurrence", ""),
                    datetime.fromisoformat(call["scheduled_at"]),
                )
                if following is not None:
                    self._calls.append(
                        {
                            **call,
                            "id": uuid.uuid4().hex[:12],
                            "scheduled_at": following.isoformat(),
                            "status": "scheduled",
                            "reason": call.get("reason", ""),
                            "started_at": "",
                            "answered_at": "",
                            "ended_at": "",
                            "duration": 0,
                            "attempts": 0,
                            "created_at": now_local().isoformat(timespec="seconds"),
                        }
                    )
            self._save(CALLS_FILE, self._calls)

    def record(self, entry: dict) -> None:
        with self._lock:
            self._logs.insert(0, entry)
            del self._logs[KEEP_LOGS:]
            self._save(LOG_FILE, self._logs)

    def history(self, limit: int = 25) -> list[dict]:
        with self._lock:
            return [dict(item) for item in self._logs[:limit]]

    def clear_history(self) -> None:
        with self._lock:
            self._logs = []
            self._save(LOG_FILE, self._logs)

    async def place_call(
        self,
        message: str = "",
        reason: str = "",
        call_id: str = "",
        duration: int = 600,
        test: bool = False,
    ) -> dict:
        from app.services.phone.conversation import PhoneConversation
        from app.services.voice_service import JON_VOICE

        if not self.enabled():
            raise RuntimeError(
                "Die Telefonfunktion ist ausgeschaltet. Du kannst sie in den "
                "Einstellungen unter Telefon einschalten."
            )
        if self._stack is None:
            await self.start()
        if self._stack is None:
            raise RuntimeError(self._error or "Der SIP-Dienst laeuft nicht.")
        if self._active is not None:
            raise RuntimeError("Es laeuft bereits ein Anruf.")
        data = self.settings()
        opening = message.strip() or _default_opening(reason, test)
        record = {
            "id": call_id or uuid.uuid4().hex[:12],
            "status": "calling",
            "reason": reason,
            "message": opening,
            "started_at": now_local().isoformat(timespec="seconds"),
            "duration": 0,
            "transcript": [],
        }
        self._active = record
        self._status = "calling"
        started = time.time()
        handle = None
        try:
            handle = await self._stack.call(display=data.get("phone_caller_name", "Jon"))
            record["status"] = handle.state
            if handle.state != "active":
                raise _CallEnded(handle.state, handle.reason)
            self._status = "active"
            record["status"] = "active"
            record["answered_at"] = now_local().isoformat(timespec="seconds")
            keep = bool(data.get("phone_keep_transcript", False))
            conversation = PhoneConversation(
                call=handle,
                opening=opening,
                persona=await _persona(reason, test),
                voice=data.get("phone_voice", "") or JON_VOICE,
                language=(data.get("language", "de") or "de")[:2],
                max_seconds=max(int(duration or 600), 30),
                on_turn=None,
            )
            transcript = await conversation.run()
            record["transcript"] = transcript if keep else []
            record["rtp_in"] = handle.rtp.packets_received
            record["rtp_out"] = handle.rtp.packets_sent
            record["status"] = "completed"
            heard = any(line["who"] == "user" for line in transcript)
            if handle.rtp.packets_received == 0:
                record["reason"] = (
                    "Bei Jon kam kein Ton an. Fast immer fehlt die Firewallregel "
                    "fuer UDP 16384-32768 - dann hoert Jon dich nicht, egal was du "
                    "sagst."
                )
            elif not heard:
                record["reason"] = (
                    "Ton kam an, aber es wurde nichts verstanden. Sprich etwas "
                    "lauter oder pruefe das Mikrofon am Handy."
                )
            else:
                record["reason"] = "Gespraech beendet"
        except _CallEnded as ended:
            record["status"] = ended.state
            record["reason"] = ended.reason
        except Exception as exc:
            record["status"] = "failed"
            record["reason"] = str(exc)
            log.exception("Anruf fehlgeschlagen")
        finally:
            if handle is not None:
                try:
                    await handle.hangup(record.get("reason", ""))
                except Exception:
                    pass
            record["duration"] = int(time.time() - started)
            record["ended_at"] = now_local().isoformat(timespec="seconds")
            self._active = None
            self._status = "waiting" if self._stack else "offline"
            self.record(dict(record))
            if call_id:
                self._finish(
                    call_id, record["status"], record["reason"], record["duration"]
                )
        return record

    async def _handle_incoming(self, call) -> None:
        from app.services.phone.conversation import PhoneConversation
        from app.services.voice_service import JON_VOICE

        if self._active is not None:
            await call.hangup("Es laeuft bereits ein Anruf")
            return
        data = self.settings()
        greeting = data.get("phone_greeting", "") or "Hey Felix! Was gibt es?"
        record = {
            "id": uuid.uuid4().hex[:12],
            "status": "active",
            "direction": "in",
            "reason": "",
            "message": greeting,
            "started_at": now_local().isoformat(timespec="seconds"),
            "answered_at": now_local().isoformat(timespec="seconds"),
            "duration": 0,
            "transcript": [],
        }
        self._active = record
        self._status = "active"
        started = time.time()
        try:
            conversation = PhoneConversation(
                call=call,
                opening=greeting,
                persona=await _persona("", False),
                voice=data.get("phone_voice", "") or JON_VOICE,
                language=(data.get("language", "de") or "de")[:2],
                max_seconds=max(int(data.get("phone_max_seconds", 600) or 600), 30),
            )
            transcript = await conversation.run()
            record["transcript"] = (
                transcript if data.get("phone_keep_transcript", False) else []
            )
            record["rtp_in"] = call.rtp.packets_received
            record["rtp_out"] = call.rtp.packets_sent
            record["status"] = "completed"
            record["reason"] = (
                "Bei Jon kam kein Ton an. Fehlt die Firewallregel fuer UDP "
                "16384-32768?"
                if call.rtp.packets_received == 0
                else "Gespraech beendet"
            )
        except Exception as exc:
            record["status"] = "failed"
            record["reason"] = str(exc)
            log.exception("Eingehender Anruf fehlgeschlagen")
        finally:
            record["duration"] = int(time.time() - started)
            record["ended_at"] = now_local().isoformat(timespec="seconds")
            self._active = None
            self._status = "waiting" if self._stack else "offline"
            self.record(dict(record))

    async def run_due(self) -> None:
        if not self.enabled():
            return
        for call in self.due():
            if self._active is not None:
                return
            with self._lock:
                stored = next((c for c in self._calls if c["id"] == call["id"]), None)
                if stored is None or stored["status"] != "scheduled":
                    continue
                stored["status"] = "calling"
                stored["started_at"] = now_local().isoformat(timespec="seconds")
                stored["attempts"] = int(stored.get("attempts", 0)) + 1
                self._save(CALLS_FILE, self._calls)
            await self.place_call(
                message=call.get("message", ""),
                reason=call.get("reason", ""),
                call_id=call["id"],
                duration=int(call.get("duration", 600)),
            )


class _CallEnded(Exception):
    def __init__(self, state: str, reason: str) -> None:
        super().__init__(reason or state)
        self.state = state if state in STATES else "failed"
        self.reason = reason or _state_text(state)


def _state_text(state: str) -> str:
    return {
        "missed": "Es wurde nicht abgenommen",
        "rejected": "Der Anruf wurde abgelehnt",
        "failed": "Der Anruf ist fehlgeschlagen",
    }.get(state, state)


def _default_opening(reason: str, test: bool) -> str:
    if test:
        return (
            "Hey Felix! Das ist ein Testanruf von Jon. "
            "Deine Telefonfunktion funktioniert."
        )
    if reason:
        return f"Hey Felix! Jon hier. Ich wollte dich an {reason} erinnern."
    return "Hey Felix! Jon hier. Ich wollte kurz mit dir sprechen."


async def _persona(reason: str, test: bool) -> str:
    from app.services.persona_service import get_persona_service

    base = ""
    try:
        base = get_persona_service().persona_block()
    except Exception:
        base = ""
    lines = [
        base.strip(),
        "Du telefonierst gerade mit Felix. Das ist ein echtes Telefongespraech.",
        "Antworte kurz und gesprochen, hoechstens zwei bis drei Saetze.",
        "Keine Aufzaehlungen, keine Sternchen, kein Markdown, keine Codebloecke.",
        "Keine Emojis und keine Erklaerungen zur Bedienung.",
        "Sprich wie am Telefon: natuerlich, direkt, freundlich.",
        "Wenn Felix sich verabschiedet, verabschiede dich ebenfalls kurz.",
    ]
    if reason:
        lines.append(f"Der Grund fuer den Anruf ist: {reason}.")
    if test:
        lines.append("Es ist ein Testanruf. Halte ihn sehr kurz.")
    return "\n".join(line for line in lines if line)


_service: PhoneService | None = None


def get_phone_service() -> PhoneService:
    global _service
    if _service is None:
        _service = PhoneService()
    return _service
