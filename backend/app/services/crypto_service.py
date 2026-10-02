from __future__ import annotations

import base64
import json
import os
import threading

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import DATA_DIR
from app.core.fehler import leise

KEY_FILE = DATA_DIR / "chat_key.bin"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.b64decode(value)


class CryptoService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._private = self._load()
        self._shared: dict[str, bytes] = {}

    def _load(self) -> X25519PrivateKey:
        from app.core.krypto import bytes_lesen, bytes_schreiben

        if KEY_FILE.exists():
            roh = bytes_lesen(KEY_FILE, "chat-schluessel")
            if roh is not None and len(roh) == 32:
                try:
                    private = X25519PrivateKey.from_private_bytes(roh)
                    if KEY_FILE.read_bytes() == roh:
                        bytes_schreiben(KEY_FILE, roh, "chat-schluessel")
                    return private
                except Exception as _fehler:
                    leise(_fehler, "services/crypto_service")
        private = X25519PrivateKey.generate()
        raw = private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        bytes_schreiben(KEY_FILE, raw, "chat-schluessel")
        return private

    def public_key(self) -> str:
        raw = self._private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return _b64(raw)

    def _session_key(self, peer_public: str) -> bytes:
        with self._lock:
            cached = self._shared.get(peer_public)
            if cached:
                return cached
        peer = X25519PublicKey.from_public_bytes(_unb64(peer_public))
        shared = self._private.exchange(peer)
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"jon-chat-v1",
        ).derive(shared)
        with self._lock:
            self._shared[peer_public] = key
        return key

    def encrypt(self, payload: dict, peer_public: str) -> dict:
        key = self._session_key(peer_public)
        nonce = os.urandom(12)
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sealed = AESGCM(key).encrypt(nonce, raw, None)
        return {"nonce": _b64(nonce), "data": _b64(sealed)}

    def decrypt(self, envelope: dict, peer_public: str) -> dict:
        key = self._session_key(peer_public)
        raw = AESGCM(key).decrypt(
            _unb64(str(envelope["nonce"])), _unb64(str(envelope["data"])), None
        )
        return json.loads(raw.decode("utf-8"))


_service: CryptoService | None = None


def get_crypto_service() -> CryptoService:
    global _service
    if _service is None:
        _service = CryptoService()
    return _service
