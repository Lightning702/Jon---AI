from __future__ import annotations

import time
from typing import Awaitable, Callable

Route = list[tuple[str, str]]
_wechsel: list[dict] = []


def wechsel_merken(von: tuple[str, str], zu: tuple[str, str], grund: str) -> None:
    _wechsel.append({"zeit": time.time(), "von": list(von), "zu": list(zu), "grund": str(grund)[:200]})
    del _wechsel[:-50]


def letzte_wechsel(anzahl: int = 10) -> list[dict]:
    return list(_wechsel[-anzahl:])


def fallback_erlaubt() -> bool:
    try:
        from app.services.settings_service import get_settings_service

        return bool(get_settings_service().get().get("auto_failover", True))
    except Exception:
        return True


class ModelRouter:
    def __init__(self, registry=None) -> None:
        if registry is None:
            from app.providers.registry import get_registry

            registry = get_registry()
        self.registry = registry

    async def anbieter(self, provider: str, model: str) -> list[str]:
        from app.services.chat_service import route_providers

        return await route_providers(self.registry, provider, model)

    async def plan(
        self,
        provider: str,
        model: str,
        *,
        anbieter: Callable[[str, str], Awaitable[list[str]]] | None = None,
        planen: Callable[[str, list[str], str], Awaitable[Route]] | None = None,
        ollama: bool = True,
        grenze: int = 0,
    ) -> Route:
        from app.services.chat_service import attempt_plan_for, mit_ollama_ersatz, ollama_ersatz

        try:
            namen = await (anbieter or self.anbieter)(provider, model)
            if planen is not None:
                route = await planen(provider, namen, model)
            else:
                route = await attempt_plan_for(self.registry, provider, namen, model)
        except Exception:
            route = []
        if not route:
            route = [(provider, model)]
        if (provider, model) not in route:
            route.insert(0, (provider, model))
        from app.services.offline import aktiv as offline, lokal, lokales_modell

        if offline():
            route = [r for r in route if lokal(*r)] or [lokales_modell()]
        if ollama and fallback_erlaubt():
            try:
                route = mit_ollama_ersatz(route, await ollama_ersatz(self.registry, provider))
            except Exception:
                pass
        return route[:grenze] if grenze else route

    @staticmethod
    def zeichenbudget(provider: str, model: str) -> int:
        from app.services.harness.modell import Zugang

        try:
            return Zugang(provider, model).zeichenbudget()
        except Exception:
            return 24000

    @staticmethod
    def lokal(provider: str, model: str = "") -> bool:
        return provider in {"ollama", "lmstudio", "lokalserver"} or model.startswith("share:")


def get_model_router() -> ModelRouter:
    return ModelRouter()
