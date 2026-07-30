from __future__ import annotations

import asyncio
import json
import math
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import DATA_DIR

MP_DIR = DATA_DIR / "multiplayer"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
TICK_HZ = 20.0
TICK_DT = 1.0 / TICK_HZ
SNAPSHOT_HISTORY = 48
PING_INTERVAL = 1.0
CLIENT_TIMEOUT = 15.0
RECONNECT_GRACE = 150.0
LOBBY_TTL = 6 * 3600.0
EVENT_HISTORY = 512
MAX_PLAYERS = 8
MAX_VIOLATIONS = 40
PROTOCOL_VERSION = 1

WORLD_KEY = re.compile(r"^[a-z]{1,12}:[A-Za-z0-9_.,\-]{1,48}$")
NAME_CLEAN = re.compile(r"[^\wÄÖÜäöüß .\-]")

PLAYER_FIELDS = (
    "x", "y", "z", "yaw", "pitch", "vx", "vy", "vz",
    "anim", "flags", "emote", "face", "layer", "hp", "scene", "act",
)


@dataclass
class GameProfile:
    max_speed: float = 12.0
    max_fall: float = 90.0
    world_radius: float = 100000.0
    height_min: float = -256.0
    height_max: float = 4096.0
    edit_range: float = 9.0
    interact_range: float = 12.0
    edits_per_second: float = 40.0
    acts_per_second: float = 60.0
    block_ids: tuple[int, ...] = tuple(range(0, 64))


GAMES: dict[str, GameProfile] = {
    "blockwelt": GameProfile(
        max_speed=14.0,
        world_radius=40000.0,
        height_min=-8.0,
        height_max=140.0,
        edit_range=9.0,
        block_ids=tuple(range(0, 24)),
    ),
    "aetheria": GameProfile(
        max_speed=16.0,
        world_radius=6000.0,
        height_min=-64.0,
        height_max=1024.0,
        edit_range=6.0,
        interact_range=14.0,
        edits_per_second=8.0,
    ),
    "echo": GameProfile(
        max_speed=11.0,
        world_radius=2000.0,
        height_min=-64.0,
        height_max=512.0,
        edit_range=4.0,
        interact_range=6.0,
        edits_per_second=8.0,
    ),
}

ACT_KINDS = {
    "block", "blocks", "door", "lever", "switch", "puzzle", "item", "npc",
    "quest", "light", "timer", "physics", "harvest", "strike", "checkpoint",
    "teleport", "explode", "signal",
}

FX_KINDS = {
    "pearl", "swing", "hit", "step", "particle", "sound", "spark", "voice",
}

MAX_BATCH_CELLS = 768

SHARED_PREFIX = {
    "block": "b",
    "door": "door",
    "lever": "lever",
    "switch": "sw",
    "puzzle": "puz",
    "item": "item",
    "npc": "npc",
    "quest": "quest",
    "light": "light",
    "timer": "timer",
    "physics": "phys",
    "harvest": "flora",
    "signal": "sig",
}


def _now() -> float:
    return time.monotonic()


def _clean_name(raw: Any, fallback: str) -> str:
    text = NAME_CLEAN.sub("", str(raw or "")).strip()
    return text[:20] or fallback


def _num(raw: Any, default: float = 0.0) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return value


