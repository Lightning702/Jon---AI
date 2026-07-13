from __future__ import annotations

import asyncio
import base64
import ipaddress
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
from app.db.models import P2PMessage, P2POutbox
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
        self._invites: dict[str, dict] = {}
        self._groups: dict[str, dict] = self._load_groups()
        self._transport: asyncio.DatagramTransport | None = None
        self._typing: dict[tuple[str, str], float] = {}
        self._notified: dict[str, set[str]] = {}
        self._loc_cache: dict[str, str] = {}
        self._cleaned = False
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
                if isinstance(data, dict) and "groups" in data:
                    self._invites = data.get("invites", {})
                    return data.get("groups", {})
                if isinstance(data, dict):
                    self._invites = {}
                    return data
            except Exception:
                pass
        self._invites = {}
        return {}

    def _save_groups(self) -> None:
        try:
            GROUPS_FILE.write_text(
                json.dumps(
                    {"groups": self._groups, "invites": self._invites},
                    ensure_ascii=False,
                    indent=2,
                ),
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

    @staticmethod
    def _is_public_ip(ip: str) -> bool:
        try:
            return ipaddress.ip_address(ip).is_global
        except Exception:
            return False

    async def lookup_location(self, ip: str = "") -> str:
        key = ip or "self"
        cached = self._loc_cache.get(key)
        if cached is not None:
            return cached
        location = ""
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                data = (
                    await client.get(
                        f"http://ip-api.com/json/{ip}"
                        "?fields=status,country,city&lang=de"
                    )
                ).json()
            if data.get("status") == "success":
                country = str(data.get("country", "")).strip()
                city = str(data.get("city", "")).strip()
                if country:
                    location = f"Ungefähr aus {country}"
                    if city:
                        location += f" · {city}"
        except Exception:
            location = ""
        if location:
            self._loc_cache[key] = location
        return location

    async def _refine_request_location(self, peer_id: str, ip: str) -> None:
        location = await self.lookup_location(ip)
        if not location:
            return
        with self._lock:
            request = self._requests.get(peer_id)
            if request is not None:
                request["location"] = location
                self._save()

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

    def discovered(self) -> list[dict]:
        me = self.identity()["id"]
        with self._lock:
            friends = set(self._peers)
            blocked = set(self._blocked)
        now = time.time()
        result = []
        for peer_id, data in list(self._seen_peers.items()):
            if now - float(data.get("seen_at", 0)) > 30:
                continue
            if peer_id == me or peer_id in blocked or peer_id in friends:
                continue
            name = str(data.get("name", "")).strip()
            if not name:
                continue
            result.append(
                {
                    "id": peer_id,
                    "name": name,
                    "avatar": str(data.get("avatar", "")) or "🙂",
                }
            )
        result.sort(key=lambda p: p["name"].lower())
        return result

    def _known_chat_ids(self) -> tuple[set[str], set[str]]:
        with self._lock:
            return set(self._peers), set(self._groups)

    def _is_known(self, peer_id: str, group_id: str | None) -> bool:
        peer_ids, group_ids = self._known_chat_ids()
        if group_id:
            return group_id in group_ids
        return peer_id in peer_ids

    def _cleanup_orphans(self) -> None:
        if self._cleaned:
            return
        self._cleaned = True
        try:
            peer_ids, group_ids = self._known_chat_ids()
            with session_scope() as session:
                for row in session.query(P2PMessage).all():
                    known = (
                        row.group_id in group_ids
                        if row.group_id
                        else row.peer_id in peer_ids
                    )
                    if known:
                        continue
                    if row.media_file:
                        (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
                    session.delete(row)
        except Exception:
            self._cleaned = False

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
        self._later(self._notify_accepted(peer_id))
        return {"accepted": True, "id": peer_id}

    async def _notify_accepted(self, peer_id: str) -> None:
        me = self.identity()
        await self._send_or_queue(
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
            "seen_at": time.time(),
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
            "from_location": await self.lookup_location(),
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

    def is_typing(self, peer_id: str, group_id: str = "") -> bool:
        stamp = self._typing.get((peer_id, group_id), 0.0)
        return (time.time() - stamp) < 4.0

    def note_typing(self, peer_id: str, group_id: str = "") -> None:
        self._typing[(peer_id, group_id)] = time.time()

    def typing_peers(self) -> list[dict]:
        return [
            {"peer_id": peer_id, "group_id": group_id}
            for (peer_id, group_id) in list(self._typing)
            if self.is_typing(peer_id, group_id)
        ]

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

    async def send_typing(self, peer_id: str, group_id: str = "") -> None:
        me = self.identity()
        await self._deliver(
            peer_id, "typing", {"from_id": me["id"], "group_id": group_id}
        )

    def pending_notifications(self, channel: str = "app") -> list[dict]:
        self._cleanup_orphans()
        seen = self._notified.setdefault(channel, set())
        with session_scope() as session:
            rows = (
                session.query(P2PMessage)
                .filter(P2PMessage.direction == "in", P2PMessage.seen == 0)
                .order_by(P2PMessage.created_at.asc())
                .limit(20)
                .all()
            )
            fresh = [
                self._as_dict(r)
                for r in rows
                if r.id not in seen and self._is_known(r.peer_id, r.group_id)
            ]
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
        message_id: str = "",
        reply_to: str = "",
        reply_preview: str = "",
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
            if message_id and session.get(P2PMessage, message_id) is not None:
                return self._as_dict(session.get(P2PMessage, message_id))
            message = P2PMessage(
                id=message_id or uuid.uuid4().hex,
                peer_id=peer_id,
                group_id=group_id or None,
                direction=direction,
                sender_name=sender_name,
                text=text[:8000],
                media_file=media_file,
                media_kind=media_kind,
                media_name=media_name,
                media_mime=media_mime,
                reply_to=reply_to or None,
                reply_preview=reply_preview or None,
                seen=1 if direction == "out" else 0,
            )
            session.add(message)
            session.flush()
            return self._as_dict(message)

    @staticmethod
    def _as_dict(message: P2PMessage) -> dict:
        try:
            reactions = json.loads(message.reactions) if message.reactions else {}
        except Exception:
            reactions = {}
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
            "reply_to": message.reply_to,
            "reply_preview": message.reply_preview,
            "reactions": reactions,
            "deleted": bool(message.deleted),
            "delivered": message.delivered_at is not None,
            "read": message.read_at is not None,
            "has_media": bool(message.media_file),
            "created_at": message.created_at.isoformat(),
        }

    def _queue(self, peer_id: str, kind: str, payload: dict, message_id: str = "") -> None:
        with session_scope() as session:
            session.add(
                P2POutbox(
                    peer_id=peer_id,
                    kind=kind,
                    message_id=message_id or None,
                    payload=json.dumps(payload, ensure_ascii=False),
                )
            )

    def _mark_delivered(self, message_id: str) -> None:
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is not None and row.delivered_at is None:
                row.delivered_at = datetime.now(timezone.utc)

    async def _send_or_queue(
        self, peer_id: str, kind: str, payload: dict, message_id: str = ""
    ) -> bool:
        ok = await self._deliver(peer_id, kind, payload)
        if ok:
            if message_id:
                await asyncio.to_thread(self._mark_delivered, message_id)
            return True
        await asyncio.to_thread(self._queue, peer_id, kind, payload, message_id)
        return False

    def _reply_preview(self, reply_to: str) -> str:
        if not reply_to:
            return ""
        with session_scope() as session:
            row = session.get(P2PMessage, reply_to)
            if row is None:
                return ""
            who = "Du" if row.direction == "out" else (row.sender_name or "?")
            body = row.text or (f"[{row.media_kind}]" if row.media_kind else "")
            return f"{who}: {body[:80]}"

    async def send(
        self,
        peer_id: str,
        text: str,
        media: dict | None = None,
        group_id: str = "",
        reply_to: str = "",
    ) -> dict:
        if group_id:
            return await self.send_group(group_id, text, media, reply_to)
        with self._lock:
            peer = dict(self._peers.get(peer_id) or {})
        if not peer:
            return {"error": "Unbekannter Kontakt"}
        if not text.strip() and not (media and media.get("data")):
            return {"error": "Leere Nachricht"}
        if peer.get("waiting"):
            return {
                "error": f"{peer.get('name', 'Der Kontakt')} hat deine "
                "Freundschaftsanfrage noch nicht angenommen."
            }
        me = self.identity()
        message_id = uuid.uuid4().hex
        preview = await asyncio.to_thread(self._reply_preview, reply_to)
        payload = {
            "from_id": me["id"],
            "from_name": me["name"] or "Jon-Nutzer",
            "from_avatar": me["avatar"],
            "from_port": CHAT_PORT,
            "public_key": me["public_key"],
            "msg_id": message_id,
            "text": text,
            "media": media or None,
            "reply_to": reply_to or "",
            "reply_preview": preview,
        }
        try:
            message = await asyncio.to_thread(
                self._store,
                peer_id,
                "out",
                me["name"],
                text,
                media,
                "",
                message_id,
                reply_to,
                preview,
            )
        except ValueError as exc:
            return {"error": str(exc)}
        delivered = await self._send_or_queue(peer_id, "inbox", payload, message_id)
        message["delivered"] = delivered
        message["queued"] = not delivered
        return message

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
        with self._lock:
            if self._peers.get(peer_id, {}).pop("waiting", None) is not None:
                self._save()
        group = payload.get("group") if isinstance(payload.get("group"), dict) else None
        group_id = ""
        if group and group.get("id"):
            group_id = str(group["id"])
            with self._lock:
                if group_id not in self._groups:
                    return {"error": "Gruppe nicht angenommen"}
        media = payload.get("media") if isinstance(payload.get("media"), dict) else None
        message = self._store(
            peer_id,
            "in",
            str(payload.get("from_name", "")),
            str(payload.get("text", "")),
            media,
            group_id,
            str(payload.get("msg_id", "")),
            str(payload.get("reply_to", "")),
            str(payload.get("reply_preview", "")),
        )
        self._typing.pop((peer_id, group_id), None)
        if payload.get("msg_id"):
            self._later(
                self._send_event(
                    peer_id,
                    {
                        "type": "receipt",
                        "msg_id": str(payload["msg_id"]),
                        "state": "delivered",
                    },
                )
            )
        return {"ok": True, "id": message["id"]}

    def _later(self, coro) -> None:
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            try:
                asyncio.run(coro)
            except Exception:
                pass

    async def _send_event(self, peer_id: str, event: dict) -> bool:
        me = self.identity()
        payload = {"from_id": me["id"], "from_name": me["name"], **event}
        return await self._deliver(peer_id, "event", payload)

    async def _broadcast_event(self, message: dict, event: dict) -> None:
        group_id = message.get("group_id")
        if group_id:
            with self._lock:
                members = list(
                    (self._groups.get(group_id) or {}).get("members", [])
                )
            me = self.identity()["id"]
            for member in members:
                if member != me:
                    await self._send_event(member, event)
            return
        await self._send_event(message["peer_id"], event)

    def receive_event(self, payload: dict, sender_ip: str) -> dict:
        peer_id = str(payload.get("from_id", "")).strip()
        if not peer_id or peer_id in self._blocked:
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
        kind = str(payload.get("type", ""))
        message_id = str(payload.get("msg_id", ""))

        if kind == "receipt" and message_id:
            with session_scope() as session:
                row = session.get(P2PMessage, message_id)
                if row is not None:
                    now = datetime.now(timezone.utc)
                    if row.delivered_at is None:
                        row.delivered_at = now
                    if payload.get("state") == "read" and row.read_at is None:
                        row.read_at = now
            return {"ok": True}

        if kind == "reaction" and message_id:
            emoji = str(payload.get("emoji", ""))[:8]
            who = str(payload.get("from_name", "?"))
            with session_scope() as session:
                row = session.get(P2PMessage, message_id)
                if row is None:
                    return {"ok": True}
                try:
                    data = json.loads(row.reactions) if row.reactions else {}
                except Exception:
                    data = {}
                people = [p for p in data.get(emoji, []) if p != who]
                if len(people) == len(data.get(emoji, [])):
                    people.append(who)
                if people:
                    data[emoji] = people
                else:
                    data.pop(emoji, None)
                row.reactions = json.dumps(data, ensure_ascii=False)
            return {"ok": True}

        if kind == "delete" and message_id:
            self._tombstone(message_id)
            return {"ok": True}

        if kind == "group_invite":
            group = payload.get("group") or {}
            group_id = str(group.get("id", ""))
            if not group_id:
                return {"error": "Ungültige Einladung"}
            members = [m for m in (group.get("members") or []) if isinstance(m, dict)]
            me = self.identity()["id"]
            with self._lock:
                known_member = any(
                    m.get("id") in self._peers and m.get("id") != me for m in members
                ) or peer_id in self._peers
            if not known_member:
                return {"error": "keine gemeinsamen Freunde"}
            with self._lock:
                if group_id in self._groups:
                    return {"ok": True}
                self._invites[group_id] = {
                    "name": str(group.get("name", "Gruppe")),
                    "from_id": peer_id,
                    "from_name": str(payload.get("from_name", "")),
                    "members": members,
                    "created_at": _now_iso(),
                }
                self._save_groups()
            return {"ok": True, "pending": True}

        if kind == "group_leave":
            group_id = str(payload.get("group_id", ""))
            with self._lock:
                group = self._groups.get(group_id)
                if group and peer_id in group.get("members", []):
                    group["members"] = [
                        m for m in group["members"] if m != peer_id
                    ]
                    self._save_groups()
            if group is not None:
                name = str(payload.get("from_name", "Jemand"))
                self._store(
                    peer_id,
                    "in",
                    "",
                    f"{name} hat die Gruppe verlassen.",
                    None,
                    group_id,
                )
            return {"ok": True}

        return {"ok": True}

    def _tombstone(self, message_id: str) -> None:
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is None:
                return
            if row.media_file:
                (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
            row.deleted = 1
            row.text = ""
            row.media_file = None
            row.media_kind = None
            row.media_name = None
            row.media_mime = None
            row.transcript = None
            row.reactions = None
            row.seen = 1

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
        location = str(payload.get("from_location", "")).strip()
        if sender_ip and not self._is_public_ip(sender_ip):
            location = "Aus deinem Netzwerk (WLAN)"
        elif not location:
            location = "Über das Internet"
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
                "location": location,
                "created_at": _now_iso(),
            }
            self._save()
        if self._is_public_ip(sender_ip):
            self._later(self._refine_request_location(peer_id, sender_ip))
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

    def _member_card(self, peer_id: str) -> dict:
        me = self.identity()
        if peer_id == me["id"]:
            return {
                "id": me["id"],
                "name": me["name"],
                "avatar": me["avatar"],
                "ip": self.local_ip(),
                "port": CHAT_PORT,
                "public_key": me["public_key"],
            }
        peer = self._peers.get(peer_id) or {}
        return {
            "id": peer_id,
            "name": peer.get("name", "?"),
            "avatar": peer.get("avatar", "🙂"),
            "ip": peer.get("ip", ""),
            "port": self._peer_port(peer),
            "public_key": peer.get("public_key", ""),
        }

    async def create_group(self, name: str, members: list[str]) -> dict:
        clean = name.strip()[:40]
        valid = [m for m in members if m in self._peers]
        if not clean:
            return {"error": "Gruppenname angeben"}
        if not valid:
            return {"error": "Mindestens einen Freund auswählen"}
        me = self.identity()
        group_id = uuid.uuid4().hex[:10]
        all_members = [me["id"], *valid]
        with self._lock:
            self._groups[group_id] = {
                "name": clean,
                "members": all_members,
                "created_at": _now_iso(),
            }
            self._save_groups()
        cards = [self._member_card(m) for m in all_members]
        for member in valid:
            await self._send_or_queue(
                member,
                "event",
                {
                    "from_id": me["id"],
                    "from_name": me["name"],
                    "type": "group_invite",
                    "group": {"id": group_id, "name": clean, "members": cards},
                },
            )
        return {"id": group_id, "name": clean, "members": all_members}

    def group_invites(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": gid,
                    "name": data.get("name", "Gruppe"),
                    "from_name": data.get("from_name", ""),
                    "members": [m.get("name", "?") for m in data.get("members", [])],
                }
                for gid, data in self._invites.items()
            ]

    def accept_group(self, group_id: str) -> dict:
        with self._lock:
            invite = self._invites.get(group_id)
        if not invite:
            return {"error": "Keine Einladung für diese Gruppe"}
        me = self.identity()["id"]
        members = invite.get("members", [])
        if not any(
            m.get("id") in self._peers and m.get("id") != me for m in members
        ) and invite.get("from_id") not in self._peers:
            return {"error": "Du bist mit niemandem aus dieser Gruppe befreundet."}
        for member in members:
            member_id = str(member.get("id", ""))
            if not member_id or member_id == me or member_id in self._blocked:
                continue
            if member_id not in self._peers:
                self._add_peer(
                    member_id,
                    str(member.get("name", "")),
                    str(member.get("avatar", "")),
                    str(member.get("ip", "")),
                    int(member.get("port") or 0),
                    str(member.get("public_key", "")),
                )
                with self._lock:
                    self._peers[member_id]["via_group"] = True
                    self._save()
        with self._lock:
            self._groups[group_id] = {
                "name": invite.get("name", "Gruppe"),
                "members": [str(m.get("id")) for m in members],
                "created_at": _now_iso(),
            }
            self._invites.pop(group_id, None)
            self._save_groups()
        return {"accepted": True, "id": group_id}

    def reject_group(self, group_id: str) -> dict:
        with self._lock:
            existed = self._invites.pop(group_id, None) is not None
            if existed:
                self._save_groups()
        return {"rejected": existed}

    async def leave_group(self, group_id: str) -> dict:
        with self._lock:
            group = dict(self._groups.get(group_id) or {})
        if not group:
            return {"error": "Unbekannte Gruppe"}
        me = self.identity()
        for member in group.get("members", []):
            if member != me["id"]:
                await self._send_or_queue(
                    member,
                    "event",
                    {
                        "from_id": me["id"],
                        "from_name": me["name"],
                        "type": "group_leave",
                        "group_id": group_id,
                    },
                )
        self.delete_group(group_id)
        return {"left": True, "id": group_id}

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
        self,
        group_id: str,
        text: str,
        media: dict | None = None,
        reply_to: str = "",
    ) -> dict:
        with self._lock:
            group = dict(self._groups.get(group_id) or {})
        if not group:
            return {"error": "Unbekannte Gruppe"}
        if not text.strip() and not (media and media.get("data")):
            return {"error": "Leere Nachricht"}
        me = self.identity()
        members = [m for m in group.get("members", []) if m != me["id"]]
        message_id = uuid.uuid4().hex
        preview = await asyncio.to_thread(self._reply_preview, reply_to)
        payload_base = {
            "from_id": me["id"],
            "from_name": me["name"] or "Jon-Nutzer",
            "from_avatar": me["avatar"],
            "from_port": CHAT_PORT,
            "public_key": me["public_key"],
            "msg_id": message_id,
            "text": text,
            "media": media or None,
            "reply_to": reply_to or "",
            "reply_preview": preview,
            "group": {
                "id": group_id,
                "name": group.get("name", "Gruppe"),
                "members": [me["id"], *members],
            },
        }
        message = await asyncio.to_thread(
            self._store,
            me["id"],
            "out",
            me["name"],
            text,
            media,
            group_id,
            message_id,
            reply_to,
            preview,
        )
        delivered = 0
        for member in members:
            if await self._send_or_queue(member, "inbox", dict(payload_base)):
                delivered += 1
        if delivered:
            await asyncio.to_thread(self._mark_delivered, message_id)
        message["delivered"] = delivered > 0
        message["delivered_to"] = delivered
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
        receipts: list[tuple[str, str]] = []
        with session_scope() as session:
            query = session.query(P2PMessage).filter(P2PMessage.seen == 0)
            if peer_id in self._groups:
                query = query.filter(P2PMessage.group_id == peer_id)
            else:
                query = query.filter(P2PMessage.peer_id == peer_id)
            rows = query.all()
            for row in rows:
                row.seen = 1
                if row.direction == "in" and not row.group_id:
                    receipts.append((row.peer_id, row.id))
        for sender, message_id in receipts:
            self._later(
                self._send_event(
                    sender,
                    {"type": "receipt", "msg_id": message_id, "state": "read"},
                )
            )
        return len(rows)

    async def react(self, message_id: str, emoji: str) -> dict:
        emoji = emoji.strip()[:8]
        if not emoji:
            return {"error": "Emoji angeben"}
        me = self.identity()["name"] or "Du"
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is None or row.deleted:
                return {"error": "Nachricht nicht gefunden"}
            try:
                data = json.loads(row.reactions) if row.reactions else {}
            except Exception:
                data = {}
            people = [p for p in data.get(emoji, []) if p != me]
            if len(people) == len(data.get(emoji, [])):
                people.append(me)
            if people:
                data[emoji] = people
            else:
                data.pop(emoji, None)
            row.reactions = json.dumps(data, ensure_ascii=False)
            message = self._as_dict(row)
        await self._broadcast_event(
            message, {"type": "reaction", "msg_id": message_id, "emoji": emoji}
        )
        return message

    async def delete_message(self, message_id: str, for_all: bool = False) -> dict:
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is None:
                return {"error": "Nachricht nicht gefunden"}
            message = self._as_dict(row)
        if for_all and message["direction"] != "out":
            return {"error": "Nur eigene Nachrichten können für alle gelöscht werden."}
        if for_all:
            await self._broadcast_event(
                message, {"type": "delete", "msg_id": message_id}
            )
            await asyncio.to_thread(self._tombstone, message_id)
            return {"deleted": True, "for_all": True}
        with session_scope() as session:
            row = session.get(P2PMessage, message_id)
            if row is not None:
                if row.media_file:
                    (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
                session.delete(row)
        return {"deleted": True, "for_all": False}

    def clear_chat(self, chat_id: str) -> int:
        with session_scope() as session:
            query = session.query(P2PMessage)
            if chat_id in self._groups:
                query = query.filter(P2PMessage.group_id == chat_id)
            else:
                query = query.filter(
                    P2PMessage.peer_id == chat_id, P2PMessage.group_id.is_(None)
                )
            rows = query.all()
            for row in rows:
                if row.media_file:
                    (MEDIA_DIR / row.media_file).unlink(missing_ok=True)
                session.delete(row)
            return len(rows)

    def search(self, query: str, limit: int = 40) -> list[dict]:
        needle = query.strip().lower()
        if len(needle) < 2:
            return []
        results = []
        with session_scope() as session:
            rows = (
                session.query(P2PMessage)
                .filter(P2PMessage.deleted == 0)
                .order_by(P2PMessage.created_at.desc())
                .limit(2000)
                .all()
            )
            for row in rows:
                haystack = f"{row.text or ''} {row.transcript or ''}".lower()
                if needle not in haystack:
                    continue
                item = self._as_dict(row)
                if row.group_id:
                    item["chat_name"] = (
                        self._groups.get(row.group_id, {}).get("name", "Gruppe")
                    )
                    item["chat_id"] = row.group_id
                else:
                    peer = self._peers.get(row.peer_id) or {}
                    item["chat_name"] = peer.get("name", "Unbekannt")
                    item["chat_id"] = row.peer_id
                results.append(item)
                if len(results) >= limit:
                    break
        return results

    async def outbox_loop(self) -> None:
        while True:
            await asyncio.sleep(12)
            try:
                with session_scope() as session:
                    rows = (
                        session.query(P2POutbox)
                        .order_by(P2POutbox.created_at.asc())
                        .limit(20)
                        .all()
                    )
                    pending = [
                        (r.id, r.peer_id, r.kind, r.payload, r.message_id, r.tries)
                        for r in rows
                    ]
                for row_id, peer_id, kind, raw, message_id, tries in pending:
                    if peer_id not in self._peers:
                        await asyncio.to_thread(self._drop_outbox, row_id)
                        continue
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        await asyncio.to_thread(self._drop_outbox, row_id)
                        continue
                    if await self._deliver(peer_id, kind, payload):
                        if message_id:
                            await asyncio.to_thread(self._mark_delivered, message_id)
                        await asyncio.to_thread(self._drop_outbox, row_id)
                    elif tries > 200:
                        await asyncio.to_thread(self._drop_outbox, row_id)
                    else:
                        await asyncio.to_thread(self._bump_outbox, row_id)
            except Exception:
                continue

    def _drop_outbox(self, row_id: str) -> None:
        with session_scope() as session:
            row = session.get(P2POutbox, row_id)
            if row is not None:
                session.delete(row)

    def _bump_outbox(self, row_id: str) -> None:
        with session_scope() as session:
            row = session.get(P2POutbox, row_id)
            if row is not None:
                row.tries += 1

    def pending_outbox(self) -> int:
        with session_scope() as session:
            return session.query(P2POutbox).count()

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
        self._cleanup_orphans()
        with session_scope() as session:
            rows = (
                session.query(P2PMessage).filter(P2PMessage.seen == 0).all()
            )
            return sum(
                1 for row in rows if self._is_known(row.peer_id, row.group_id)
            )

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
