from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.core.config import DATA_DIR
from app.db.database import session_scope
from app.db.models import P2PMessage
from app.services.crypto_service import get_crypto_service
from app.services.settings_service import get_settings_service

DISCOVERY_PORT = int(os.environ.get("JON_DISCOVERY_PORT", "8757"))
CHAT_PORT = int(os.environ.get("JON_CHAT_PORT", "8758"))
PEERS_FILE = DATA_DIR / "peers.json"
GROUPS_FILE = DATA_DIR / "groups.json"
MEDIA_DIR = DATA_DIR / "p2p_media"
MAX_MEDIA = 60_000_000
RELAY_MAX_MEDIA = 4_000_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class P2PService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        data = self._load()
        self._peers: dict[str, dict] = data.get("peers", {})
        self._requests: dict[str, dict] = data.get("requests", {})
        self._blocked: list[str] = data.get("blocked", [])
        self._groups: dict[str, dict] = self._load_groups()
        self._transport: asyncio.DatagramTransport | None = None
        self._typing: dict[str, float] = {}
        self._notified: dict[str, set[str]] = {}
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if PEERS_FILE.exists():
            try:
                raw = json.loads(PEERS_FILE.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and "peers" in raw:
                    return raw
                if isinstance(raw, dict):
                    return {"peers": raw, "requests": {}, "blocked": []}
            except Exception:
                pass
        return {"peers": {}, "requests": {}, "blocked": []}

    def _save(self) -> None:
        try:
            PEERS_FILE.write_text(
                json.dumps(
                    {
                        "peers": self._peers,
                        "requests": self._requests,
                        "blocked": self._blocked,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load_groups(self) -> dict:
        if GROUPS_FILE.exists():
            try:
                data = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {}

    def _save_groups(self) -> None:
        try:
            GROUPS_FILE.write_text(
                json.dumps(self._groups, ensure_ascii=False, indent=2),
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
            "public_key": get_crypto_service().public_key(),
            "code": user_id,
        }

    def set_profile(self, name: str, avatar: str = "") -> dict:
        values: dict = {"p2p_username": name.strip()[:32]}
        if avatar.strip():
            values["p2p_avatar"] = avatar.strip()[:4]
        get_settings_service().update(values)
        return self.identity()

    def local_ip(self) -> str:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return str(probe.getsockname()[0])
        except Exception:
            return "127.0.0.1"
        finally:
            probe.close()

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

    @staticmethod
    def _peer_port(peer: dict) -> int:
        try:
            return int(peer.get("port") or CHAT_PORT)
        except Exception:
            return CHAT_PORT

    def _remember_peer(
        self,
        peer_id: str,
        name: str,
        avatar: str,
        ip: str,
        port: int = 0,
        public_key: str = "",
    ) -> None:
        if peer_id == self.identity()["id"] or peer_id in self._blocked:
            return
        with self._lock:
            if peer_id not in self._peers:
                return
            peer = self._peers[peer_id]
            peer.update(
                {
                    "name": name or peer.get("name", "Unbekannt"),
                    "avatar": avatar or peer.get("avatar", "🙂"),
                    "ip": ip or peer.get("ip", ""),
                    "port": port or peer.get("port") or CHAT_PORT,
                    "public_key": public_key or peer.get("public_key", ""),
                    "last_seen": _now_iso(),
                }
            )
            self._save()

    def _add_peer(
        self,
        peer_id: str,
        name: str,
        avatar: str,
        ip: str,
        port: int = 0,
        public_key: str = "",
        approved: bool = True,
    ) -> None:
        with self._lock:
            self._peers[peer_id] = {
                "name": name or "Unbekannt",
                "avatar": avatar or "🙂",
                "ip": ip,
                "port": port or CHAT_PORT,
                "public_key": public_key,
                "approved": approved,
                "last_seen": _now_iso(),
                "added_at": _now_iso(),
            }
            self._requests.pop(peer_id, None)
            self._save()

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
                    "port": self._peer_port(peer),
                    "online": online or self.is_typing(peer_id),
                    "typing": self.is_typing(peer_id),
                    "encrypted": bool(peer.get("public_key")),
                    "waiting": bool(peer.get("waiting")),
                    "last_seen": peer.get("last_seen", ""),
                    "unread": self.unread_count(peer_id),
                }
            )
        result.sort(key=lambda p: (not p["online"], p["name"].lower()))
        return result

    def requests(self) -> list[dict]:
        with self._lock:
            return [
                {"id": rid, **data} for rid, data in self._requests.items()
            ]

    def blocked(self) -> list[dict]:
        with self._lock:
            return [{"id": bid} for bid in self._blocked]

    def accept_request(self, peer_id: str) -> dict:
        with self._lock:
            request = self._requests.get(peer_id)
        if not request:
            return {"error": "Keine Anfrage von diesem Kontakt"}
        self._add_peer(
            peer_id,
            str(request.get("name", "")),
            str(request.get("avatar", "")),
            str(request.get("ip", "")),
            int(request.get("port") or 0),
            str(request.get("public_key", "")),
        )
        asyncio.create_task(self._notify_accepted(peer_id))
        return {"accepted": True, "id": peer_id}

    async def _notify_accepted(self, peer_id: str) -> None:
        me = self.identity()
        await self._deliver(
            peer_id,
            "request",
            {
                "from_id": me["id"],
                "from_name": me["name"],
                "from_avatar": me["avatar"],
                "from_port": CHAT_PORT,
                "public_key": me["public_key"],
                "accepted": True,
            },
        )

    def reject_request(self, peer_id: str) -> dict:
        with self._lock:
            existed = self._requests.pop(peer_id, None) is not None
            if existed:
                self._save()
        return {"rejected": existed}

    def block_peer(self, peer_id: str) -> dict:
        with self._lock:
            if peer_id not in self._blocked:
                self._blocked.append(peer_id)
            self._requests.pop(peer_id, None)
            self._peers.pop(peer_id, None)
            self._save()
        self._delete_messages(peer_id)
        return {"blocked": True, "id": peer_id}

    def unblock_peer(self, peer_id: str) -> dict:
        with self._lock:
            if peer_id in self._blocked:
                self._blocked.remove(peer_id)
                self._save()
                return {"unblocked": True}
        return {"unblocked": False}

    def _delete_messages(self, peer_id: str) -> None:
        with session_scope() as session:
            for row in (
                session.query(P2PMessage).filter(P2PMessage.peer_id == peer_id).all()
            ):
                if row.media_file:
                    (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
                session.delete(row)

    def forget_peer(self, peer_id: str) -> bool:
        with self._lock:
            existed = self._peers.pop(peer_id, None) is not None
            if existed:
                self._save()
        self._delete_messages(peer_id)
        return existed

    def _query_name(self, name: str) -> None:
        self._broadcast({"jon": 1, "type": "query", "name": name.strip().lower()})

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
                    "port": CHAT_PORT,
                    "public_key": me["public_key"],
                }
            )
            return
        peer_id = str(payload.get("id", ""))
        if not peer_id or peer_id in self._blocked:
            return
        self._seen_peers[peer_id] = {
            "name": str(payload.get("name", "")),
            "avatar": str(payload.get("avatar", "")),
            "ip": sender_ip,
            "port": int(payload.get("port") or CHAT_PORT),
            "public_key": str(payload.get("public_key", "")),
        }
        self._remember_peer(
            peer_id,
            str(payload.get("name", "")),
            str(payload.get("avatar", "")),
            sender_ip,
            int(payload.get("port") or 0),
            str(payload.get("public_key", "")),
        )

    _seen_peers: dict[str, dict] = {}

    def _discovered(self, name: str) -> dict | None:
        wanted = name.strip().lower()
        for peer_id, data in list(self._seen_peers.items()):
            if str(data.get("name", "")).strip().lower() == wanted:
                return {"id": peer_id, **data}
        return None

    async def resolve_name(self, name: str, timeout: float = 2.5) -> dict | None:
        found = self._discovered(name) or self._peer_by_name(name)
        if found:
            return found
        self._query_name(name)
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.2)
            found = self._discovered(name)
            if found:
                return found
        return None

    async def name_available(self, name: str) -> tuple[bool, str]:
        clean = name.strip()
        if len(clean) < 2:
            return False, "Der Name muss mindestens 2 Zeichen haben."
        me = self.identity()
        self._query_name(clean)
        await asyncio.sleep(1.2)
        found = self._discovered(clean)
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

    async def _send_request(self, target: dict) -> dict:
        me = self.identity()
        payload = {
            "from_id": me["id"],
            "from_name": me["name"] or "Jon-Nutzer",
            "from_avatar": me["avatar"],
            "from_port": CHAT_PORT,
            "public_key": me["public_key"],
        }
        peer_id = str(target["id"])
        self._add_peer(
            peer_id,
            str(target.get("name", "")),
            str(target.get("avatar", "")),
            str(target.get("ip", "")),
            int(target.get("port") or 0),
            str(target.get("public_key", "")),
        )
        with self._lock:
            self._peers[peer_id]["waiting"] = True
            self._save()
        ok = await self._deliver(peer_id, "request", payload)
        if not ok:
            return {
                "id": peer_id,
                "name": target.get("name"),
                "warning": "Anfrage konnte nicht zugestellt werden — ist Jon dort offen?",
            }
        return {"id": peer_id, "name": target.get("name"), "requested": True}

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
                "seid ihr im selben Netzwerk? Für Freunde im Internet nimm den "
                "Jon-Code."
            }
        return await self._send_request(found)

    async def add_peer_by_ip(self, ip: str) -> dict:
        ip = ip.strip()
        if not ip:
            return {"error": "IP-Adresse angeben"}
        port = CHAT_PORT
        if ":" in ip:
            ip, _, raw_port = ip.partition(":")
            try:
                port = int(raw_port)
            except Exception:
                port = CHAT_PORT
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                data = (await client.get(f"http://{ip}:{port}/ping")).json()
        except Exception:
            return {
                "error": f"Unter {ip} antwortet kein Jon. Läuft Jon dort und seid "
                "ihr im selben WLAN?"
            }
        if not data.get("id"):
            return {"error": "Ungültige Antwort"}
        if str(data["id"]) == self.identity()["id"]:
            return {"error": "Das bist du selbst. 🙂"}
        return await self._send_request(
            {
                "id": str(data["id"]),
                "name": str(data.get("name", "")),
                "avatar": str(data.get("avatar", "")),
                "ip": ip,
                "port": int(data.get("port") or port),
                "public_key": str(data.get("public_key", "")),
            }
        )

    async def add_peer_by_code(self, code: str) -> dict:
        clean = code.strip().lower()
        if len(clean) < 6:
            return {"error": "Der Jon-Code sieht nicht richtig aus."}
        if clean == self.identity()["id"]:
            return {"error": "Das bist du selbst. 🙂"}
        from app.services.relay_service import get_relay_service

        relay = get_relay_service()
        if not relay.connected():
            return {
                "error": "Das Internet-Relay ist nicht verbunden. Aktiviere es im "
                "Zahnrad-Menü unter Verbindungen."
            }
        return await self._send_request(
            {"id": clean, "name": "Freund", "avatar": "🙂", "ip": "", "port": 0}
        )

    def is_typing(self, peer_id: str) -> bool:
        return (time.time() - self._typing.get(peer_id, 0.0)) < 4.0

    def note_typing(self, peer_id: str) -> None:
        self._typing[peer_id] = time.time()

    def typing_peers(self) -> list[str]:
        return [pid for pid in list(self._typing) if self.is_typing(pid)]

    async def _deliver(self, peer_id: str, kind: str, payload: dict) -> bool:
        with self._lock:
            peer = dict(self._peers.get(peer_id) or {})
        public_key = str(peer.get("public_key", ""))
        body: dict = dict(payload)
        if public_key and kind != "request":
            try:
                sealed = get_crypto_service().encrypt(payload, public_key)
                body = {
                    "from_id": payload.get("from_id"),
                    "enc": sealed,
                }
            except Exception:
                body = dict(payload)
        ip = str(peer.get("ip", ""))
        if ip:
            url = f"http://{ip}:{self._peer_port(peer)}/{kind}"
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(url, json=body)
                    if response.status_code == 200:
                        return True
                    if response.status_code == 403:
                        return False
            except Exception:
                pass
        from app.services.relay_service import get_relay_service

        return await get_relay_service().publish(peer_id, kind, body)

    async def send_typing(self, peer_id: str) -> None:
        me = self.identity()
        await self._deliver(peer_id, "typing", {"from_id": me["id"]})

    def pending_notifications(self, channel: str = "app") -> list[dict]:
        seen = self._notified.setdefault(channel, set())
        with session_scope() as session:
            rows = (
                session.query(P2PMessage)
                .filter(P2PMessage.direction == "in", P2PMessage.seen == 0)
                .order_by(P2PMessage.created_at.asc())
                .limit(20)
                .all()
            )
            fresh = [self._as_dict(r) for r in rows if r.id not in seen]
        for item in fresh:
            seen.add(item["id"])
            with self._lock:
                peer = self._peers.get(item["peer_id"]) or {}
            item["avatar"] = peer.get("avatar", "🙂")
            if item.get("group_id"):
                item["group_name"] = (
                    self._groups.get(item["group_id"], {}).get("name", "Gruppe")
                )
        if len(seen) > 400:
            self._notified[channel] = set(list(seen)[-200:])
        return fresh

    def _store(
        self,
        peer_id: str,
        direction: str,
        sender_name: str,
        text: str,
        media: dict | None,
        group_id: str = "",
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
            if media_mime.startswith("image/"):
                media_kind = "image"
            elif media_mime.startswith("video/"):
                media_kind = "video"
            elif media_mime.startswith("audio/"):
                media_kind = "audio"
            else:
                media_kind = "file"
        with session_scope() as session:
            message = P2PMessage(
                peer_id=peer_id,
                group_id=group_id or None,
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
            "group_id": message.group_id,
            "direction": message.direction,
            "sender_name": message.sender_name,
            "text": message.text,
            "media_kind": message.media_kind,
            "media_name": message.media_name,
            "media_mime": message.media_mime,
            "transcript": message.transcript,
            "has_media": bool(message.media_file),
            "created_at": message.created_at.isoformat(),
        }

    async def send(
        self,
        peer_id: str,
        text: str,
        media: dict | None = None,
        group_id: str = "",
    ) -> dict:
        if group_id:
            return await self.send_group(group_id, text, media)
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
            "from_port": CHAT_PORT,
            "public_key": me["public_key"],
            "text": text,
            "media": media or None,
        }
        ok = await self._deliver(peer_id, "inbox", payload)
        if not ok:
            if peer.get("waiting"):
                return {
                    "error": f"{peer.get('name', 'Der Kontakt')} hat deine "
                    "Freundschaftsanfrage noch nicht angenommen."
                }
            return {
                "error": f"{peer.get('name', 'Der Kontakt')} ist gerade nicht "
                "erreichbar."
            }
        with self._lock:
            if self._peers.get(peer_id, {}).pop("waiting", None) is not None:
                self._save()
        try:
            return await asyncio.to_thread(
                self._store, peer_id, "out", me["name"], text, media, group_id
            )
        except ValueError as exc:
            return {"error": str(exc)}

    def receive(self, payload: dict, sender_ip: str) -> dict:
        peer_id = str(payload.get("from_id", "")).strip()
        if not peer_id:
            return {"error": "Absender fehlt"}
        if peer_id in self._blocked:
            return {"error": "blocked"}
        with self._lock:
            known = peer_id in self._peers
        if not known:
            return {"error": "pending"}
        if "enc" in payload:
            with self._lock:
                public_key = str(self._peers[peer_id].get("public_key", ""))
            try:
                payload = get_crypto_service().decrypt(payload["enc"], public_key)
            except Exception:
                return {"error": "Entschlüsselung fehlgeschlagen"}
        self._remember_peer(
            peer_id,
            str(payload.get("from_name", "")),
            str(payload.get("from_avatar", "")),
            sender_ip,
            int(payload.get("from_port") or 0),
            str(payload.get("public_key", "")),
        )
        group = payload.get("group") if isinstance(payload.get("group"), dict) else None
        group_id = ""
        if group and group.get("id"):
            group_id = str(group["id"])
            with self._lock:
                if group_id not in self._groups:
                    self._groups[group_id] = {
                        "name": str(group.get("name", "Gruppe")),
                        "members": [str(m) for m in (group.get("members") or [])],
                        "created_at": _now_iso(),
                    }
                    self._save_groups()
        media = payload.get("media") if isinstance(payload.get("media"), dict) else None
        message = self._store(
            peer_id,
            "in",
            str(payload.get("from_name", "")),
            str(payload.get("text", "")),
            media,
            group_id,
        )
        self._typing.pop(peer_id, None)
        return {"ok": True, "id": message["id"]}

    def receive_request(self, payload: dict, sender_ip: str) -> dict:
        peer_id = str(payload.get("from_id", "")).strip()
        if not peer_id or peer_id in self._blocked:
            return {"error": "blocked"}
        if payload.get("accepted"):
            with self._lock:
                if peer_id in self._peers:
                    self._peers[peer_id].pop("waiting", None)
                    self._peers[peer_id]["public_key"] = str(
                        payload.get("public_key", "")
                    ) or self._peers[peer_id].get("public_key", "")
                    self._save()
            return {"ok": True}
        with self._lock:
            if peer_id in self._peers:
                self._peers[peer_id]["public_key"] = str(
                    payload.get("public_key", "")
                ) or self._peers[peer_id].get("public_key", "")
                self._peers[peer_id].pop("waiting", None)
                self._save()
                return {"ok": True, "auto_accepted": True}
            self._requests[peer_id] = {
                "name": str(payload.get("from_name", "Unbekannt")),
                "avatar": str(payload.get("from_avatar", "🙂")),
                "ip": sender_ip,
                "port": int(payload.get("from_port") or CHAT_PORT),
                "public_key": str(payload.get("public_key", "")),
                "created_at": _now_iso(),
            }
            self._save()
        return {"ok": True, "pending": True}

    def groups(self) -> list[dict]:
        with self._lock:
            items = list(self._groups.items())
        result = []
        for group_id, group in items:
            names = []
            for member in group.get("members", []):
                peer = self._peers.get(member)
                if peer:
                    names.append(peer.get("name", "?"))
            result.append(
                {
                    "id": group_id,
                    "name": group.get("name", "Gruppe"),
                    "members": group.get("members", []),
                    "member_names": names,
                    "unread": self.group_unread(group_id),
                }
            )
        return result

    def create_group(self, name: str, members: list[str]) -> dict:
        clean = name.strip()[:40]
        valid = [m for m in members if m in self._peers]
        if not clean:
            return {"error": "Gruppenname angeben"}
        if not valid:
            return {"error": "Mindestens einen Freund auswählen"}
        group_id = uuid.uuid4().hex[:10]
        with self._lock:
            self._groups[group_id] = {
                "name": clean,
                "members": valid,
                "created_at": _now_iso(),
            }
            self._save_groups()
        return {"id": group_id, "name": clean, "members": valid}

    def delete_group(self, group_id: str) -> bool:
        with self._lock:
            existed = self._groups.pop(group_id, None) is not None
            if existed:
                self._save_groups()
        with session_scope() as session:
            for row in (
                session.query(P2PMessage)
                .filter(P2PMessage.group_id == group_id)
                .all()
            ):
                if row.media_file:
                    (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
                session.delete(row)
        return existed

    async def send_group(
        self, group_id: str, text: str, media: dict | None = None
    ) -> dict:
        with self._lock:
            group = dict(self._groups.get(group_id) or {})
        if not group:
            return {"error": "Unbekannte Gruppe"}
        me = self.identity()
        members = [m for m in group.get("members", []) if m != me["id"]]
        payload_base = {
            "from_id": me["id"],
            "from_name": me["name"] or "Jon-Nutzer",
            "from_avatar": me["avatar"],
            "from_port": CHAT_PORT,
            "public_key": me["public_key"],
            "text": text,
            "media": media or None,
            "group": {
                "id": group_id,
                "name": group.get("name", "Gruppe"),
                "members": [me["id"], *members],
            },
        }
        delivered = 0
        for member in members:
            if await self._deliver(member, "inbox", dict(payload_base)):
                delivered += 1
        message = await asyncio.to_thread(
            self._store, me["id"], "out", me["name"], text, media, group_id
        )
        message["delivered"] = delivered
        message["members"] = len(members)
        return message

    def messages(self, peer_id: str, limit: int = 200) -> list[dict]:
        with session_scope() as session:
            query = session.query(P2PMessage)
            if peer_id in self._groups:
                query = query.filter(P2PMessage.group_id == peer_id)
            else:
                query = query.filter(
                    P2PMessage.peer_id == peer_id, P2PMessage.group_id.is_(None)
                )
            rows = query.order_by(P2PMessage.created_at.asc()).limit(limit).all()
            return [self._as_dict(r) for r in rows]

    def mark_seen(self, peer_id: str) -> int:
        with session_scope() as session:
            query = session.query(P2PMessage).filter(P2PMessage.seen == 0)
            if peer_id in self._groups:
                query = query.filter(P2PMessage.group_id == peer_id)
            else:
                query = query.filter(P2PMessage.peer_id == peer_id)
            rows = query.all()
            for row in rows:
                row.seen = 1
            return len(rows)

    def unread_count(self, peer_id: str = "") -> int:
        with session_scope() as session:
            query = session.query(P2PMessage).filter(P2PMessage.seen == 0)
            if peer_id:
                query = query.filter(
                    P2PMessage.peer_id == peer_id, P2PMessage.group_id.is_(None)
                )
            return query.count()

    def group_unread(self, group_id: str) -> int:
        with session_scope() as session:
            return (
                session.query(P2PMessage)
                .filter(P2PMessage.group_id == group_id, P2PMessage.seen == 0)
                .count()
            )

    def total_unread(self) -> int:
        with session_scope() as session:
            return session.query(P2PMessage).filter(P2PMessage.seen == 0).count()

    def media_path(self, message_id: str) -> tuple[Path, str] | None:
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is None or not row.media_file:
                return None
            return (
                MEDIA_DIR / row.media_file,
                row.media_mime or "application/octet-stream",
            )

    def transcribe(self, message_id: str) -> dict:
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is None or not row.media_file:
                return {"error": "Nachricht hat keine Audiodatei"}
            if row.transcript:
                return {"transcript": row.transcript}
            path = MEDIA_DIR / row.media_file
        if not path.exists():
            return {"error": "Audiodatei nicht gefunden"}
        try:
            from app.services.voice_service import VoiceService

            text = VoiceService().transcribe_wav(path.read_bytes())
        except Exception as exc:
            return {"error": f"Transkription fehlgeschlagen: {exc}"}
        if not text.strip():
            return {"error": "Nichts verstanden"}
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is not None:
                row.transcript = text.strip()
        return {"transcript": text.strip()}

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
                            "port": CHAT_PORT,
                            "public_key": me["public_key"],
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