def _int(raw: Any, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _diff(old: dict, new: dict) -> dict:
    out: dict[str, Any] = {}
    for key, value in new.items():
        if old.get(key) != value:
            out[key] = value
    return out


def _diff_nested(old: dict, new: dict) -> tuple[dict, list[str]]:
    changed: dict[str, Any] = {}
    for key, value in new.items():
        previous = old.get(key)
        if previous is None:
            changed[key] = value
            continue
        partial = _diff(previous, value)
        if partial:
            changed[key] = partial
    removed = [key for key in old if key not in new]
    return changed, removed


class Bucket:
    def __init__(self, rate: float, burst: float | None = None) -> None:
        self.rate = rate
        self.capacity = burst if burst is not None else rate * 2.0
        self.tokens = self.capacity
        self.stamp = _now()

    def take(self, amount: float = 1.0) -> bool:
        now = _now()
        self.tokens = min(self.capacity, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens < amount:
            return False
        self.tokens -= amount
        return True


class Transport:
    redirected: bool = False

    async def send(self, payload: dict) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class WebSocketTransport(Transport):
    def __init__(self, socket: Any) -> None:
        self._socket = socket

    async def send(self, payload: dict) -> None:
        await self._socket.send_text(json.dumps(payload, separators=(",", ":")))

    async def close(self) -> None:
        try:
            await self._socket.close()
        except Exception:
            pass


class StreamTransport(Transport):
    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self._writer = writer
        self._lock = asyncio.Lock()

    async def send(self, payload: dict) -> None:
        blob = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        async with self._lock:
            self._writer.write(len(blob).to_bytes(4, "big") + blob)
            await self._writer.drain()

    async def close(self) -> None:
        try:
            self._writer.close()
        except Exception:
            pass


@dataclass
class Participant:
    player_id: str
    token: str
    name: str
    model: str = "default"
    host: bool = False
    slot: int = 0
    ready: bool = False
    online: bool = False
    loaded: bool = False
    transport: Transport | None = None
    state: dict[str, Any] = field(default_factory=dict)
    history: list[tuple[float, dict]] = field(default_factory=list)
    inventory: dict[str, int] = field(default_factory=dict)
    spawn: dict[str, float] = field(default_factory=dict)
    scene: str = "lobby"
    last_seen: float = field(default_factory=_now)
    last_input: float = 0.0
    dropped_at: float = 0.0
    ping: float = 0.0
    jitter: float = 0.0
    loss: float = 0.0
    ack: int = 0
    event_cursor: int = 0
    snapshots_sent: int = 0
    snapshots_acked: int = 0
    violations: int = 0
    edit_bucket: Bucket = field(default_factory=lambda: Bucket(40.0))
    act_bucket: Bucket = field(default_factory=lambda: Bucket(60.0))
    chat_bucket: Bucket = field(default_factory=lambda: Bucket(2.0, 6.0))
    pending_ping: dict[int, float] = field(default_factory=dict)
    ping_seq: int = 0

    def public(self) -> dict:
        return {
            "id": self.player_id,
            "name": self.name,
            "model": self.model,
            "host": self.host,
            "slot": self.slot,
            "ready": self.ready,
            "online": self.online,
            "loaded": self.loaded,
            "ping": round(self.ping),
            "loss": round(self.loss, 1),
            "scene": self.scene,
        }

    def net_state(self) -> dict:
        merged = {key: self.state.get(key, 0) for key in PLAYER_FIELDS}
        merged["ping"] = round(self.ping)
        merged["online"] = 1 if self.online else 0
        merged["name"] = self.name
        merged["model"] = self.model
        return merged

    def rewind(self, target: float) -> dict:
        if not self.history:
            return dict(self.state)
        best = self.history[0]
        for entry in self.history:
            if entry[0] <= target:
                best = entry
            else:
                break
        return best[1]

    def store(self) -> dict:
        return {
            "player_id": self.player_id,
            "token": self.token,
            "name": self.name,
            "model": self.model,
            "host": self.host,
            "slot": self.slot,
            "inventory": self.inventory,
            "spawn": self.spawn,
            "scene": self.scene,
            "state": self.state,
        }


@dataclass
class Lobby:
    code: str
    game: str
    seed: int
    profile: GameProfile
    owner: str = ""
    phase: str = "lobby"
    scene: str = "world"
    tick: int = 0
    created: float = field(default_factory=_now)
    touched: float = field(default_factory=_now)
    max_players: int = 2
    private: bool = True
    base_spawn: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    participants: dict[str, Participant] = field(default_factory=dict)
    world: dict[str, Any] = field(default_factory=dict)
    save: dict[str, Any] = field(default_factory=dict)
    snapshots: list[tuple[int, dict]] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    snapshot_id: int = 0
    event_id: int = 0
    dirty: bool = False
    started_at: float = 0.0

    def host(self) -> Participant | None:
        for member in self.participants.values():
            if member.host:
                return member
        return None

    def online_members(self) -> list[Participant]:
        return [m for m in self.participants.values() if m.online]

    def ordered(self) -> list[Participant]:
        return sorted(self.participants.values(), key=lambda m: m.slot)

    def free_slot(self) -> int:
        used = {m.slot for m in self.participants.values()}
        slot = 0
        while slot in used:
            slot += 1
        return slot

    def summary(self) -> dict:
        return {
            "code": self.code,
            "game": self.game,
            "seed": self.seed,
            "phase": self.phase,
            "scene": self.scene,
            "tick": self.tick,
            "max_players": self.max_players,
            "owner": self.owner,
            "players": [m.public() for m in self.ordered()],
            "spawn": self.base_spawn,
            "ready": all(m.ready or m.host for m in self.participants.values()),
        }

    def full_state(self) -> dict:
        return {
            "players": {m.player_id: m.net_state() for m in self.ordered()},
            "world": dict(self.world),
            "phase": self.phase,
            "scene": self.scene,
        }

    def store(self) -> dict:
        return {
            "code": self.code,
            "game": self.game,
            "seed": self.seed,
            "owner": self.owner,
            "phase": self.phase,
            "scene": self.scene,
            "max_players": self.max_players,
            "base_spawn": self.base_spawn,
            "world": self.world,
            "save": self.save,
            "created": time.time(),
            "participants": [m.store() for m in self.ordered()],
        }


class MultiplayerService:
    def __init__(self) -> None:
        self._lobbies: dict[str, Lobby] = {}
        self._tokens: dict[str, tuple[str, str]] = {}
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._server: asyncio.AbstractServer | None = None
        self._stats = {"created": 0, "joins": 0, "snapshots": 0, "kicks": 0}
        self._load()

    # ------------------------------------------------------------------ setup

    def _load(self) -> None:
        if not MP_DIR.is_dir():
            return
        cutoff = time.time() - LOBBY_TTL
        for path in MP_DIR.glob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if float(raw.get("created", 0)) < cutoff:
                path.unlink(missing_ok=True)
                continue
            lobby = self._restore(raw)
            if lobby is not None:
                self._lobbies[lobby.code] = lobby

    def _restore(self, raw: dict) -> Lobby | None:
        code = str(raw.get("code", "")).upper()
        game = str(raw.get("game", "blockwelt"))
        if len(code) != CODE_LENGTH or game not in GAMES:
            return None
        lobby = Lobby(
            code=code,
            game=game,
            seed=_int(raw.get("seed"), 0),
            profile=GAMES[game],
            owner=str(raw.get("owner", "")),
            phase="lobby",
            scene=str(raw.get("scene", "world")),
            max_players=max(2, min(MAX_PLAYERS, _int(raw.get("max_players"), 2))),
            base_spawn=dict(raw.get("base_spawn") or {}),
            world=dict(raw.get("world") or {}),
            save=dict(raw.get("save") or {}),
        )
        for entry in raw.get("participants") or []:
            member = Participant(
                player_id=str(entry.get("player_id", "")),
                token=str(entry.get("token", "")),
                name=_clean_name(entry.get("name"), "Spieler"),
                model=str(entry.get("model", "default")),
                host=bool(entry.get("host")),
                slot=_int(entry.get("slot"), 0),
            )
            if not member.player_id or not member.token:
                continue
            member.inventory = dict(entry.get("inventory") or {})
            member.spawn = dict(entry.get("spawn") or {})
            member.scene = str(entry.get("scene", "world"))
            member.state = dict(entry.get("state") or {})
            member.dropped_at = _now()
            lobby.participants[member.player_id] = member
            self._tokens[member.token] = (code, member.player_id)
        if not lobby.participants:
            return None
        return lobby

    def _persist(self, lobby: Lobby) -> None:
        try:
            MP_DIR.mkdir(parents=True, exist_ok=True)
            path = MP_DIR / f"{lobby.code}.json"
            path.write_text(
                json.dumps(lobby.store(), ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _forget(self, lobby: Lobby) -> None:
        for member in lobby.participants.values():
            self._tokens.pop(member.token, None)
        self._lobbies.pop(lobby.code, None)
        try:
            (MP_DIR / f"{lobby.code}.json").unlink(missing_ok=True)
        except Exception:
            pass

    def status(self) -> dict:
        return {
            "protocol": PROTOCOL_VERSION,
            "tick_rate": TICK_HZ,
            "games": sorted(GAMES),
            "lobbies": len(self._lobbies),
            "players": sum(len(l.participants) for l in self._lobbies.values()),
            "online": sum(len(l.online_members()) for l in self._lobbies.values()),
            "stats": dict(self._stats),
        }

    def lobby_info(self, code: str) -> dict | None:
        lobby = self._lobbies.get(str(code or "").upper().strip())
        if lobby is None:
            return None
        return lobby.summary()

    @staticmethod
    def _beacon_entry(lobby: Lobby) -> dict:
        host = lobby.host()
        return {
            "code": lobby.code,
            "game": lobby.game,
            "phase": lobby.phase,
            "players": len(lobby.participants),
            "max_players": lobby.max_players,
            "host_name": host.name if host is not None else "",
            "free": max(0, lobby.max_players - len(lobby.participants)),
        }

    def beacon_lookup(self, code: str) -> dict | None:
        lobby = self._lobbies.get(str(code or "").upper().strip())
        if lobby is None or lobby.phase == "ended":
            return None
        return self._beacon_entry(lobby)

    def beacon_list(self) -> list[dict]:
        entries = []
        for lobby in self._lobbies.values():
            if lobby.phase == "ended" or not lobby.participants:
                continue
            if len(lobby.participants) >= lobby.max_players:
                continue
            entries.append(self._beacon_entry(lobby))
        return entries

    def knows_code(self, code: str) -> bool:
        return str(code or "").upper().strip() in self._lobbies

    def invite_info(self, code: str) -> dict:
        from app.services.coop_lan_service import get_coop_beacon, invite_host, local_addresses

        beacon = get_coop_beacon()
        host = invite_host()
        return {
            "invite": f"{str(code or '').upper()}@{host}:{beacon.ws_port}",
            "invite_tcp": f"{str(code or '').upper()}@{host}:{beacon.tcp_port}",
            "invite_host": host,
            "addresses": local_addresses(),
            "tcp_port": beacon.tcp_port,
            "ws_port": beacon.ws_port,
            "discovery": beacon.online,
            "findable": beacon.findable,
        }

    async def find_remote(self, code: str, timeout: float = 1.8) -> dict | None:
        from app.services.coop_lan_service import get_coop_beacon

        if self.knows_code(code):
            return None
        try:
            return await get_coop_beacon().find(code, timeout)
        except Exception:
            return None

    async def scan_remote(self, timeout: float = 1.4) -> list[dict]:
        from app.services.coop_lan_service import get_coop_beacon

        try:
            return await get_coop_beacon().scan(timeout)
        except Exception:
            return []

    # ------------------------------------------------------------- lobby core

    def _new_code(self) -> str:
        for _ in range(64):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._lobbies:
                return code
        return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH + 2))

    def _spawn_for(self, lobby: Lobby, slot: int) -> dict[str, float]:
        base = lobby.base_spawn or {"x": 0.0, "y": 0.0, "z": 0.0}
        if slot == 0:
            return {"x": _num(base.get("x")), "y": _num(base.get("y")), "z": _num(base.get("z")), "yaw": 0.0}
        angle = (slot - 1) * (2.0 * math.pi / max(1, lobby.max_players - 1))
        radius = 2.5 + slot * 0.4
        return {
            "x": _num(base.get("x")) + math.cos(angle) * radius,
            "y": _num(base.get("y")),
            "z": _num(base.get("z")) + math.sin(angle) * radius,
            "yaw": -angle,
        }

    def create_lobby(
        self,
        game: str,
        name: str,
        model: str = "default",
        seed: int | None = None,
        max_players: int = 2,
        spawn: dict | None = None,
    ) -> tuple[Lobby, Participant]:
        profile = GAMES.get(game)
        if profile is None:
            raise ValueError("unbekanntes Spiel")
        lobby = Lobby(
            code=self._new_code(),
            game=game,
            seed=_int(seed, secrets.randbelow(2**31)) or secrets.randbelow(2**31),
            profile=profile,
            max_players=max(2, min(MAX_PLAYERS, _int(max_players, 2))),
        )
        if spawn:
            lobby.base_spawn = {
                "x": _num(spawn.get("x")),
                "y": _num(spawn.get("y")),
                "z": _num(spawn.get("z")),
            }
        member = self._add_participant(lobby, name, model, host=True)
        lobby.owner = member.player_id
        self._lobbies[lobby.code] = lobby
        self._stats["created"] += 1
        self._persist(lobby)
        return lobby, member

    def _add_participant(
        self, lobby: Lobby, name: str, model: str, host: bool = False
    ) -> Participant:
        slot = lobby.free_slot()
        member = Participant(
            player_id=secrets.token_hex(6),
            token=secrets.token_urlsafe(24),
            name=_clean_name(name, f"Spieler {slot + 1}"),
            model=str(model or "default")[:24],
            host=host,
            slot=slot,
        )
        member.edit_bucket = Bucket(lobby.profile.edits_per_second)
        member.act_bucket = Bucket(lobby.profile.acts_per_second)
        member.spawn = self._spawn_for(lobby, slot)
        member.state = {key: 0 for key in PLAYER_FIELDS}
        member.state.update(
            {
                "x": member.spawn["x"],
                "y": member.spawn["y"],
                "z": member.spawn["z"],
                "yaw": member.spawn.get("yaw", 0.0),
                "anim": "idle",
                "hp": 100,
                "scene": lobby.scene,
            }
        )
        member.scene = lobby.scene
        lobby.participants[member.player_id] = member
        self._tokens[member.token] = (lobby.code, member.player_id)
        return member

    def join_lobby(
        self, code: str, name: str, model: str = "default"
    ) -> tuple[Lobby, Participant]:
        lobby = self._lobbies.get(str(code or "").upper().strip())
        if lobby is None:
            raise ValueError("Code nicht gefunden")
        if len(lobby.participants) >= lobby.max_players:
            raise ValueError("Lobby ist voll")
        if lobby.phase == "ended":
            raise ValueError("Lobby wurde geschlossen")
        member = self._add_participant(lobby, name, model)
        lobby.touched = _now()
        self._stats["joins"] += 1
        self._persist(lobby)
        return lobby, member

    def resume(self, token: str) -> tuple[Lobby, Participant] | None:
        entry = self._tokens.get(str(token or ""))
        if entry is None:
            return None
        lobby = self._lobbies.get(entry[0])
        if lobby is None:
            return None
        member = lobby.participants.get(entry[1])
        if member is None:
            return None
        return lobby, member

    # ---------------------------------------------------------------- sending

    async def _deliver(self, member: Participant, payload: dict) -> None:
        transport = member.transport
        if transport is None:
            return
        try:
            await transport.send(payload)
        except Exception:
            member.online = False
            member.transport = None
            member.dropped_at = _now()

    async def _broadcast(self, lobby: Lobby, payload: dict, skip: str = "") -> None:
        targets = [m for m in lobby.online_members() if m.player_id != skip]
        if not targets:
            return
        await asyncio.gather(*(self._deliver(m, payload) for m in targets))

    async def _push_lobby(self, lobby: Lobby) -> None:
        await self._broadcast(lobby, {"t": "lobby", "lobby": lobby.summary()})

    def _emit(self, lobby: Lobby, kind: str, body: dict | None = None) -> None:
        lobby.event_id += 1
        event = {"eid": lobby.event_id, "kind": kind}
        if body:
            event.update(body)
        lobby.events.append(event)
        if len(lobby.events) > EVENT_HISTORY:
            del lobby.events[: len(lobby.events) - EVENT_HISTORY]

    # ------------------------------------------------------------- connection

    def _resume_spawn(self, member: Participant) -> dict[str, float]:
        state = member.state or {}
        return {
            "x": _num(state.get("x")),
            "y": _num(state.get("y")),
            "z": _num(state.get("z")),
            "yaw": _num(state.get("yaw")),
        }

    async def attach(
        self, lobby: Lobby, member: Participant, transport: Transport
    ) -> None:
        if member.transport is not None and member.transport is not transport:
            await member.transport.close()
        member.transport = transport
        member.online = True
        member.last_seen = _now()
        member.dropped_at = 0.0
        member.ack = 0
        member.last_input = 0.0
        member.event_cursor = max(0, lobby.event_id - 32)
        lobby.touched = _now()
        if lobby.phase in ("playing", "paused"):
            member.loaded = False
            member.spawn = self._resume_spawn(member)
        await self._deliver(
            member,
            {
                "t": "welcome",
                "protocol": PROTOCOL_VERSION,
                "player_id": member.player_id,
                "token": member.token,
                "tick_rate": TICK_HZ,
                "you": member.public(),
                "spawn": member.spawn,
                "lobby": lobby.summary(),
                "state": lobby.full_state(),
                "save": lobby.save,
                **self.invite_info(lobby.code),
            },
        )
        self._emit(lobby, "presence", {"id": member.player_id, "online": True})
        await self._push_lobby(lobby)

    async def detach(self, lobby: Lobby, member: Participant) -> None:
        member.online = False
        member.transport = None
        member.ready = False
        member.dropped_at = _now()
        self._emit(lobby, "presence", {"id": member.player_id, "online": False})
        await self._push_lobby(lobby)
        self._persist(lobby)

    # ------------------------------------------------------------- validation

    def _accept_move(self, lobby: Lobby, member: Participant, body: dict) -> bool:
        profile = lobby.profile
        now = _now()
        x = _num(body.get("x"), member.state.get("x", 0.0))
        y = _num(body.get("y"), member.state.get("y", 0.0))
        z = _num(body.get("z"), member.state.get("z", 0.0))
        if abs(x) > profile.world_radius or abs(z) > profile.world_radius:
            return False
        if y < profile.height_min or y > profile.height_max:
            return False
        previous = member.state
        elapsed = now - member.last_input if member.last_input else TICK_DT
        member.last_input = now
        if lobby.phase == "playing":
            span = min(2.0, max(elapsed, TICK_DT))
            dx = x - _num(previous.get("x"))
            dz = z - _num(previous.get("z"))
            dy = y - _num(previous.get("y"))
            allowed = profile.max_speed * span * 1.8 + 1.5
            drop = profile.max_fall * span * 1.8 + 2.0
            if math.hypot(dx, dz) > allowed or abs(dy) > max(allowed, drop):
                member.violations += 1
                return False
        member.violations = max(0, member.violations - 1)
        member.state.update(
            {
                "x": x,
                "y": y,
                "z": z,
                "yaw": _num(body.get("yaw"), 0.0),
                "pitch": _num(body.get("pitch"), 0.0),
                "vx": _num(body.get("vx"), 0.0),
                "vy": _num(body.get("vy"), 0.0),
                "vz": _num(body.get("vz"), 0.0),
                "anim": str(body.get("anim", "idle"))[:16],
                "flags": _int(body.get("flags"), 0),
            }
        )
        for field, limit in (("emote", 64), ("face", 64), ("layer", 8), ("act", 64)):
            if field in body:
                member.state[field] = max(0, min(limit, _int(body.get(field))))
        if "hp" in body:
            member.state["hp"] = max(0, min(9999, _int(body.get("hp"), 100)))
        member.history.append((now, dict(member.state)))
        if len(member.history) > 40:
            del member.history[: len(member.history) - 40]
        return True

    def _in_range(self, member: Participant, body: dict, limit: float) -> bool:
        if "x" not in body and "px" not in body:
            return True
        tx = _num(body.get("x", body.get("px")))
        ty = _num(body.get("y", body.get("py")))
        tz = _num(body.get("z", body.get("pz")))
        state = member.state
        dist = math.dist(
            (tx, ty, tz),
            (_num(state.get("x")), _num(state.get("y")), _num(state.get("z"))),
        )
        return dist <= limit

    def _apply_act(self, lobby: Lobby, member: Participant, body: dict) -> bool:
        kind = str(body.get("kind", ""))
        if kind not in ACT_KINDS:
            return False
        if not member.act_bucket.take():
            return False
        profile = lobby.profile

        if kind == "block":
            if not member.edit_bucket.take():
                return False
            bx, by, bz = _int(body.get("x")), _int(body.get("y")), _int(body.get("z"))
            block = _int(body.get("id"))
            if block not in profile.block_ids:
                return False
            if by < 1 or by >= int(profile.height_max):
                return False
            if not self._in_range(member, body, profile.edit_range):
                member.violations += 1
                return False
            key = f"b:{bx},{by},{bz}"
            if lobby.world.get(key) == block:
                return False
            lobby.world[key] = block
            lobby.dirty = True
            return True

        if kind == "blocks":
            cells = body.get("cells")
            if not isinstance(cells, list) or not cells:
                return False
            if len(cells) > MAX_BATCH_CELLS:
                return False
            if not member.edit_bucket.take(max(1.0, len(cells) / 32.0)):
                return False
            if not self._in_range(member, body, profile.edit_range * 12.0):
                member.violations += 1
                return False
            applied = 0
            for cell in cells:
                if not isinstance(cell, (list, tuple)) or len(cell) < 4:
                    continue
                bx, by, bz = _int(cell[0]), _int(cell[1]), _int(cell[2])
                block = _int(cell[3])
                if by < 1 or by >= int(profile.height_max):
                    continue
                if block not in profile.block_ids:
                    continue
                key = f"b:{bx},{by},{bz}"
                if lobby.world.get(key) == block:
                    continue
                lobby.world[key] = block
                applied += 1
            if applied:
                lobby.dirty = True
            return applied > 0

        if kind == "explode":
            if not self._in_range(member, body, profile.interact_range * 4.0):
                return False
            cells = body.get("cells")
            if not isinstance(cells, list) or len(cells) > 4096:
                return False
            for cell in cells:
                if not isinstance(cell, (list, tuple)) or len(cell) < 3:
                    continue
                key = f"b:{_int(cell[0])},{_int(cell[1])},{_int(cell[2])}"
                lobby.world[key] = 0
            lobby.dirty = True
            self._emit(
                lobby,
                "explode",
                {
                    "x": _num(body.get("x")),
                    "y": _num(body.get("y")),
                    "z": _num(body.get("z")),
                    "by": member.player_id,
                },
            )
            return True

        if kind == "teleport":
            distance = _num(body.get("distance"), 0.0)
            if distance > 128.0:
                return False
            member.state.update(
                {
                    "x": _num(body.get("x")),
                    "y": _num(body.get("y")),
                    "z": _num(body.get("z")),
                }
            )
            member.last_input = 0.0
            self._emit(
                lobby,
                "teleport",
                {"id": member.player_id, "x": member.state["x"], "y": member.state["y"], "z": member.state["z"]},
            )
            return True

        if kind == "strike":
            target = str(body.get("target", ""))[:48]
            if not target:
                return False
            when = _num(body.get("at"), 0.0)
            lag = min(0.5, max(0.0, member.ping / 1000.0))
            snapshot = member.rewind(_now() - lag) if when else member.state
            key = f"mob:{target}"
            entry = lobby.world.get(key)
            health = _num(entry.get("hp") if isinstance(entry, dict) else entry, 100.0)
            health -= max(0.0, min(200.0, _num(body.get("damage"), 0.0)))
            record = {"hp": max(0.0, health), "alive": health > 0.0}
            lobby.world[key] = record
            lobby.dirty = True
            self._emit(
                lobby,
                "strike",
                {
                    "by": member.player_id,
                    "target": target,
                    "hp": record["hp"],
                    "killed": not record["alive"],
                    "x": _num(snapshot.get("x")),
                    "z": _num(snapshot.get("z")),
                },
            )
            return True

        if kind == "checkpoint":
            payload = body.get("data")
            if not isinstance(payload, dict) or len(json.dumps(payload)) > 200_000:
                return False
            lobby.save.update(payload)
            lobby.save["by"] = member.player_id
            lobby.save["tick"] = lobby.tick
            lobby.dirty = True
            self._emit(lobby, "save", {"by": member.player_id})
            self._persist(lobby)
            return True

        prefix = SHARED_PREFIX.get(kind)
        if prefix is None:
            return False
        ident = str(body.get("id", ""))[:48]
        if not ident or not WORLD_KEY.match(f"{prefix}:{ident}"):
            return False
        limit = profile.interact_range if kind != "harvest" else profile.edit_range
        if not self._in_range(member, body, limit):
            member.violations += 1
            return False
        value = body.get("value", 1)
        if isinstance(value, (dict, list)):
            if len(json.dumps(value)) > 8_000:
                return False
        elif isinstance(value, str):
            value = value[:120]
        elif isinstance(value, bool):
            value = bool(value)
        else:
            value = _num(value, 0.0)
            if value == int(value):
                value = int(value)
        key = f"{prefix}:{ident}"
        if lobby.world.get(key) == value:
            return False
        lobby.world[key] = value
        lobby.dirty = True
        self._emit(
            lobby,
            "interact",
            {"by": member.player_id, "act": kind, "key": key, "value": value},
        )
        return True

    # --------------------------------------------------------------- messages

    async def handle(self, lobby: Lobby, member: Participant, message: dict) -> None:
        kind = str(message.get("t", ""))
        member.last_seen = _now()
        lobby.touched = _now()

        if kind == "input":
            if not self._accept_move(lobby, member, message):
                await self._deliver(
                    member,
                    {
                        "t": "correct",
                        "x": member.state.get("x"),
                        "y": member.state.get("y"),
                        "z": member.state.get("z"),
                        "seq": _int(message.get("seq")),
                    },
                )
                if member.violations > MAX_VIOLATIONS:
                    await self.kick(lobby, member, "Bewegung nicht plausibel")
            return

        if kind == "ack":
            snap = _int(message.get("snap"))
            if snap > member.ack:
                member.ack = snap
                member.snapshots_acked += 1
            cursor = _int(message.get("ev"))
            if cursor > member.event_cursor:
                member.event_cursor = cursor
            return

        if kind == "pong":
            seq = _int(message.get("s"))
            sent = member.pending_ping.pop(seq, None)
            if sent is not None:
                sample = (_now() - sent) * 1000.0
                member.jitter = abs(sample - member.ping) if member.ping else 0.0
                member.ping = sample if not member.ping else member.ping * 0.7 + sample * 0.3
            return

        if kind == "ping":
            await self._deliver(
                member, {"t": "pong", "c": message.get("c"), "s": member.ping_seq}
            )
            return

        if kind == "ready":
            member.ready = bool(message.get("value", True))
            await self._push_lobby(lobby)
            return

        if kind == "name":
            member.name = _clean_name(message.get("value"), member.name)
            member.model = str(message.get("model", member.model))[:24]
            await self._push_lobby(lobby)
            self._persist(lobby)
            return

        if kind == "act":
            if self._apply_act(lobby, member, message):
                return
            await self._deliver(
                member,
                {
                    "t": "reject",
                    "kind": message.get("kind"),
                    "id": message.get("id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                    "z": message.get("z"),
                },
            )
            return

        if kind == "fx":
            effect = str(message.get("kind", ""))
            if effect not in FX_KINDS or not member.act_bucket.take():
                return
            body = message.get("data")
            if isinstance(body, dict) and len(json.dumps(body)) > 2_000:
                return
            await self._broadcast(
                lobby,
                {
                    "t": "fx",
                    "kind": effect,
                    "by": member.player_id,
                    "data": body if isinstance(body, dict) else {},
                },
                skip=member.player_id,
            )
            return

        if kind == "scene":
            phase = str(message.get("phase", ""))
            if phase == "ready":
                member.loaded = True
                member.scene = str(message.get("scene", lobby.scene))[:32]
                if lobby.phase in ("playing", "paused"):
                    await self._resume_player(lobby, member)
                else:
                    await self._check_barrier(lobby)
            elif phase == "request" and member.host:
                await self.change_scene(lobby, str(message.get("scene", "world"))[:32])
            return

        if kind == "chat":
            if not member.chat_bucket.take():
                return
            text = str(message.get("text", ""))[:300].strip()
            if text:
                await self._broadcast(
                    lobby,
                    {"t": "chat", "id": member.player_id, "name": member.name, "text": text},
                )
            return

        if kind == "emote":
            member.state["emote"] = _int(message.get("id"))
            return

        if kind == "start" and member.host:
            await self.start_game(lobby)
            return

        if kind == "pause" and member.host:
            lobby.phase = "paused" if lobby.phase == "playing" else "playing"
            await self._push_lobby(lobby)
            return

        if kind == "close" and member.host:
            await self.close_lobby(lobby, "Host hat die Lobby geschlossen")
            return

        if kind == "leave":
            await self.remove(lobby, member)
            return

    # ----------------------------------------------------------------- phases

    async def start_game(self, lobby: Lobby) -> None:
        members = lobby.online_members()
        if not members:
            return
        if not all(m.ready or m.host for m in members):
            host = lobby.host()
            if host is not None:
                await self._deliver(
                    host, {"t": "error", "code": "not_ready", "msg": "Nicht alle sind bereit"}
                )
            return
        lobby.phase = "loading"
        lobby.started_at = _now()
        for member in lobby.participants.values():
            member.loaded = False
            member.last_input = 0.0
            member.spawn = self._spawn_for(lobby, member.slot)
            member.state.update(
                {
                    "x": member.spawn["x"],
                    "y": member.spawn["y"],
                    "z": member.spawn["z"],
                    "yaw": member.spawn.get("yaw", 0.0),
                    "anim": "idle",
                }
            )
        await self._broadcast(
            lobby,
            {
                "t": "start",
                "seed": lobby.seed,
                "scene": lobby.scene,
                "save": lobby.save,
                "spawns": {m.player_id: m.spawn for m in lobby.ordered()},
                "lobby": lobby.summary(),
            },
        )
        self._persist(lobby)

    async def _resume_player(self, lobby: Lobby, member: Participant) -> None:
        member.last_input = 0.0
        await self._deliver(
            member,
            {
                "t": "spawn",
                "scene": lobby.scene,
                "at": lobby.tick + 2,
                "resumed": True,
                "spawns": {member.player_id: member.spawn},
                "state": lobby.full_state(),
            },
        )
        await self._push_lobby(lobby)

    async def _check_barrier(self, lobby: Lobby) -> None:
        members = lobby.online_members()
        if not members or lobby.phase not in ("loading", "switching"):
            await self._push_lobby(lobby)
            return
        if not all(m.loaded for m in members):
            await self._broadcast(
                lobby,
                {
                    "t": "sync",
                    "loaded": [m.player_id for m in members if m.loaded],
                    "total": len(members),
                },
            )
            return
        lobby.phase = "playing"
        await self._broadcast(
            lobby,
            {
                "t": "spawn",
                "scene": lobby.scene,
                "at": lobby.tick + 2,
                "spawns": {m.player_id: m.spawn for m in lobby.ordered()},
                "state": lobby.full_state(),
            },
        )
        await self._push_lobby(lobby)

    async def change_scene(self, lobby: Lobby, scene: str) -> None:
        if scene == lobby.scene:
            return
        lobby.scene = scene
        lobby.phase = "switching"
        for member in lobby.participants.values():
            member.loaded = False
            member.scene = scene
            member.last_input = 0.0
        await self._broadcast(lobby, {"t": "scene", "scene": scene, "phase": "load"})
        self._persist(lobby)

    async def kick(self, lobby: Lobby, member: Participant, reason: str) -> None:
        self._stats["kicks"] += 1
        await self._deliver(member, {"t": "kick", "reason": reason})
        if member.transport is not None:
            await member.transport.close()
        await self.remove(lobby, member)

    async def remove(self, lobby: Lobby, member: Participant) -> None:
        lobby.participants.pop(member.player_id, None)
        self._tokens.pop(member.token, None)
        if member.transport is not None:
            await member.transport.close()
        self._emit(lobby, "left", {"id": member.player_id})
        if member.host:
            remaining = lobby.ordered()
            if remaining:
                remaining[0].host = True
                lobby.owner = remaining[0].player_id
        if not lobby.participants:
            self._forget(lobby)
            return
        await self._push_lobby(lobby)
        self._persist(lobby)

    async def close_lobby(self, lobby: Lobby, reason: str) -> None:
        lobby.phase = "ended"
        await self._broadcast(lobby, {"t": "bye", "reason": reason})
        for member in list(lobby.participants.values()):
            if member.transport is not None:
                await member.transport.close()
        self._forget(lobby)

    # ------------------------------------------------------------------- tick

    async def _tick_lobby(self, lobby: Lobby) -> None:
        lobby.tick += 1
        now = _now()
        state = lobby.full_state()
        lobby.snapshot_id += 1
        lobby.snapshots.append((lobby.snapshot_id, state))
        if len(lobby.snapshots) > SNAPSHOT_HISTORY:
            del lobby.snapshots[: len(lobby.snapshots) - SNAPSHOT_HISTORY]
        history = dict(lobby.snapshots)

        for member in list(lobby.participants.values()):
            if not member.online:
                if member.dropped_at and now - member.dropped_at > RECONNECT_GRACE:
                    await self.remove(lobby, member)
                continue
            if now - member.last_seen > CLIENT_TIMEOUT:
                await self.detach(lobby, member)
                continue

            base = history.get(member.ack)
            payload: dict[str, Any] = {
                "t": "snap",
                "id": lobby.snapshot_id,
                "tick": lobby.tick,
                "time": round(now * 1000.0),
            }
            if base is None:
                payload["base"] = 0
                payload["players"] = state["players"]
                payload["world"] = state["world"]
                payload["phase"] = state["phase"]
                payload["scene"] = state["scene"]
            else:
                payload["base"] = member.ack
                players, gone = _diff_nested(base["players"], state["players"])
                if players:
                    payload["players"] = players
                if gone:
                    payload["gone"] = gone
                world = _diff(base["world"], state["world"])
                if world:
                    payload["world"] = world
                dropped = [k for k in base["world"] if k not in state["world"]]
                if dropped:
                    payload["unset"] = dropped
                if base["phase"] != state["phase"]:
                    payload["phase"] = state["phase"]
                if base["scene"] != state["scene"]:
                    payload["scene"] = state["scene"]

            pending = [e for e in lobby.events if e["eid"] > member.event_cursor]
            if pending:
                payload["ev"] = pending[-64:]

            if len(payload) > 4 or pending or base is None:
                member.snapshots_sent += 1
                self._stats["snapshots"] += 1
                await self._deliver(member, payload)

            if member.snapshots_sent > 20:
                acked = member.snapshots_acked
                member.loss = max(
                    0.0,
                    min(100.0, (1.0 - acked / max(1, member.snapshots_sent)) * 100.0),
                )

            if lobby.tick % int(TICK_HZ * PING_INTERVAL) == 0:
                member.ping_seq += 1
                member.pending_ping[member.ping_seq] = now
                if len(member.pending_ping) > 8:
                    oldest = sorted(member.pending_ping)[0]
                    member.pending_ping.pop(oldest, None)
                    member.ping = min(2000.0, member.ping * 1.2 + 40.0)
                await self._deliver(member, {"t": "ping", "s": member.ping_seq})

        if lobby.tick % int(TICK_HZ * 5) == 0:
            await self._push_lobby(lobby)
            if lobby.dirty:
                lobby.dirty = False
                self._persist(lobby)

    async def _loop(self) -> None:
        while True:
            started = _now()
            try:
                for lobby in list(self._lobbies.values()):
                    if not lobby.participants:
                        self._forget(lobby)
                        continue
                    if _now() - lobby.touched > LOBBY_TTL:
                        await self.close_lobby(lobby, "Lobby abgelaufen")
                        continue
                    await self._tick_lobby(lobby)
            except Exception:
                pass
            delay = TICK_DT - (_now() - started)
            await asyncio.sleep(max(0.001, delay))

    async def start(self) -> None:
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._loop())

    # ------------------------------------------------------------ tcp bridge

    async def serve_stream(self, host: str, port: int) -> None:
        async def client(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            transport = StreamTransport(writer)
            lobby: Lobby | None = None
            member: Participant | None = None
            try:
                while True:
                    header = await reader.readexactly(4)
                    size = int.from_bytes(header, "big")
                    if size <= 0 or size > 1_000_000:
                        break
                    blob = await reader.readexactly(size)
                    try:
                        message = json.loads(blob.decode("utf-8", errors="replace"))
                    except Exception:
                        continue
                    if not isinstance(message, dict):
                        continue
                    if lobby is None or member is None:
                        pair = await self.handshake(message, transport)
                        if pair is None:
                            if not transport.redirected:
                                await transport.send(
                                    {"t": "error", "code": "handshake", "msg": "Anmeldung fehlgeschlagen"}
                                )
                            break
                        lobby, member = pair
                        continue
                    await self.handle(lobby, member, message)
            except (asyncio.IncompleteReadError, ConnectionError, asyncio.CancelledError):
                pass
            except Exception:
                pass
            finally:
                if lobby is not None and member is not None and member.transport is transport:
                    await self.detach(lobby, member)
                await transport.close()

        try:
            self._server = await asyncio.start_server(client, host, port)
        except Exception:
            return
        async with self._server:
            try:
                await self._server.serve_forever()
            except asyncio.CancelledError:
                pass

    async def handshake(
        self, message: dict, transport: Transport
    ) -> tuple[Lobby, Participant] | None:
        kind = str(message.get("t", ""))
        name = message.get("name")
        model = str(message.get("model", "default"))
        game = str(message.get("game", "blockwelt"))

        async def fail(code: str, text: str) -> None:
            try:
                await transport.send({"t": "error", "code": code, "msg": text})
            except Exception:
                pass

        if kind == "hello":
            token = str(message.get("token", ""))
            found = self.resume(token)
            if found is None:
                await fail("resume", "Sitzung ist abgelaufen")
                return None
            lobby, member = found
            member.name = _clean_name(name, member.name)
            await self.attach(lobby, member, transport)
            return lobby, member

        if kind == "create":
            try:
                lobby, member = self.create_lobby(
                    game,
                    name,
                    model,
                    seed=message.get("seed"),
                    max_players=_int(message.get("max_players"), 2),
                    spawn=message.get("spawn") if isinstance(message.get("spawn"), dict) else None,
                )
            except ValueError as error:
                await fail("create", str(error))
                return None
            await self.attach(lobby, member, transport)
            return lobby, member

        if kind == "join":
            code = str(message.get("code", ""))
            if not self.knows_code(code):
                remote = await self.find_remote(code)
                if remote is not None:
                    transport.redirected = True
                    try:
                        await transport.send(
                            {
                                "t": "redirect",
                                "code": str(remote.get("code", code)).upper(),
                                "host": remote.get("host", ""),
                                "tcp_port": remote.get("tcp_port", 0),
                                "ws_port": remote.get("ws_port", 0),
                                "origin": remote.get("origin", ""),
                                "msg": "Gastgeber im Netzwerk gefunden",
                            }
                        )
                    except Exception:
                        pass
                    return None
            try:
                lobby, member = self.join_lobby(code, name, model)
            except ValueError as error:
                await fail("join", str(error))
                return None
            await self.attach(lobby, member, transport)
            return lobby, member

        await fail("handshake", "Anmeldung fehlgeschlagen")
        return None


_service: MultiplayerService | None = None


def get_multiplayer_service() -> MultiplayerService:
    global _service
    if _service is None:
        _service = MultiplayerService()
    return _service
