from __future__ import annotations

import json
import urllib.request

from app.services.settings_service import get_settings_service

DOMAINS = {
    "light",
    "switch",
    "media_player",
    "climate",
    "cover",
    "fan",
    "scene",
    "script",
    "vacuum",
    "lock",
}

ACTIONS = {
    "on": "turn_on",
    "an": "turn_on",
    "ein": "turn_on",
    "off": "turn_off",
    "aus": "turn_off",
    "toggle": "toggle",
    "open": "open_cover",
    "close": "close_cover",
    "play": "media_play",
    "pause": "media_pause",
    "start": "start",
    "stop": "stop",
    "lock": "lock",
    "unlock": "unlock",
}


class HomeAssistantService:
    def _cfg(self) -> tuple[str, str]:
        cfg = get_settings_service().get()
        url = str(cfg.get("ha_url", "")).strip().rstrip("/")
        token = str(cfg.get("ha_token", "")).strip()
        if not url or not token:
            raise RuntimeError(
                "Home Assistant ist nicht eingerichtet. Trage URL (z.B. "
                "http://homeassistant.local:8123) und Langzeit-Token im "
                "Zahnrad-Menue unter 'Verbindungen' ein."
            )
        return url, token

    def _request(self, path: str, payload: dict | None = None) -> object:
        url, token = self._cfg()
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            url + path,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST" if data else "GET",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    def devices(self) -> list[dict]:
        states = self._request("/api/states")
        result = []
        for item in states if isinstance(states, list) else []:
            entity = str(item.get("entity_id", ""))
            if entity.split(".")[0] not in DOMAINS:
                continue
            result.append(
                {
                    "entity_id": entity,
                    "name": (item.get("attributes") or {}).get(
                        "friendly_name", entity
                    ),
                    "zustand": item.get("state"),
                }
            )
        return result[:120]

    def control(self, entity_id: str, action: str, value: float | None = None) -> dict:
        entity_id = entity_id.strip()
        domain = entity_id.split(".")[0]
        if domain not in DOMAINS:
            raise ValueError(f"Unbekanntes Geraet: {entity_id}")
        service = ACTIONS.get(action.strip().lower())
        payload: dict = {"entity_id": entity_id}
        if service is None:
            if action.strip().lower() in ("helligkeit", "brightness") and value is not None:
                service = "turn_on"
                payload["brightness_pct"] = max(1, min(int(value), 100))
            elif action.strip().lower() in ("temperatur", "temperature") and value is not None:
                service = "set_temperature"
                payload["temperature"] = float(value)
            else:
                raise ValueError(
                    f"Unbekannte Aktion '{action}'. Erlaubt: "
                    f"{', '.join(sorted(set(ACTIONS)))}, helligkeit, temperatur"
                )
        if domain == "scene" and service in ("turn_on", "toggle"):
            service = "turn_on"
        self._request(f"/api/services/{domain}/{service}", payload)
        return {"entity_id": entity_id, "aktion": service, "ok": True}


_service: HomeAssistantService | None = None


def get_homeassistant_service() -> HomeAssistantService:
    global _service
    if _service is None:
        _service = HomeAssistantService()
    return _service
