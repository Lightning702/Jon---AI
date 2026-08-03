from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import uuid
from datetime import datetime
from typing import Any

import httpx

from app.core.config import DATA_DIR

SHARE_FILE = DATA_DIR / "ollama_share.json"

DISCOVERY_PORT = int(os.environ.get("JON_SHARE_DISCOVERY_PORT", "8762"))
MAGIC = "jon-ollama-share"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
INVITE_LENGTH = 10
LINK_SCHEME = "jon://ollama/"
JOIN_LIMIT = 10
JOIN_WINDOW = 60.0
SESSION_IDLE = 90.0
REMOTE_PREFIX = "share:"
VISIBILITIES = ("private", "invited", "public")

CODE_PATTERN = re.compile(r"^[A-Z0-9]{4,16}$")
LINK_PATTERN = re.compile(
    r"^(?:jon://ollama/)?([A-Za-z0-9]{4,16})(?:@([^\s:/]+|\[[^\]]+\])(?::(\d+))?)?/?$"
)

SHARE_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "name": "",
    "description": "",
    "visibility": "private",
    "code": "",
    "created_at": "",
}


class ShareError(ValueError):
    pass


def _now() -> float:
    return time.time()


def _stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def make_code(length: int = CODE_LENGTH) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def parse_invite(raw: str) -> tuple[str, str, int]:
    text = str(raw or "").strip()
    if text.lower().startswith(LINK_SCHEME):
        text = text[len(LINK_SCHEME):]
    match = LINK_PATTERN.match(text)
    if not match:
        raise ShareError(
            "Der Freigabecode sieht nicht richtig aus. Erlaubt sind zum Beispiel "
            "AB39KD12 oder AB39KD12@192.168.1.50:8758."
        )
    code = match.group(1).upper()
    host = (match.group(2) or "").strip("[]")
    port = int(match.group(3) or 0)
    return code, host, port


