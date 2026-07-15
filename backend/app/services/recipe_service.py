from __future__ import annotations

import json
import re

from app.services.llm import complete
from app.services.settings_service import get_settings_service

SUGGEST_SYSTEM = (
    "Du bist Jon, ein hilfreicher Kochassistent. Der Nutzer nennt dir, was er zu "
    "Hause hat oder worauf er Lust hat. Schlage 3 passende, realistische Gerichte vor, "
    "die man mit üblichen Küchenmitteln kochen kann. Antworte AUSSCHLIESSLICH mit JSON: "
    '{"vorschlaege": [{"name": "...", "dauer": "25 Min", "schwierigkeit": "einfach", '
    '"beschreibung": "ein kurzer appetitlicher Satz"}]}'
)

RECIPE_SYSTEM = (
    "Du bist Jon, ein Kochassistent. Gib für das gewünschte Gericht ein vollständiges "
    "Rezept. Antworte AUSSCHLIESSLICH mit JSON: "
    '{"name": "...", "portionen": 2, "zutaten": ["200 g ...", "..."], '
    '"schritte": ["klarer, gut vorlesbarer Schritt", "..."]} '
    "Die Schritte sollen so formuliert sein, dass man sie beim Kochen laut vorlesen kann "
    "— je einer pro Handlung, ohne Nummern davor, kurz und konkret."
)


async def _json_complete(system: str, user: str, max_tokens: int) -> dict | None:
    provider, model = get_settings_service().selection()
    try:
        raw = await complete(
            system,
            user,
            provider=provider or None,
            model=model or None,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        match = re.search(r"\{.*\}", raw, re.S)
        return json.loads(match.group(0)) if match else None
    except Exception:
        return None


async def suggest(ingredients: str) -> dict:
    text = ingredients.strip()
    if not text:
        return {"error": "Sag mir, was du hast oder worauf du Lust hast."}
    data = await _json_complete(SUGGEST_SYSTEM, f"Ich habe / möchte: {text[:600]}", 700)
    ideas = []
    if data:
        for item in (data.get("vorschlaege") or [])[:3]:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            ideas.append(
                {
                    "name": str(item.get("name"))[:80],
                    "dauer": str(item.get("dauer", ""))[:20],
                    "schwierigkeit": str(item.get("schwierigkeit", ""))[:20],
                    "beschreibung": str(item.get("beschreibung", ""))[:200],
                }
            )
    if not ideas:
        return {"error": "Mir fällt gerade nichts ein — versuch es nochmal oder anders."}
    return {"vorschlaege": ideas}


async def recipe(dish: str) -> dict:
    name = dish.strip()
    if not name:
        return {"error": "Welches Gericht soll ich kochen?"}
    data = await _json_complete(RECIPE_SYSTEM, f"Gericht: {name[:120]}", 1400)
    if not data or not data.get("schritte"):
        return {"error": "Ich konnte kein Rezept erstellen. Versuch es nochmal."}
    steps = [str(s).strip() for s in data.get("schritte") if str(s).strip()][:20]
    ingredients = [str(z).strip() for z in (data.get("zutaten") or []) if str(z).strip()][:30]
    if not steps:
        return {"error": "Das Rezept hatte keine Schritte. Versuch es nochmal."}
    return {
        "name": str(data.get("name") or name)[:80],
        "portionen": int(data.get("portionen") or 2),
        "zutaten": ingredients,
        "schritte": steps,
    }
