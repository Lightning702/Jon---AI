from __future__ import annotations

import asyncio
import re

from app.core.config import get_settings
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.registry import get_registry
from app.services.screen_service import VISION_DEFAULTS
from app.services.settings_service import get_settings_service
from app.services.system_service import SystemService

WEBCAM_PROMPT = (
    "Beschreibe freundlich und praezise auf Deutsch, was auf diesem Foto zu "
    "sehen ist: Personen (ohne zu raten, wer sie sind), Umgebung, "
    "Gegenstaende, Licht, Stimmung. Sprich die Person hinter der Kamera "
    "direkt mit 'du' an, ohne Namen. Beginne sofort mit der Beschreibung, "
    "ohne Einleitung."
)

NEUTRAL_PROMPT = (
    "Beschreibe praezise und detailliert auf Deutsch, was auf diesem Bild zu "
    "sehen ist: Personen, Umgebung, Gegenstaende, Licht. Beginne sofort mit "
    "der Beschreibung."
)

REFUSAL = re.compile(
    r"kann\s+(ich\s+)?nicht|nicht\s+zugreifen|zugriff|cannot|can.?t|unable|"
    r"keine\s+berechtigung|tut\s+mir\s+leid|sorry|nicht\s+in\s+der\s+lage",
    re.I,
)

_system = SystemService()


class WebcamService:
    async def describe(
        self,
        question: str = "",
        provider_name: str | None = None,
        model: str | None = None,
    ) -> dict:
        settings = get_settings()
        user = get_settings_service()
        if not bool(user.get().get("webcam_enabled", False)):
            return {
                "error": "Die Webcam ist in den Einstellungen deaktiviert. "
                "Aktiviere im Zahnrad-Menue den Schalter „Webcam erlauben“, "
                "dann schaue ich sofort nach."
            }
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
                "error": "Webcam-Analyse braucht einen OpenAI-kompatiblen Anbieter "
                "mit Vision-Modell (z.B. NVIDIA, OpenAI, OpenRouter)."
            }
        if not provider.available():
            return {"error": f"Kein API-Key fuer {provider_name}."}
        try:
            data_url = await asyncio.to_thread(_system.webcam_snapshot_data_url)
        except Exception as exc:
            return {"error": str(exc)}
        prompt = WEBCAM_PROMPT
        clean_question = re.sub(
            r"(?i)web\s*-?\s*cam|kamera|ueber meine|über meine", "", question
        ).strip(" ?!.,")
        if clean_question:
            prompt += f"\nDie Person moechte besonders wissen: {clean_question}"
        try:
            text = await provider.describe_image(
                vision_model, data_url, prompt, max_tokens=500
            )
            if REFUSAL.search(text) and len(text.strip()) < 300:
                text = await provider.describe_image(
                    vision_model, data_url, NEUTRAL_PROMPT, max_tokens=500
                )
        except Exception as exc:
            return {"error": f"Webcam-Analyse fehlgeschlagen: {exc}"}
        if REFUSAL.search(text) and len(text.strip()) < 300:
            return {
                "error": "Das Vision-Modell wollte das Bild nicht beschreiben. "
                "Versuch es einfach nochmal oder stelle in den Einstellungen "
                "ein staerkeres vision_model ein."
            }
        return {"beschreibung": text.strip()}


_service: WebcamService | None = None


def get_webcam_service() -> WebcamService:
    global _service
    if _service is None:
        _service = WebcamService()
    return _service
