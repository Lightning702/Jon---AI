from __future__ import annotations

from openai import AsyncOpenAI

from app.providers.base import ProviderError
from app.providers.openai_compatible import OpenAICompatibleProvider


def einstellung() -> tuple[str, str]:
    try:
        from app.services.settings_service import get_settings_service

        daten = get_settings_service().get()
    except Exception:
        return "", ""
    adresse = str(daten.get("lokaler_server_url", "") or "").strip().rstrip("/")
    if adresse and not adresse.startswith(("http://", "https://")):
        adresse = "http://" + adresse
    if adresse and not adresse.endswith("/v1"):
        adresse += "/v1"
    return adresse, str(daten.get("lokaler_server_key", "") or "").strip() or "lokal"


class LokalerServer(OpenAICompatibleProvider):
    def __init__(self, timeout: float = 600.0) -> None:
        super().__init__(name="lokalserver", base_url="", api_key="lokal", default_models=[], timeout=timeout)

    def _key(self, slot: str = "jon") -> str | None:
        adresse, schluessel = einstellung()
        return schluessel if adresse else None

    def _client(self, slot: str = "jon") -> AsyncOpenAI:
        adresse, schluessel = einstellung()
        if not adresse:
            raise ProviderError("lokalserver: Keine Adresse eingetragen")
        kennung = adresse + "|" + schluessel
        client = self._clients.get(kennung)
        if client is None:
            client = AsyncOpenAI(base_url=adresse, api_key=schluessel, timeout=self._timeout, max_retries=1)
            self._clients = {kennung: client}
            self._models_cache = None
        return client
