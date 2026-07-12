from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import socket
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.core.config import DATA_DIR
from app.db.database import session_scope
from app.db.models import P2PMessage
from app.services.settings_service import get_settings_service

DISCOVERY_PORT = 8757
CHAT_PORT = 8758
PEERS_FILE = DATA_DIR / "peers.json"
MEDIA_DIR = DATA_DIR / "p2p_media"
MAX_MEDIA = 60_000_000

VIDEO_MIMES = ("video/",)
IMAGE_MIMES = ("image/",)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class P2PService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._peers: dict[str, dict] = self._load()
        self._transport: asyncio.DatagramTransport | None = None
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if PEERS_FILE.exists():
            try:
                data = json.loads(PEERS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {}

    def _save(self) -> None:
        try:
            PEERS_FILE.write_text(
                json.dumps(self._peers, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def identity(self) -> dict:
        settings = get_settings_service()
        data = settings.get()
        user_id = str(data.get("p2p_user_id", "")).strip()
        if not user_id:
            user_id = uuid.uuid4().hex[:12]
            settings.update({"p2p_user_id": user_id})
        return {
            "id": user_id,
            "name": str(data.get("p2p_username", "")).strip(),
            "avatar": str(data.get("p2p_avatar", "🙂")) or "🙂",
            "enabled": bool(data.get("p2p_enabled", True)),
        }

    def set_profile(self, name: str, avatar: str = "") -> dict:
        values: dict = {"p2p_username": name.strip()[:32]}
        if avatar.strip():
            values["p2p_avatar"] = avatar.strip()[:4]
        get_settings_service().update(values)
        return self.identity()

    def _peer_by_name(self, name: str, only_fresh: bool = False) -> dict | None:
        wanted = name.strip().lower()
        if not wanted:
            return None
        now = datetime.now(timezone.utc)
        with self._lock:
            items = list(self._peers.items())
        for peer_id, peer in items:
            if str(peer.get("name", "")).strip().lower() != wanted:
                continue
            if only_fresh:
                try:
                    seen = datetime.fromisoformat(peer.get("last_seen", ""))
                except Exception:
                    continue
                if (now - seen).total_seconds() > 30:
                    continue
            return {"id": peer_id, **peer}
        return None

    def broadcast_targets(self) -> list[str]:
        targets = ["255.255.255.255"]
        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                parts = ip.split(".")
                if len(parts) == 4 and not ip.startswith("127."):
                    subnet = ".".join(parts[:3]) + ".255"
                    if subnet not in targets:
                        targets.append(subnet)
        except Exception:
            pass
        return targets

    def _broadcast(self, payload: dict) -> None:
        if self._transport is None:
            return
        packet = json.dumps(payload).encode()
        for target in self.broadcast_targets():
            try:
                self._transport.sendto(packet, (target, DISCOVERY_PORT))
            except Exception:
                continue

    def handle_packet(self, payload: dict, sender_ip: str) -> None:
        if payload.get("jon") != 1:
            return
        if payload.get("type") == "query":
            me = self.identity()
            wanted = str(payload.get("name", "")).strip().lower()
            if not me["enabled"] or not me["name"]:
                return
            if me["name"].lower() != wanted:
                return
            self._broadcast(
                {
                    "jon": 1,
                    "type": "announce",
                    "id": me["id"],
                    "name": me["name"],
                    "avatar": me["avatar"],
                }
            )
            return
        if not payload.get("id"):
            return
        self._remember_peer(
            str(payload["id"]),
            str(payload.get("name", "")),
            str(payload.get("avatar", "")),
            sender_ip,
        )

    def _query_name(self, name: str) -> None:
        self._broadcast(
            {"jon": 1, "type": "query", "name": name.strip().lower()}
        )

    async def resolve_name(
        self, name: str, timeout: float = 2.5, only_fresh: bool = False
    ) -> dict | None:
        found = self._peer_by_name(name, only_fresh)
        if found:
            return found
        self._query_name(name)
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.2)
            found = self._peer_by_name(name, only_fresh)
            if found:
                return found
        return None

    async def name_available(self, name: str) -> tuple[bool, str]:
        clean = name.strip()
        if len(clean) < 2:
            return False, "Der Name muss mindestens 2 Zeichen haben."
        me = self.identity()
        found = await self.resolve_name(clean, timeout=2.0, only_fresh=True)
        if found and found["id"] != me["id"]:
            return False, (
                f"Der Name „{clean}“ ist im Netzwerk schon vergeben. "
                "Wähle bitte einen anderen."
            )
        return True, ""

    async def set_profile_checked(self, name: str, avatar: str = "") -> dict:
        ok, reason = await self.name_available(name)
        if not ok:
            return {"error": reason}
        return self.set_profile(name, avatar)

    async def add_peer_by_name(self, name: str) -> dict:
        clean = name.strip()
        if not clean:
            return {"error": "Namen angeben"}
        me = self.identity()
        if clean.lower() == (me["name"] or "").lower():
            return {"error": "Das bist du selbst. 🙂"}
        found = await self.resolve_name(clean)
        if not found:
            return {
                "error": f"Niemand namens „{clean}“ gefunden. Läuft Jon dort und "
                "seid ihr im selben Netzwerk?"
            }
        return {"id": found["id"], "name": found.get("name"), "ip": found.get("ip")}

    def local_ip(self) -> str:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return str(probe.getsockname()[0])
        except Exception:
            return "127.0.0.1"
        finally:
            probe.close()

    def peers(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        result = []
        with self._lock:
            items = list(self._peers.items())
        for peer_id, peer in items:
            try:
                seen = datetime.fromisoformat(peer.get("last_seen", ""))
                online = (now - seen).total_seconds() < 25
            except Exception:
                online = False
            result.append(
                {
                    "id": peer_id,
                    "name": peer.get("name", "Unbekannt"),
                    "avatar": peer.get("avatar", "🙂"),
                    "ip": peer.get("ip", ""),
                    "online": online,
                    "last_seen": peer.get("last_seen", ""),
                    "unread": self.unread_count(peer_id),
                }
            )
        result.sort(key=lambda p: (not p["online"], p["name"].lower()))
        return result

    def _remember_peer(self, peer_id: str, name: str, avatar: str, ip: str) -> None:
        if peer_id == self.identity()["id"]:
            return
        with self._lock:
            peer = self._peers.setdefault(peer_id, {})
            peer.update(
                {
                    "name": name or peer.get("name", "Unbekannt"),
                    "avatar": avatar or peer.get("avatar", "🙂"),
                    "ip": ip or peer.get("ip", ""),
                    "last_seen": _now_iso(),
                }
            )
            self._save()

    def forget_peer(self, peer_id: str) -> bool:
        with self._lock:
            existed = self._peers.pop(peer_id, None) is not None
            if existed:
                self._save()
        with session_scope() as session:
            for row in (
                session.query(P2PMessage).filter(P2PMessage.peer_id == peer_id).all()
            ):
                if row.media_file:
                    (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
                session.delete(row)
        return existed

    async def add_peer_by_ip(self, ip: str) -> dict:
        ip = ip.strip()
        if not ip:
            return {"error": "IP-Adresse angeben"}
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                response = await client.get(f"http://{ip}:{CHAT_PORT}/ping")
                data = response.json()
        except Exception:
            return {
                "error": f"Unter {ip} antwortet kein Jon. Läuft Jon dort und seid "
                "ihr im selben WLAN?"
            }
        if not data.get("id"):
            return {"error": "Ungültige Antwort"}
        self._remember_peer(
            str(data["id"]), str(data.get("name", "")), str(data.get("avatar", "")), ip
        )
        return {"id": data["id"], "name": data.get("name"), "ip": ip}

    def _store(
        self,
        peer_id: str,
        direction: str,
        sender_name: str,
        text: str,
        media: dict | None,
    ) -> dict:
        media_file = None
        media_kind = None
        media_name = None
        media_mime = None
        if media and media.get("data"):
            raw = base64.b64decode(media["data"])
            if len(raw) > MAX_MEDIA:
                raise ValueError("Datei zu groß (max 60 MB)")
            media_mime = str(media.get("mime") or "application/octet-stream")
            media_name = str(media.get("name") or "datei")
            suffix = Path(media_name).suffix or (
                mimetypes.guess_extension(media_mime) or ""
            )
            media_file = f"{uuid.uuid4().hex}{suffix}"
            (MEDIA_DIR / media_file).write_bytes(raw)
            if media_mime.startswith(IMAGE_MIMES):
                media_kind = "image"
            elif media_mime.startswith(VIDEO_MIMES):
                media_kind = "video"
            else:
                media_kind = "file"
        with session_scope() as session:
            message = P2PMessage(
                peer_id=peer_id,
                direction=direction,
                sender_name=sender_name,
                text=text[:8000],
                media_file=media_file,
                media_kind=media_kind,
                media_name=media_name,
                media_mime=media_mime,
                seen=1 if direction == "out" else 0,
            )
            session.add(message)
            session.flush()
            return self._as_dict(message)

    @staticmethod
    def _as_dict(message: P2PMessage) -> dict:
        return {
            "id": message.id,
            "peer_id": message.peer_id,
            "direction": message.direction,
            "sender_name": message.sender_name,
            "text": message.text,
            "media_kind": message.media_kind,
            "media_name": message.media_name,
            "media_mime": message.media_mime,
            "has_media": bool(message.media_file),
            "created_at": message.created_at.isoformat(),
        }

    async def send(self, peer_id: str, text: str, media: dict | None = None) -> dict:
        with self._lock:
            peer = dict(self._peers.get(peer_id) or {})
        if not peer:
            return {"error": "Unbekannter Kontakt"}
        if not text.strip() and not (media and media.get("data")):
            return {"error": "Leere Nachricht"}
        me = self.identity()
        payload = {
            "from_id": me["id"],
            "from_name": me["name"] or "Jon-Nutzer",
            "from_avatar": me["avatar"],
            "text": text,
            "media": media or None,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"http://{peer.get('ip')}:{CHAT_PORT}/inbox", json=payload
                )
                if response.status_code != 200:
                    return {"error": f"Empfänger antwortete mit {response.status_code}"}
        except Exception:
            return {
                "error": f"{peer.get('name', 'Der Kontakt')} ist gerade nicht "
                "erreichbar (Jon muss dort laufen)."
            }
        try:
            return await asyncio.to_thread(
                self._store, peer_id, "out", me["name"], text, media
            )
        except ValueError as exc:
            return {"error": str(exc)}

    def receive(self, payload: dict, sender_ip: str) -> dict:
        peer_id = str(payload.get("from_id", "")).strip()
        if not peer_id:
            return {"error": "Absender fehlt"}
        self._remember_peer(
            peer_id,
            str(payload.get("from_name", "")),
            str(payload.get("from_avatar", "")),
            sender_ip,
        )
        media = payload.get("media") if isinstance(payload.get("media"), dict) else None
        message = self._store(
            peer_id,
            "in",
            str(payload.get("from_name", "")),
            str(payload.get("text", "")),
            media,
        )
        return {"ok": True, "id": message["id"]}

    def messages(self, peer_id: str, limit: int = 200) -> list[dict]:
        with session_scope() as session:
            rows = (
                session.query(P2PMessage)
                .filter(P2PMessage.peer_id == peer_id)
                .order_by(P2PMessage.created_at.asc())
                .limit(limit)
                .all()
            )
            return [self._as_dict(r) for r in rows]

    def mark_seen(self, peer_id: str) -> int:
        with session_scope() as session:
            rows = (
                session.query(P2PMessage)
                .filter(P2PMessage.peer_id == peer_id, P2PMessage.seen == 0)
                .all()
            )
            for row in rows:
                row.seen = 1
            return len(rows)

    def unread_count(self, peer_id: str = "") -> int:
        with session_scope() as session:
            query = session.query(P2PMessage).filter(P2PMessage.seen == 0)
            if peer_id:
                query = query.filter(P2PMessage.peer_id == peer_id)
            return query.count()

    def media_path(self, message_id: str) -> tuple[Path, str] | None:
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is None or not row.media_file:
                return None
            return (
                MEDIA_DIR / row.media_file,
                row.media_mime or "application/octet-stream",
            )

    async def announce_loop(self) -> None:
        while True:
            try:
                me = self.identity()
                if me["enabled"] and me["name"]:
                    self._broadcast(
                        {
                            "jon": 1,
                            "type": "announce",
                            "id": me["id"],
                            "name": me["name"],
                            "avatar": me["avatar"],
                        }
                    )
            except Exception:
                pass
            await asyncio.sleep(8)

    async def listen_loop(self) -> None:
        loop = asyncio.get_running_loop()
        service = self

        class Protocol(asyncio.DatagramProtocol):
            def connection_made(self, transport) -> None:
                service._transport = transport

            def datagram_received(self, data: bytes, addr) -> None:
                try:
                    payload = json.loads(data.decode("utf-8", errors="replace"))
                except Exception:
                    return
                service.handle_packet(payload, addr[0])

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            transport, _ = await loop.create_datagram_endpoint(Protocol, sock=sock)
        except Exception:
            sock.close()
            return
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            transport.close()
            self._transport = None


_service: P2PService | None = None


def get_p2p_service() -> P2PService:
    global _service
    if _service is None:
        _service = P2PService()
    return _service
