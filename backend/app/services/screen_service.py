from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.registry import get_registry
from app.services.settings_service import get_settings_service
from app.services.system_service import SystemService

VISION_DEFAULTS = {
    "nvidia": "meta/llama-3.2-11b-vision-instruct",
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
        settings = get_settings()
        user = get_settings_service()
        saved_provider, saved_model = user.selection()
        provider_name = provider_name or saved_provider or settings.default_provider
        vision_model = (
            user.get().get("vision_model")
            or VISION_DEFAULTS.get(provider_name)
            or model
            or saved_model
            or settings.jon_model
        )
        provider = get_registry().all().get(provider_name)
        if not isinstance(provider, OpenAICompatibleProvider):
            return {
                "observation": "",
                "error": "Live Screen braucht einen OpenAI-kompatiblen Anbieter mit "
                "Vision-Modell (z.B. NVIDIA, OpenAI, OpenRouter).",
            }
        if not provider.available():
            return {"observation": "", "error": f"Kein API-Key fuer {provider_name}."}
        try:
            data_url = await asyncio.to_thread(_system.screenshot_data_url)
            text = await provider.describe_image(vision_model, data_url, WATCH_PROMPT)
        except Exception as exc:
            return {"observation": "", "error": str(exc)}
        clean = text.strip()
        if clean.lower().strip(" .!\"'") in ("nichts", "nothing", ""):
            return {"observation": ""}
        return {"observation": clean}

    async def explain(self) -> dict:
        settings = get_settings()
        user = get_settings_service()
        saved_provider, saved_model = user.selection()
        provider_name = saved_provider or settings.default_provider
        vision_model = (
            user.get().get("vision_model")
            or VISION_DEFAULTS.get(provider_name)
            or saved_model
            or settings.jon_model
        )
        provider = get_registry().all().get(provider_name)
        if not isinstance(provider, OpenAICompatibleProvider) or not provider.available():
            return {
                "error": "Dafür braucht Jon einen Anbieter mit Vision-Modell "
                "(z. B. NVIDIA, OpenAI oder OpenRouter mit hinterlegtem Key)."
            }
        try:
            data_url = await asyncio.to_thread(_system.screenshot_data_url)
            text = await provider.describe_image(
                vision_model, data_url, EXPLAIN_PROMPT, max_tokens=600
            )
        except Exception as exc:
            return {"error": str(exc)}
        clean = text.strip()
        if not clean:
            return {"error": "Ich konnte auf dem Bildschirm nichts erkennen."}
        return {"explanation": clean}


_service: ScreenService | None = None


def get_screen_service() -> ScreenService:
    global _service
    if _service is None:
        _service = ScreenService()
    return _service
