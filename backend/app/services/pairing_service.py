from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import uuid
from datetime import datetime

from app.core.config import DATA_DIR

DEVICES_FILE = DATA_DIR / "paired_devices.json"
REQUEST_TTL = 300
MAX_ATTEMPTS = 5


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PairingService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, dict] = {}
        self._devices: list[dict] = []
        try:
            self._devices = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
        except Exception:
            self._devices = []

    def _save(self) -> None:
        try:
            DEVICES_FILE.write_text(
                json.dumps(self._devices, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _prune(self) -> None:
        cutoff = time.time() - REQUEST_TTL
        for rid in [r for r, v in self._requests.items() if v["created"] < cutoff]:
            del self._requests[rid]

    def request(self, name: str) -> str:
        with self._lock:
            self._prune()
            request_id = secrets.token_hex(16)
            self._requests[request_id] = {
                "name": (name or "").strip()[:40] or "Geraet",
                "code": f"{secrets.randbelow(1_000_000):06d}",
                "created": time.time(),
                "attempts": 0,
            }
            return request_id

    def pending(self) -> list[dict]:
        with self._lock:
            self._prune()
            return [
                {"request_id": rid, "name": req["name"], "code": req["code"]}
                for rid, req in sorted(
                    self._requests.items(), key=lambda kv: kv[1]["created"]
                )
            ]

    def deny(self, request_id: str) -> bool:
        with self._lock:
            return self._requests.pop(request_id, None) is not None

    def claim(self, request_id: str, code: str) -> dict:
        with self._lock:
            self._prune()
            req = self._requests.get(request_id)
            if req is None:
                return {"error": "Anfrage abgelaufen - bitte neu starten"}
            req["attempts"] += 1
            if req["attempts"] > MAX_ATTEMPTS:
                del self._requests[request_id]
                return {"error": "Zu viele Versuche - bitte neu starten"}
            if code.strip() != req["code"]:
                return {"error": "Falscher Code"}
            token = secrets.token_hex(32)
            self._devices.append(
                {
                    "id": uuid.uuid4().hex,
                    "name": req["name"],
                    "token_hash": _hash(token),
                    "paired_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            self._save()
            del self._requests[request_id]
            return {"token": token}

    def verify(self, token: str) -> bool:
        if not token:
            return False
        digest = _hash(token)
        with self._lock:
            return any(d.get("token_hash") == digest for d in self._devices)

    def devices(self) -> list[dict]:
        with self._lock:
            return [
                {"id": d["id"], "name": d["name"], "paired_at": d.get("paired_at", "")}
                for d in self._devices
            ]

    def remove(self, device_id: str) -> bool:
        with self._lock:
            before = len(self._devices)
            self._devices = [d for d in self._devices if d["id"] != device_id]
            if len(self._devices) != before:
                self._save()
                return True
            return False


_service: PairingService | None = None


def get_pairing_service() -> PairingService:
    global _service
    if _service is None:
        _service = PairingService()
    return _service
