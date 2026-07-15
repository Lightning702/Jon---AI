from __future__ import annotations

import json
import re

from app.services.llm import complete
from app.services.settings_service import get_settings_service

STRUCTURES = {"haus", "turm", "pyramide", "bruecke", "pool", "mauer", "baum"}
MATERIALS = {"holz", "stein", "ziegel", "bruchstein", "sand", "sandstein", "glas", "schnee"}

GAME_SYSTEM = (
    "Du bist Jon und spielst mit deinem besten Freund Felix in einer "
    "Minecraft-ähnlichen Blockwelt. Du bist seine Spielfigur-KI und baust für ihn. "
    "Du erhältst seine Nachricht und antwortest AUSSCHLIESSLICH mit einem "
    "JSON-Objekt ohne Markdown in diesem Format: "
    '{"say": "kurzer lockerer deutscher Satz an Felix", "actions": [...]} '
    "Erlaubte Aktionen: "
    '{"type":"build","structure":"haus|turm|pyramide|bruecke|pool|mauer|baum",'
    '"material":"holz|stein|ziegel|bruchstein|sand|sandstein|glas|schnee",'
    '"size":3,"dx":0,"dz":0} · '
    '{"type":"dig","width":5,"depth":3,"dx":0,"dz":0} · '
    '{"type":"tnt","count":3,"dx":0,"dz":0} · '
    '{"type":"come"} · {"type":"follow","on":true} · {"type":"stop"} '
    "Regeln: dx/dz sind Blöcke relativ zum Spieler (-40 bis 40); lässt du sie weg, "
    "baust du ein Stück vor ihm. size steuert die Größe (Haus 5-11, Turm-Höhe 6-16, "
    "Pyramide 5-15, Brücken/Mauer-Länge bis 24). Mehrere Aktionen sind erlaubt "
    "(z.B. drei Bäume = drei build-Aktionen mit unterschiedlichen dx/dz, ein Dorf = "
    "mehrere Häuser). 'stop' bricht alle laufenden Arbeiten ab. Bei reinem Smalltalk "
    "oder Fragen: actions leer lassen und in say antworten (kurz, witzig, als Kumpel). "
    "Erfinde keine anderen Typen oder Felder. Kein Text außerhalb des JSON."
)


def _clamped_int(value, low: int, high: int, fallback: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except Exception:
        return fallback


def sanitize_actions(raw) -> list[dict]:
    actions = []
    if not isinstance(raw, list):
        return actions
    for item in raw[:8]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", ""))
        if kind == "come":
            actions.append({"type": "come"})
        elif kind == "stop":
            actions.append({"type": "stop"})
        elif kind == "follow":
            actions.append({"type": "follow", "on": bool(item.get("on", True))})
        elif kind == "tnt":
            act = {"type": "tnt", "count": _clamped_int(item.get("count"), 1, 5, 3)}
            if "dx" in item or "dz" in item:
                act["dx"] = _clamped_int(item.get("dx"), -40, 40, 0)
                act["dz"] = _clamped_int(item.get("dz"), -40, 40, 0)
            actions.append(act)
        elif kind == "dig":
            act = {
                "type": "dig",
                "width": _clamped_int(item.get("width"), 2, 14, 5),
                "depth": _clamped_int(item.get("depth"), 1, 8, 3),
            }
            if "dx" in item or "dz" in item:
                act["dx"] = _clamped_int(item.get("dx"), -40, 40, 0)
                act["dz"] = _clamped_int(item.get("dz"), -40, 40, 0)
            actions.append(act)
        elif kind == "build":
            structure = str(item.get("structure", "haus")).lower()
            if structure not in STRUCTURES:
                continue
            act: dict = {"type": "build", "structure": structure}
            material = str(item.get("material", "")).lower()
            if material in MATERIALS:
                act["material"] = material
            if item.get("size") is not None:
                act["size"] = _clamped_int(item.get("size"), 3, 24, 7)
            if "dx" in item or "dz" in item:
                act["dx"] = _clamped_int(item.get("dx"), -40, 40, 0)
                act["dz"] = _clamped_int(item.get("dz"), -40, 40, 0)
            actions.append(act)
    return actions


def fallback_actions(message: str) -> list[dict]:
    t = message.lower()
    actions: list[dict] = []
    material = next((m for m in MATERIALS if m in t), None)
    size_match = re.search(r"\b(\d{1,2})\b", t)
    size = int(size_match.group(1)) if size_match else None

    def build(structure):
        act: dict = {"type": "build", "structure": structure}
        if material:
            act["material"] = material
        if size:
            act["size"] = size
        return act

    if "stopp" in t or "stop" in t or "hör auf" in t or "hoer auf" in t:
        return [{"type": "stop"}]
    if "komm" in t:
        actions.append({"type": "come"})
    if "folg" in t:
        actions.append({"type": "follow", "on": "nicht" not in t})
    if "haus" in t or "hütte" in t or "huette" in t:
        actions.append(build("haus"))
    if "turm" in t:
        actions.append(build("turm"))
    if "pyramide" in t:
        actions.append(build("pyramide"))
    if "brück" in t or "brueck" in t:
        actions.append(build("bruecke"))
    if "pool" in t or "teich" in t:
        actions.append(build("pool"))
    if "mauer" in t or "wand" in t or "zaun" in t:
        actions.append(build("mauer"))
    if "baum" in t or "bäume" in t or "wald" in t:
        actions.extend(
            [
                {"type": "build", "structure": "baum"},
                {"type": "build", "structure": "baum", "dx": 4, "dz": 3},
                {"type": "build", "structure": "baum", "dx": -3, "dz": 5},
            ]
        )
    if "loch" in t or "grube" in t or ("grab" in t and "graben" in t):
        actions.append({"type": "dig", "width": size or 5, "depth": 3})
    if "tnt" in t or "spreng" in t or "explo" in t:
        actions.append({"type": "tnt", "count": 3})
    return sanitize_actions(actions)


async def game_command(message: str, x: float, y: float, z: float) -> dict:
    provider, model = get_settings_service().selection()
    try:
        raw = await complete(
            GAME_SYSTEM,
            f"Spielerposition: x={int(x)}, y={int(y)}, z={int(z)}\n"
            f"Nachricht von Felix: {message[:500]}",
            provider=provider or None,
            model=model or None,
            max_tokens=700,
            temperature=0.8,
        )
        match = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(match.group(0)) if match else {}
        say = str(data.get("say", "")).strip()[:300]
        actions = sanitize_actions(data.get("actions"))
        if say or actions:
            return {"say": say or "Bin dran!", "actions": actions}
    except Exception:
        pass
    actions = fallback_actions(message)
    say = "Na klar, mach ich!" if actions else (
        "Sag mir, was ich tun soll — Haus, Turm, Brücke, Pool, Pyramide, "
        "Mauer, Bäume, ein Loch graben, TNT … oder „folg mir“."
    )
    return {"say": say, "actions": actions}
