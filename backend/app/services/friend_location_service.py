from __future__ import annotations

import json
import threading
import time
from typing import Any

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text

LOCATIONS_FILE = DATA_DIR / "friend_locations.json"

FRESH_SECONDS = 1800.0
STALE_SECONDS = 300.0
EVENT_TYPE = "standort"


class FriendLocationService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        base = {
            "teilen": {"aktiv": False, "alle": True, "peers": []},
            "empfangen": {},
            "zuletzt_gesendet": 0.0,
        }
        try:
            stored = json.loads(LOCATIONS_FILE.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                base["teilen"].update(stored.get("teilen") or {})
                received = stored.get("empfangen")
                if isinstance(received, dict):
                    base["empfangen"] = received
        except Exception:
            pass
        return base

    def _save(self) -> None:
        try:
            atomic_write_text(LOCATIONS_FILE,
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def sharing(self) -> dict[str, Any]:
        with self._lock:
            state = dict(self._data["teilen"])
        state["peers"] = list(state.get("peers") or [])
        return state

    def set_sharing(
        self,
        aktiv: bool | None = None,
        alle: bool | None = None,
        peers: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            state = self._data["teilen"]
            if aktiv is not None:
                state["aktiv"] = bool(aktiv)
            if alle is not None:
                state["alle"] = bool(alle)
            if peers is not None:
                state["peers"] = [str(item) for item in peers][:64]
            self._save()
            return dict(state)

    def targets(self, known_peer_ids: list[str]) -> list[str]:
        state = self.sharing()
        if not state.get("aktiv"):
            return []
        if state.get("alle"):
            return list(known_peer_ids)
        allowed = set(state.get("peers") or [])
        return [peer for peer in known_peer_ids if peer in allowed]

    def record(
        self,
        peer_id: str,
        lat: float,
        lon: float,
        accuracy: float | None = None,
        name: str = "",
        stamp: float | None = None,
    ) -> bool:
        if not peer_id:
            return False
        if not (-90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0):
            return False
        moment = float(stamp or time.time())
        if moment > time.time() + 120:
            moment = time.time()
        with self._lock:
            self._data["empfangen"][str(peer_id)] = {
                "lat": float(lat),
                "lon": float(lon),
                "genauigkeit_m": float(accuracy) if accuracy is not None else None,
                "name": str(name or ""),
                "ts": moment,
            }
            self._save()
        return True

    def forget(self, peer_id: str) -> bool:
        with self._lock:
            removed = self._data["empfangen"].pop(str(peer_id), None) is not None
            if removed:
                self._save()
        return removed

    def clear(self) -> int:
        with self._lock:
            count = len(self._data["empfangen"])
            self._data["empfangen"] = {}
            self._save()
        return count

    def friends(self, peers: list[dict]) -> list[dict[str, Any]]:
        now = time.time()
        with self._lock:
            received = dict(self._data["empfangen"])
        result: list[dict[str, Any]] = []
        for peer in peers:
            peer_id = str(peer.get("id", ""))
            fix = received.get(peer_id)
            if not fix:
                continue
            age = now - float(fix.get("ts") or 0.0)
            if age > FRESH_SECONDS:
                continue
            result.append(
                {
                    "id": peer_id,
                    "name": peer.get("name") or fix.get("name") or "Freund",
                    "avatar": peer.get("avatar") or "🙂",
                    "lat": fix["lat"],
                    "lon": fix["lon"],
                    "genauigkeit_m": fix.get("genauigkeit_m"),
                    "alter_s": round(age, 1),
                    "frisch": age <= STALE_SECONDS,
                    "online": bool(peer.get("online")),
                }
            )
        result.sort(key=lambda item: item["alter_s"])
        return result

    def note_sent(self) -> None:
        with self._lock:
            self._data["zuletzt_gesendet"] = time.time()
            self._save()

    def last_sent(self) -> float:
        with self._lock:
            return float(self._data.get("zuletzt_gesendet") or 0.0)

    async def broadcast(self, force: bool = False) -> dict[str, Any]:
        state = self.sharing()
        if not state.get("aktiv") and not force:
            return {"gesendet": 0, "grund": "Standortfreigabe ist aus"}

        from app.services.p2p_service import get_p2p_service

        p2p = get_p2p_service()
        peers = p2p.peers()
        targets = self.targets([str(peer["id"]) for peer in peers])
        if not targets:
            return {"gesendet": 0, "grund": "Keine Freunde ausgewählt"}

        from app.services.maps import get_maps_service

        service = get_maps_service()
        fix = await service.locate_device()
        if fix is None:
            lat, lon = await service.home()
            accuracy = None
        else:
            lat, lon = fix["lat"], fix["lon"]
            accuracy = fix.get("genauigkeit_m")

        me = p2p.identity()
        event = {
            "type": EVENT_TYPE,
            "lat": float(lat),
            "lon": float(lon),
            "genauigkeit_m": accuracy,
            "ts": time.time(),
            "from_name": me.get("name", ""),
        }
        sent = 0
        for peer_id in targets:
            try:
                if await p2p._send_event(peer_id, event):
                    sent += 1
            except Exception:
                continue
        self.note_sent()
        return {"gesendet": sent, "empfaenger": len(targets)}


_service: FriendLocationService | None = None


def get_friend_location_service() -> FriendLocationService:
    global _service
    if _service is None:
        _service = FriendLocationService()
    return _service
