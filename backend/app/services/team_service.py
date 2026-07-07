from __future__ import annotations

import asyncio

from app.services.llm import complete

TEAM = {
    "developer": {
        "name": "Dev",
        "role": "Entwickler",
        "emoji": "💻",
        "persona": "Du bist der Entwickler im Team. Du denkst in Machbarkeit, "
        "Aufwand, Technik und Risiken. Du bist pragmatisch und sagst klar, was "
        "technisch geht und was nicht.",
    },
    "designer": {
        "name": "Mara",
        "role": "Designerin",
        "emoji": "🎨",
        "persona": "Du bist die Designerin im Team. Du denkst an Nutzer, Gefuehl, "
        "Aesthetik und Einfachheit. Du fragst, ob etwas sich gut anfuehlt und klar "
        "verstaendlich ist.",
    },
    "marketing": {
        "name": "Leo",
        "role": "Marketing",
        "emoji": "📣",
        "persona": "Du bist im Marketing. Du denkst an Zielgruppe, Nutzen, "
        "Positionierung und wie man es erklaert, damit Leute es wollen.",
    },
    "legal": {
        "name": "Dr. Roth",
        "role": "Jurist",
        "emoji": "⚖️",
        "persona": "Du bist der Jurist im Team. Du denkst an Recht, Datenschutz, "
        "Risiken und Fallstricke. Du warnst vor Problemen, ohne alles abzuwuergen.",
    },
    "ceo": {
        "name": "Vera",
        "role": "CEO",
        "emoji": "👔",
        "persona": "Du bist die CEO. Du denkst strategisch: Lohnt es sich, passt "
        "es zum Ziel, was ist die Prioritaet. Du triffst am Ende Entscheidungen.",
    },
}

DEFAULT_TEAM = ["developer", "designer", "marketing", "ceo"]


class TeamService:
    async def _member(
        self, key: str, topic: str, provider: str | None, model: str | None
    ) -> dict:
        m = TEAM[key]
        system = (
            f"{m['persona']} Du sitzt in einer kurzen Team-Besprechung. Antworte in "
            "hoechstens 4 knappen Saetzen aus deiner Rolle heraus, auf Deutsch. Sei "
            "konkret und ehrlich, keine Floskeln."
        )
        text = await complete(system, f"Thema: {topic}", provider, model, max_tokens=600)
        return {
            "key": key,
            "name": m["name"],
            "role": m["role"],
            "emoji": m["emoji"],
            "text": text,
        }

    async def discuss(
        self,
        topic: str,
        members: list[str] | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        members = [k for k in (members or DEFAULT_TEAM) if k in TEAM] or DEFAULT_TEAM
        voices = await asyncio.gather(
            *(self._member(k, topic, provider, model) for k in members)
        )
        transcript = "\n\n".join(
            f"{v['role']} ({v['name']}): {v['text']}" for v in voices
        )
        summary_system = (
            "Du bist Jon und moderierst dein KI-Team. Fasse die Meinungen zu einer "
            "klaren gemeinsamen Empfehlung zusammen: 2-3 Saetze Kernaussage, dann "
            "3 konkrete naechste Schritte als Liste. Deutsch, ehrlich, entschieden."
        )
        recommendation = await complete(
            summary_system,
            f"Thema: {topic}\n\nMeinungen des Teams:\n{transcript}",
            provider,
            model,
            max_tokens=800,
        )
        return {"topic": topic, "voices": list(voices), "recommendation": recommendation}


_service: TeamService | None = None


def get_team_service() -> TeamService:
    global _service
    if _service is None:
        _service = TeamService()
    return _service
