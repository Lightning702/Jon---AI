from __future__ import annotations

from app.services.llm import complete

SIM_SYSTEM = (
    "Du bist Jons Simulations-Engine. Du beantwortest 'Was waere wenn'-Fragen, indem "
    "du moegliche Zukuenfte durchspielst, statt nur allgemein zu antworten. "
    "Struktur deiner Antwort auf Deutsch:\n"
    "1. Kurze Einordnung der Ausgangslage (1-2 Saetze).\n"
    "2. 2 bis 3 Szenarien mit Namen (z.B. 'Optimistisch', 'Realistisch', "
    "'Pessimistisch' oder passend zur Frage), je mit: was passiert, Folgen, "
    "grobe Wahrscheinlichkeit in Prozent.\n"
    "3. Ein klares Fazit mit Empfehlung.\n"
    "Sei konkret und ehrlich ueber Unsicherheit. Erfinde keine exakten Zahlen als "
    "Fakten, kennzeichne Schaetzungen als Schaetzung."
)


class SimulationService:
    async def simulate(
        self,
        scenario: str,
        context: str = "",
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        prompt = scenario.strip()
        if context.strip():
            prompt = f"{prompt}\n\nKontext: {context.strip()}"
        result = await complete(SIM_SYSTEM, prompt, provider, model, max_tokens=1400)
        return {"scenario": scenario, "result": result}


_service: SimulationService | None = None


def get_simulation_service() -> SimulationService:
    global _service
    if _service is None:
        _service = SimulationService()
    return _service
