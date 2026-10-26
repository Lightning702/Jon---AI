from __future__ import annotations

import asyncio

from app.core.config import NVIDIA_SEHEN_MODELL
from app.services.system_service import SystemService

VISION_DEFAULTS = {
    "nvidia": NVIDIA_SEHEN_MODELL,
    "openai": "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "xai": "grok-2-vision-latest",
    "gemini": "gemini-2.0-flash",
}

WATCH_PROMPT = (
    "Du bist Jon und schaust kurz auf den Bildschirm des Nutzers. Wenn du etwas "
    "erkennst, das ihm KONKRET hilft - ein sichtbarer Fehler, eine Fehlermeldung, ein "
    "Problem, etwas Veraltetes oder ein wirklich nuetzlicher Verbesserungsvorschlag - "
    "dann sag es in EINEM kurzen, freundlichen deutschen Satz, direkt an ihn gerichtet. "
    "Wenn nichts wirklich Wichtiges zu sehen ist, antworte AUSSCHLIESSLICH mit dem "
    "einzelnen Wort: nichts"
)

EXPLAIN_PROMPT = (
    "Du bist Jon und schaust auf einen Screenshot vom Bildschirm des Nutzers. "
    "Erklaere ihm auf Deutsch klar und hilfreich, was hier zu sehen ist und was es "
    "bedeutet. Wenn eine Fehlermeldung zu sehen ist, sag was sie bedeutet und wie er "
    "sie loest. Ist es eine Aufgabe (Mathe, Formular, Frage), loese sie oder hilf "
    "konkret. Ist Text in einer Fremdsprache zu sehen, uebersetze ihn. Fasse dich "
    "freundlich und praegnant, direkt an ihn gerichtet."
)

_system = SystemService()


class ScreenService:
    async def observe(
        self, provider_name: str | None = None, model: str | None = None
    ) -> dict:
        from app.services import sehen

        try:
            data_url = await asyncio.to_thread(_system.screenshot_data_url)
        except Exception as exc:
            return {"observation": "", "error": str(exc)}
        ergebnis = await sehen.bild_url_beschreiben(data_url, WATCH_PROMPT, provider_name, 300)
        if not ergebnis.get("text"):
            return {"observation": "", "error": str(ergebnis.get("fehler") or "Kein Bildmodell erreichbar.")}
        clean = ergebnis["text"].strip()
        if clean.lower().strip(" .!\"'") in ("nichts", "nothing", ""):
            return {"observation": ""}
        return {"observation": clean}

    async def explain(self) -> dict:
        from app.services.premium import get_premium

        get_premium().pruefen("bildschirm")

        from app.services import sehen

        try:
            data_url = await asyncio.to_thread(_system.screenshot_data_url)
        except Exception as exc:
            return {"error": str(exc)}
        ergebnis = await sehen.bild_url_beschreiben(data_url, EXPLAIN_PROMPT, None, 600)
        if ergebnis.get("fehler") and not ergebnis.get("text"):
            return {
                "error": "Dafür braucht Jon einen Anbieter mit Bildmodell "
                "(z. B. NVIDIA, OpenAI oder OpenRouter mit hinterlegtem Key)."
            }
        clean = ergebnis.get("text", "").strip()
        if not clean:
            return {"error": "Ich konnte auf dem Bildschirm nichts erkennen."}
        return {"explanation": clean}


_service: ScreenService | None = None


def get_screen_service() -> ScreenService:
    global _service
    if _service is None:
        _service = ScreenService()
    return _service
