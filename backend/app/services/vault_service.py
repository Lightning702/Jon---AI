from __future__ import annotations

import base64
import json
import secrets
import string
import threading
import time

from app.core.config import DATA_DIR
from app.core.store import atomic_write_bytes

VAULT_FILE = DATA_DIR / "vault.dat"
LOCK_AFTER = 900.0
FORMAT = "jon-tresor-2"
AAD = FORMAT.encode("ascii")


def _alter_schluessel(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _alt_oeffnen(raw: bytes, password: str) -> list | None:
    from cryptography.fernet import Fernet, InvalidToken

    try:
        salt_b64, blob = raw.split(b"\n", 1)
        fernet = Fernet(_alter_schluessel(password, base64.b64decode(salt_b64)))
        return json.loads(fernet.decrypt(blob).decode("utf-8"))
    except (InvalidToken, ValueError, TypeError):
        return None


class VaultService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._schluessel: bytes | None = None
        self._salz = b""
        self._entries: list[dict] = []
        self._unlocked_at = 0.0

    def exists(self) -> bool:
        return VAULT_FILE.exists()

    def status(self) -> dict:
        with self._lock:
            self._auto_lock()
            return {
                "exists": self.exists(),
                "unlocked": self._schluessel is not None,
                "verfahren": "AES-256-GCM, Argon2id",
            }

    def _auto_lock(self) -> None:
        if self._schluessel and time.time() - self._unlocked_at > LOCK_AFTER:
            self._schluessel = None
            self._entries = []

    def _write(self) -> None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        from app.core.krypto import ARGON_PARALLEL, ARGON_SPEICHER, ARGON_ZEIT, zufall

        assert self._schluessel is not None
        nonce = zufall(12)
        chiffre = AESGCM(self._schluessel).encrypt(
            nonce, json.dumps(self._entries, ensure_ascii=False).encode("utf-8"), AAD
        )
        inhalt = {
            "format": FORMAT,
            "kdf": "argon2id",
            "t": ARGON_ZEIT,
            "m": ARGON_SPEICHER,
            "p": ARGON_PARALLEL,
            "salz": base64.b64encode(self._salz).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "daten": base64.b64encode(chiffre).decode("ascii"),
        }
        atomic_write_bytes(VAULT_FILE, json.dumps(inhalt).encode("utf-8"))

    def _neuer_schluessel(self, password: str) -> None:
        from app.core.krypto import schluessel_aus_passwort, zufall

        self._salz = zufall(16)
        self._schluessel = schluessel_aus_passwort(password, self._salz)

    def create(self, password: str) -> dict:
        if len(password) < 4:
            return {"error": "Das Master-Passwort ist zu kurz (mindestens 4 Zeichen)."}
        with self._lock:
            if self.exists():
                return {"error": "Es gibt bereits einen Tresor."}
            self._neuer_schluessel(password)
            self._entries = []
            self._unlocked_at = time.time()
            self._write()
            return {"ok": True}

    def _oeffnen(self, raw: bytes, password: str) -> tuple[list, bytes, bytes] | None:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        from app.core.krypto import schluessel_aus_passwort

        try:
            inhalt = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None
        if not isinstance(inhalt, dict) or inhalt.get("format") != FORMAT:
            return None
        try:
            salz = base64.b64decode(inhalt["salz"])
            schluessel = schluessel_aus_passwort(password, salz)
            klartext = AESGCM(schluessel).decrypt(
                base64.b64decode(inhalt["nonce"]), base64.b64decode(inhalt["daten"]), AAD
            )
            return json.loads(klartext.decode("utf-8")), schluessel, salz
        except (InvalidTag, KeyError, ValueError):
            return None

    def unlock(self, password: str) -> dict:
        with self._lock:
            if not self.exists():
                return {"error": "Es gibt noch keinen Tresor. Lege zuerst ein Master-Passwort fest."}
            raw = VAULT_FILE.read_bytes()
            geoeffnet = self._oeffnen(raw, password)
            if geoeffnet is not None:
                daten, self._schluessel, self._salz = geoeffnet
            else:
                daten = _alt_oeffnen(raw, password)
                if daten is None:
                    return {"error": "Falsches Master-Passwort."}
                self._neuer_schluessel(password)
                self._entries = daten if isinstance(daten, list) else []
                self._write()
            self._entries = daten if isinstance(daten, list) else []
            self._unlocked_at = time.time()
            return {"ok": True}

    def lock(self) -> dict:
        with self._lock:
            self._schluessel = None
            self._entries = []
            return {"ok": True}

    def _offen(self) -> bool:
        self._auto_lock()
        return self._schluessel is not None

    def list(self) -> dict:
        with self._lock:
            if not self._offen():
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
            if not self._offen():
                return {"error": "Der Tresor ist gesperrt."}
            self._unlocked_at = time.time()
            entry = next((e for e in self._entries if e["id"] == entry_id), None)
            if entry is None:
                return {"error": "Eintrag nicht gefunden."}
            return {"secret": entry.get("secret", ""), "username": entry.get("username", "")}

    def add(self, title: str, username: str, secret: str) -> dict:
        import uuid

        with self._lock:
            if not self._offen():
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
            self._write()
            return {"id": entry["id"], "title": entry["title"], "username": entry["username"]}

    def delete(self, entry_id: str) -> dict:
        with self._lock:
            if not self._offen():
                return {"error": "Der Tresor ist gesperrt."}
            before = len(self._entries)
            self._entries = [e for e in self._entries if e["id"] != entry_id]
            if len(self._entries) != before:
                self._unlocked_at = time.time()
                self._write()
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
