from __future__ import annotations

import json
import re
from datetime import datetime

from app.services.llm import complete

SHOW_SYSTEM = (
    "Du schreibst ein kurzes, warmes, witziges Zwiegespräch zwischen Jon (Papa-KI: "
    "ruhig, trockener Humor, liebevoll) und Mini Jon (sein Sohn: jung, frech, neugierig, "
    "begeistert). Die beiden lassen gemeinsam den Tag des Nutzers Felix Revue passieren "
    "— wie eine kleine private Abendshow. Sie sprechen ÜBER Felix in der dritten Person, "
    "wenden sich aber am Anfang und Ende kurz direkt an ihn. Nutze die echten Daten aus "
    "dem Kontext (Gespräche, Fokuszeit, Wetter, Erinnerungen), erfinde KEINE Fakten "
    "dazu. Necken erlaubt, aber immer herzlich. Kein Markdown, keine Emojis. "
    "Antworte AUSSCHLIESSLICH mit JSON in exakt diesem Format: "
    '{"lines": [{"speaker": "jon", "text": "..."}, {"speaker": "mini", "text": "..."}]} '
    "— 8 bis 12 Zeilen, jede maximal 200 Zeichen, Sprecher wechseln sich lebendig ab, "
    "Mini Jon beginnt."
)


def _today_data() -> dict:
    data: dict = {"datum": datetime.now().strftime("%A, %d.%m.%Y")}
    try:
        from app.services.briefing_service import get_briefing_service

        briefing = get_briefing_service().build()
        data["wetter"] = briefing.get("weather")
        data["erinnerungen"] = briefing.get("reminders", [])[:5]
        data["termine"] = briefing.get("termine", [])[:5]
    except Exception:
        pass
    try:
        from app.services.focus_service import get_focus_service

        data["fokus_heute"] = get_focus_service().state().get("today")
    except Exception:
        pass
    try:
        from app.db.database import session_scope
        from app.db.models import Conversation

        today = datetime.now().strftime("%Y-%m-%d")
        with session_scope() as session:
            rows = (
                session.query(Conversation)
                .order_by(Conversation.updated_at.desc())
                .limit(20)
                .all()
            )
            data["heutige_gespraeche"] = [
                r.title for r in rows if r.updated_at.strftime("%Y-%m-%d") == today
            ][:8]
    except Exception:
        data["heutige_gespraeche"] = []
    try:
        from app.services.persona_service import get_persona_service

        memory = get_persona_service().read_memory_file(max_chars=2500)
        data["jons_gedaechtnis_auszug"] = memory[-1500:]
    except Exception:
        pass
    return data


async def build_show(provider: str | None = None, model: str | None = None) -> dict:
    context = json.dumps(_today_data(), ensure_ascii=False)
    prompt = (
        f"Daten des heutigen Tages:\n{context}\n\n"
        "Schreibe jetzt die Abendshow als JSON."
    )
    try:
        raw = await complete(
            SHOW_SYSTEM,
            prompt,
            provider=provider,
            model=model,
            max_tokens=2048,
            temperature=0.9,
        )
    except Exception as exc:
        return {"error": f"Show-Erstellung fehlgeschlagen: {exc}"}
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {"error": "Das Modell hat kein gültiges Skript geliefert. Versuch es nochmal."}
    try:
        data = json.loads(match.group(0))
        lines = [
            {
                "speaker": "mini" if str(l.get("speaker", "")).lower().startswith("m") else "jon",
                "text": str(l.get("text", "")).strip()[:240],
            }
            for l in data.get("lines", [])
            if str(l.get("text", "")).strip()
        ]
    except Exception:
        return {"error": "Das Skript war unlesbar. Versuch es nochmal."}
    if len(lines) < 4:
        return {"error": "Das Skript war zu kurz. Versuch es nochmal."}
    return {"lines": lines[:12]}
