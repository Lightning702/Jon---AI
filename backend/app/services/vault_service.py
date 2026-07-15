from __future__ import annotations

import base64
import json
import os
import secrets
import string
import threading
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import DATA_DIR

VAULT_FILE = DATA_DIR / "vault.dat"
LOCK_AFTER = 900.0


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


class VaultService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fernet: Fernet | None = None
        self._entries: list[dict] = []
        self._unlocked_at = 0.0

    def exists(self) -> bool:
        return VAULT_FILE.exists()

    def status(self) -> dict:
        with self._lock:
            self._auto_lock()
            return {"exists": self.exists(), "unlocked": self._fernet is not None}

    def _auto_lock(self) -> None:
        if self._fernet and time.time() - self._unlocked_at > LOCK_AFTER:
            self._fernet = None
            self._entries = []

    def _write(self, salt: bytes) -> None:
        blob = self._fernet.encrypt(
            json.dumps(self._entries, ensure_ascii=False).encode("utf-8")
        )
        VAULT_FILE.write_bytes(base64.b64encode(salt) + b"\n" + blob)

    def create(self, password: str) -> dict:
        if len(password) < 4:
            return {"error": "Das Master-Passwort ist zu kurz (mindestens 4 Zeichen)."}
        with self._lock:
            if self.exists():
                return {"error": "Es gibt bereits einen Tresor."}
            salt = os.urandom(16)
            self._fernet = Fernet(_derive_key(password, salt))
            self._entries = []
            self._unlocked_at = time.time()
            self._write(salt)
            return {"ok": True}

    def unlock(self, password: str) -> dict:
        with self._lock:
            if not self.exists():
                return {"error": "Es gibt noch keinen Tresor. Lege zuerst ein Master-Passwort fest."}
            try:
                raw = VAULT_FILE.read_bytes()
                salt_b64, blob = raw.split(b"\n", 1)
                salt = base64.b64decode(salt_b64)
                fernet = Fernet(_derive_key(password, salt))
                data = json.loads(fernet.decrypt(blob).decode("utf-8"))
            except (InvalidToken, Exception):
                return {"error": "Falsches Master-Passwort."}
            self._fernet = fernet
            self._entries = data if isinstance(data, list) else []
            self._unlocked_at = time.time()
            return {"ok": True}

    def lock(self) -> dict:
        with self._lock:
            self._fernet = None
            self._entries = []
            return {"ok": True}

    def _require(self) -> bytes | None:
        self._auto_lock()
        if self._fernet is None:
            return None
        raw = VAULT_FILE.read_bytes()
        salt_b64, _ = raw.split(b"\n", 1)
        return base64.b64decode(salt_b64)

    def list(self) -> dict:
        with self._lock:
            salt = self._require()
            if salt is None:
                return {"locked": True, "entries": []}
            self._unlocked_at = time.time()
            return {
                "locked": False,
                "entries": [
                    {"id": e["id"], "title": e["title"], "username": e.get("username", "")}
                    for e in self._entries
                ],
            }

    def reveal(self, entry_id: str) -> dict:
        with self._lock:
            if self._require() is None:
                return {"error": "Der Tresor ist gesperrt."}
            self._unlocked_at = time.time()
            entry = next((e for e in self._entries if e["id"] == entry_id), None)
            if entry is None:
                return {"error": "Eintrag nicht gefunden."}
            return {"secret": entry.get("secret", ""), "username": entry.get("username", "")}

    def add(self, title: str, username: str, secret: str) -> dict:
        import uuid

        with self._lock:
            salt = self._require()
            if salt is None:
                return {"error": "Der Tresor ist gesperrt."}
            if not title.strip() or not secret:
                return {"error": "Titel und Passwort dürfen nicht leer sein."}
            entry = {
                "id": uuid.uuid4().hex,
                "title": title.strip()[:80],
                "username": username.strip()[:120],
                "secret": secret,
            }
            self._entries.append(entry)
            self._unlocked_at = time.time()
            self._write(salt)
            return {"id": entry["id"], "title": entry["title"], "username": entry["username"]}

    def delete(self, entry_id: str) -> dict:
        with self._lock:
            salt = self._require()
            if salt is None:
                return {"error": "Der Tresor ist gesperrt."}
            before = len(self._entries)
            self._entries = [e for e in self._entries if e["id"] != entry_id]
            if len(self._entries) != before:
                self._unlocked_at = time.time()
                self._write(salt)
            return {"ok": True}

    def generate(self, length: int = 20, symbols: bool = True) -> str:
        length = max(6, min(int(length or 20), 128))
        alphabet = string.ascii_letters + string.digits
        if symbols:
            alphabet += "!@#$%^&*-_=+?"
        return "".join(secrets.choice(alphabet) for _ in range(length))


_service: VaultService | None = None


def get_vault_service() -> VaultService:
    global _service
    if _service is None:
        _service = VaultService()
    return _service