class OllamaShareService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data = self._load()
        self._sessions: dict[str, dict] = {}
        self._joins: dict[str, list[float]] = {}

    def _load(self) -> dict:
        data = {"share": dict(SHARE_DEFAULTS), "grants": {}, "invites": {}, "remotes": {}}
        if SHARE_FILE.exists():
            try:
                stored = json.loads(SHARE_FILE.read_text(encoding="utf-8"))
            except Exception:
                stored = {}
            if isinstance(stored, dict):
                share = stored.get("share")
                if isinstance(share, dict):
                    for key in SHARE_DEFAULTS:
                        if key in share and share[key] is not None:
                            data["share"][key] = share[key]
                for key in ("grants", "invites", "remotes"):
                    value = stored.get(key)
                    if isinstance(value, dict):
                        data[key] = value
        if not data["share"]["code"]:
            data["share"]["code"] = make_code()
            data["share"]["created_at"] = _stamp()
        return data

    def _save(self) -> None:
        try:
            SHARE_FILE.parent.mkdir(parents=True, exist_ok=True)
            SHARE_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _identity(self) -> dict:
        try:
            from app.services.p2p_service import get_p2p_service

            me = get_p2p_service().identity()
            return {"id": me["id"], "name": me["name"] or "Jon-Nutzer"}
        except Exception:
            return {"id": uuid.uuid4().hex[:12], "name": "Jon-Nutzer"}

    def _host(self) -> str:
        try:
            from app.services.coop_lan_service import invite_host

            return invite_host()
        except Exception:
            return "127.0.0.1"

    def _port(self) -> int:
        from app.services.p2p_service import CHAT_PORT

        return CHAT_PORT

    def shared_model(self) -> str:
        from app.services.ollama_service import get_ollama_service

        service = get_ollama_service()
        chosen = service.selected_model()
        if chosen:
            return chosen
        known = service.known_models()
        return known[0] if known else ""

    def share(self) -> dict:
        with self._lock:
            share = dict(self._data["share"])
            grants = len(self._data["grants"])
            invites = [
                dict(item)
                for item in self._data["invites"].values()
                if not item.get("used_by")
            ]
        host = self._host()
        port = self._port()
        share["host"] = host
        share["port"] = port
        share["link"] = f"{LINK_SCHEME}{share['code']}@{host}:{port}"
        share["user_count"] = grants
        share["open_invites"] = invites
        share["owner"] = self._identity()["name"] or "Jon-Nutzer"
        share["shared_model"] = self.shared_model()
        return share

    def update_share(self, values: dict) -> dict:
        with self._lock:
            share = self._data["share"]
            if "enabled" in values and values["enabled"] is not None:
                share["enabled"] = bool(values["enabled"])
            if values.get("name") is not None:
                share["name"] = str(values["name"]).strip()[:48]
            if values.get("description") is not None:
                share["description"] = str(values["description"]).strip()[:280]
            if values.get("visibility") is not None:
                visibility = str(values["visibility"]).strip().lower()
                if visibility not in VISIBILITIES:
                    raise ShareError(
                        "Sichtbarkeit: Erlaubt sind privat, eingeladen und öffentlich."
                    )
                share["visibility"] = visibility
            self._save()
        return self.share()

    def new_code(self) -> dict:
        with self._lock:
            self._data["share"]["code"] = make_code()
            self._data["share"]["created_at"] = _stamp()
            self._save()
        return self.share()

    def create_invite(self, label: str = "") -> dict:
        code = make_code(INVITE_LENGTH)
        entry = {
            "code": code,
            "label": str(label).strip()[:48],
            "created_at": _stamp(),
            "used_by": "",
        }
        with self._lock:
            self._data["invites"][code] = entry
            self._save()
        host = self._host()
        port = self._port()
        result = dict(entry)
        result["link"] = f"{LINK_SCHEME}{code}@{host}:{port}"
        return result

    def delete_invite(self, code: str) -> bool:
        with self._lock:
            existed = self._data["invites"].pop(str(code).upper(), None) is not None
            if existed:
                self._save()
        return existed

    def _grant_public(self, grant: dict) -> dict:
        session = self._sessions.get(grant["id"], {})
        last = max(float(grant.get("last_seen") or 0.0), float(session.get("at") or 0.0))
        active = int(session.get("active") or 0)
        return {
            "id": grant["id"],
            "user": grant.get("user", ""),
            "user_id": grant.get("user_id", ""),
            "address": grant.get("address", ""),
            "created_at": grant.get("created_at", ""),
            "model": session.get("model") or grant.get("model", ""),
            "requests": int(grant.get("requests") or 0),
            "sessions": active,
            "state": (
                "aktiv"
                if active > 0
                else ("verbunden" if last and _now() - last < SESSION_IDLE else "offline")
            ),
            "last_activity": (
                datetime.fromtimestamp(last).isoformat(timespec="seconds")
                if last
                else ""
            ),
            "invite": grant.get("invite", ""),
        }

    def users(self) -> list[dict]:
        with self._lock:
            grants = [dict(item) for item in self._data["grants"].values()]
        found = [self._grant_public(grant) for grant in grants]
        found.sort(key=lambda item: item["last_activity"], reverse=True)
        return found

    def remove_user(self, grant_id: str) -> bool:
        with self._lock:
            existed = self._data["grants"].pop(str(grant_id), None) is not None
            if existed:
                self._save()
        self._sessions.pop(str(grant_id), None)
        return existed

    def revoke_all(self) -> int:
        with self._lock:
            count = len(self._data["grants"])
            self._data["grants"] = {}
            self._save()
        self._sessions.clear()
        return count

    def _rate_limited(self, address: str) -> bool:
        now = _now()
        if len(self._joins) > 500:
            self._joins = {
                key: stamps
                for key, stamps in self._joins.items()
                if stamps and now - stamps[-1] < JOIN_WINDOW
            }
        hits = [t for t in self._joins.get(address, []) if now - t < JOIN_WINDOW]
        hits.append(now)
        self._joins[address] = hits
        return len(hits) > JOIN_LIMIT

    def info(self) -> dict:
        share = self.share()
        if not share["enabled"] or share["visibility"] == "private":
            return {"available": False}
        return {
            "available": True,
            "name": share["name"] or f"Ollama von {share['owner']}",
            "description": share["description"],
            "visibility": share["visibility"],
            "owner": share["owner"],
        }

    def providers(self) -> list[dict]:
        found: list[dict] = []
        with self._lock:
            entries = [dict(item) for item in self._data["remotes"].values()]
        for entry in entries:
            model = str(entry.get("model") or "")
            if not model:
                models = entry.get("models") or []
                model = str(models[0]) if models else ""
            if not model:
                continue
            owner = str(entry.get("owner") or "").strip()
            found.append(
                {
                    "provider": f"{REMOTE_PREFIX}{entry['code']}",
                    "label": f"Ollama von {owner or entry['code']}",
                    "owner": owner,
                    "model": model,
                }
            )
        return found

    def join(self, payload: dict, address: str) -> dict:
        raw = str(payload.get("code", "")).strip().upper()
        user = str(payload.get("name", "")).strip()[:48] or "Unbekannt"
        user_id = str(payload.get("user_id", "")).strip()[:64]
        if self._rate_limited(address or "?"):
            raise ShareError("Zu viele Versuche. Bitte kurz warten.")
        if not CODE_PATTERN.match(raw):
            raise ShareError("Freigabecode ungültig.")
        with self._lock:
            share = self._data["share"]
            if not share["enabled"]:
                raise ShareError("Dieser Ollama-Server ist nicht freigegeben.")
            visibility = share["visibility"]
            if visibility == "private":
                raise ShareError("Diese Freigabe ist privat.")
            invite = self._data["invites"].get(raw)
            if invite is not None:
                if invite.get("used_by"):
                    raise ShareError("Diese Einladung wurde bereits verwendet.")
            elif visibility == "invited":
                raise ShareError(
                    "Dieser Server nimmt nur eingeladene Benutzer an. Bitte frag "
                    "den Besitzer nach einer Einladung."
                )
            elif not hmac.compare_digest(raw, str(share["code"])):
                raise ShareError("Freigabecode unbekannt.")
            token = secrets.token_urlsafe(32)
            grant_id = uuid.uuid4().hex[:12]
            self._data["grants"][grant_id] = {
                "id": grant_id,
                "user": user,
                "user_id": user_id,
                "token_hash": hash_token(token),
                "created_at": _stamp(),
                "last_seen": _now(),
                "address": address,
                "model": "",
                "requests": 0,
                "invite": raw if invite is not None else "",
            }
            if invite is not None:
                invite["used_by"] = user or user_id
            name = share["name"]
            description = share["description"]
            self._save()
        owner = self._identity()["name"] or "Jon-Nutzer"
        return {
            "token": token,
            "grant_id": grant_id,
            "name": name or f"Ollama von {owner}",
            "description": description,
            "owner": owner,
            "model": self.shared_model(),
        }

    def authorize(self, token: str) -> dict:
        candidate = str(token or "").strip()
        if not candidate:
            raise ShareError("Kein Zugriffstoken übermittelt.")
        digest = hash_token(candidate)
        with self._lock:
            if not self._data["share"]["enabled"]:
                raise ShareError("Die Freigabe wurde deaktiviert.")
            for grant in self._data["grants"].values():
                if hmac.compare_digest(str(grant["token_hash"]), digest):
                    return dict(grant)
        raise ShareError("Zugriff widerrufen oder Token ungültig.")

    def touch(self, grant_id: str, model: str = "", delta: int = 0) -> None:
        with self._lock:
            grant = self._data["grants"].get(grant_id)
            if grant is None:
                return
            grant["last_seen"] = _now()
            if model:
                grant["model"] = model
            if delta > 0:
                grant["requests"] = int(grant.get("requests") or 0) + 1
            self._save()
        session = self._sessions.setdefault(grant_id, {"active": 0, "model": "", "at": 0.0})
        session["at"] = _now()
        if model:
            session["model"] = model
        session["active"] = max(0, int(session["active"]) + delta)

    @staticmethod
    def sanitize_payload(payload: Any) -> dict:
        from app.services.ollama_service import get_ollama_service

        if not isinstance(payload, dict):
            raise ShareError("Ungültige Anfrage.")
        model = str(payload.get("model", "")).strip()
        if not model:
            raise ShareError("Kein Modell angegeben.")
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise ShareError("Keine Nachrichten angegeben.")
        owner = get_ollama_service().config()
        options: dict[str, Any] = {}
        raw = payload.get("options")
        if isinstance(raw, dict):
            for key in ("temperature", "top_p", "top_k", "seed", "stop", "num_predict"):
                if key in raw:
                    options[key] = raw[key]
        limit = int(owner["context_length"])
        wanted = options.pop("num_ctx", None)
        try:
            options["num_ctx"] = min(int(wanted), limit) if wanted else limit
        except (TypeError, ValueError):
            options["num_ctx"] = limit
        cap = int(owner["max_tokens"])
        if cap > 0:
            try:
                predict = int(options.get("num_predict", cap))
            except (TypeError, ValueError):
                predict = cap
            options["num_predict"] = cap if predict < 0 else min(predict, cap)
        clean: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": bool(payload.get("stream", True)),
            "keep_alive": owner["keep_alive"],
            "options": options,
        }
        tools = payload.get("tools")
        if isinstance(tools, list) and tools:
            clean["tools"] = tools
        return clean

    def alive(self, grant_id: str) -> bool:
        with self._lock:
            return (
                bool(self._data["share"]["enabled"])
                and grant_id in self._data["grants"]
            )

    def remotes(self) -> list[dict]:
        with self._lock:
            items = [dict(item) for item in self._data["remotes"].values()]
        for item in items:
            item.pop("token", None)
        items.sort(key=lambda entry: entry.get("added_at", ""))
        return items

    def remote(self, code: str) -> dict | None:
        with self._lock:
            entry = self._data["remotes"].get(str(code).upper())
            return dict(entry) if entry else None

    def remote_models(self) -> list[str]:
        found: list[str] = []
        with self._lock:
            for entry in self._data["remotes"].values():
                for model in entry.get("models", []):
                    found.append(f"{REMOTE_PREFIX}{entry['code']}/{model}")
        return found

    def store_remote(self, entry: dict) -> dict:
        with self._lock:
            self._data["remotes"][entry["code"]] = entry
            self._save()
        result = dict(entry)
        result.pop("token", None)
        return result

    def forget_remote(self, code: str) -> bool:
        with self._lock:
            existed = self._data["remotes"].pop(str(code).upper(), None) is not None
            if existed:
                self._save()
        return existed

    def update_remote(self, code: str, values: dict) -> None:
        with self._lock:
            entry = self._data["remotes"].get(str(code).upper())
            if entry is None:
                return
            entry.update(values)
            self._save()

    def split_model(self, model: str) -> tuple[dict | None, str]:
        if not model.startswith(REMOTE_PREFIX):
            return None, model
        rest = model[len(REMOTE_PREFIX):]
        code, _, name = rest.partition("/")
        entry = self.remote(code.upper())
        return entry, name

    async def discover(self, code: str, timeout: float = 2.0) -> dict | None:
        from app.services.coop_lan_service import broadcast_targets

        loop = asyncio.get_running_loop()
        answer: asyncio.Future = loop.create_future()
        wanted = code.upper()

        class Protocol(asyncio.DatagramProtocol):
            def datagram_received(self, data: bytes, addr) -> None:
                try:
                    payload = json.loads(data.decode("utf-8"))
                except Exception:
                    return
                if payload.get("magic") != MAGIC or payload.get("q"):
                    return
                if str(payload.get("code", "")).upper() != wanted:
                    return
                if not answer.done():
                    payload["host"] = payload.get("host") or addr[0]
                    answer.set_result(payload)

        transport, _ = await loop.create_datagram_endpoint(
            Protocol, local_addr=("0.0.0.0", 0), allow_broadcast=True
        )
        try:
            message = json.dumps({"magic": MAGIC, "q": wanted}).encode("utf-8")
            for target in broadcast_targets():
                try:
                    transport.sendto(message, (target, DISCOVERY_PORT))
                except Exception:
                    continue
            try:
                return await asyncio.wait_for(answer, timeout=timeout)
            except asyncio.TimeoutError:
                return None
        finally:
            transport.close()

    def answer_query(self, wanted: str) -> dict | None:
        with self._lock:
            share = self._data["share"]
            if not share["enabled"] or share["visibility"] == "private":
                return None
            invite = self._data["invites"].get(wanted)
            known = hmac.compare_digest(wanted, str(share["code"])) or (
                invite is not None and not invite.get("used_by")
            )
            if not known:
                return None
            name = share["name"]
            visibility = share["visibility"]
        return {
            "magic": MAGIC,
            "code": wanted,
            "host": "",
            "port": self._port(),
            "name": name or f"Ollama von {self._identity()['name']}",
            "visibility": visibility,
        }

    async def serve_discovery(self) -> None:
        from app.services.coop_lan_service import address_for_peer

        loop = asyncio.get_running_loop()
        service = self

        class Protocol(asyncio.DatagramProtocol):
            def connection_made(self, transport) -> None:
                self.transport = transport

            def datagram_received(self, data: bytes, addr) -> None:
                try:
                    payload = json.loads(data.decode("utf-8"))
                except Exception:
                    return
                if payload.get("magic") != MAGIC:
                    return
                wanted = str(payload.get("q", "")).upper()
                if not wanted:
                    return
                reply = service.answer_query(wanted)
                if reply is None:
                    return
                reply["host"] = address_for_peer(addr[0])
                try:
                    self.transport.sendto(json.dumps(reply).encode("utf-8"), addr)
                except Exception:
                    return

        transport, _ = await loop.create_datagram_endpoint(
            Protocol, local_addr=("0.0.0.0", DISCOVERY_PORT), allow_broadcast=True
        )
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            transport.close()

    async def connect(self, raw: str, timeout: float = 8.0) -> dict:
        code, host, port = parse_invite(raw)
        if not host:
            found = await self.discover(code)
            if not found:
                raise ShareError(
                    "Kein Server mit diesem Code im Netzwerk gefunden. Nutze den "
                    "Einladungslink mit Adresse, zum Beispiel "
                    f"{code}@192.168.1.50:8758."
                )
            host = str(found.get("host", ""))
            port = int(found.get("port") or 0)
        port = port or self._port()
        me = self._identity()
        base = f"http://{host}:{port}"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    base + "/share/join",
                    json={"code": code, "name": me["name"], "user_id": me["id"]},
                )
                if response.status_code >= 400:
                    raise ShareError(_detail(response))
                data = response.json()
                models, shared = await _remote_models(client, base, data["token"])
        except ShareError:
            raise
        except httpx.HTTPError as exc:
            raise ShareError(
                f"Der Server unter {base} ist nicht erreichbar: {exc}"
            ) from exc
        entry = {
            "code": code,
            "host": host,
            "port": port,
            "base": base,
            "token": data["token"],
            "grant_id": data.get("grant_id", ""),
            "name": data.get("name", "") or f"Ollama {code}",
            "description": data.get("description", ""),
            "owner": data.get("owner", ""),
            "added_at": _stamp(),
            "last_ok": _stamp(),
            "models": models,
            "model": str(data.get("model") or shared or (models[0] if models else "")),
            "error": "",
        }
        return self.store_remote(entry)

    async def refresh_remote(self, code: str) -> dict:
        entry = self.remote(code)
        if entry is None:
            raise ShareError("Dieser Server ist nicht verbunden.")
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                models, shared = await _remote_models(
                    client, entry["base"], entry["token"]
                )
        except ShareError as exc:
            self.update_remote(code, {"error": str(exc)})
            raise
        except httpx.HTTPError as exc:
            message = f"{entry['base']} ist nicht erreichbar."
            self.update_remote(code, {"error": message})
            raise ShareError(message) from exc
        values = {"models": models, "last_ok": _stamp(), "error": ""}
        if shared:
            values["model"] = shared
        self.update_remote(code, values)
        return self.remote(code) or {}

    async def remote_status(self, code: str) -> dict:
        entry = self.remote(code)
        if entry is None:
            raise ShareError("Dieser Server ist nicht verbunden.")
        started = time.perf_counter()
        state = "offline"
        error = ""
        models: list[str] = list(entry.get("models", []))
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                models, shared = await _remote_models(
                    client, entry["base"], entry["token"]
                )
            state = "online"
            values = {"models": models, "last_ok": _stamp(), "error": ""}
            if shared:
                values["model"] = shared
            self.update_remote(code, values)
        except ShareError as exc:
            error = str(exc)
            self.update_remote(code, {"error": error})
        except httpx.HTTPError:
            error = f"{entry['base']} ist nicht erreichbar."
            self.update_remote(code, {"error": error})
        return {
            "code": entry["code"],
            "name": entry["name"],
            "owner": entry.get("owner", ""),
            "base": entry["base"],
            "state": state,
            "response_ms": int((time.perf_counter() - started) * 1000),
            "models": models,
            "model_count": len(models),
            "error": error,
            "last_ok": (self.remote(code) or {}).get("last_ok", ""),
        }


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return response.text.strip()[:200] or f"Fehler {response.status_code}"
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])[:200]
    return str(payload)[:200]


async def _remote_models(
    client: httpx.AsyncClient, base: str, token: str
) -> tuple[list[str], str]:
    response = await client.get(
        base + "/share/api/tags", headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code >= 400:
        raise ShareError(_detail(response))
    data = response.json()
    items = data.get("models", []) if isinstance(data, dict) else []
    names = [
        str(item.get("name") or item.get("model") or "").strip()
        for item in items
        if isinstance(item, dict)
    ]
    shared = str(data.get("model", "")).strip() if isinstance(data, dict) else ""
    return sorted(name for name in names if name), shared


_service: OllamaShareService | None = None


def get_share_service() -> OllamaShareService:
    global _service
    if _service is None:
        _service = OllamaShareService()
    return _service
