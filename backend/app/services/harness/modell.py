from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from app.core.config import lebendes_modell
from app.providers.base import ChatMessage, ChatRequest

VORUEBERGEHEND = ("rate limit", "rate_limit", "too many", "überlast", "ueberlast", "overloaded", "timeout", "timed out", "antwortet nicht", "unavailable", "connection", "verbindung", "temporar", "reset by peer", "leere antwort", "server disconnected")
STATUS = re.compile(r"\b(429|500|502|503|504|529)\b")
SPEICHER = ("memory", "speicher", "out of memory", "oom")
DENKEN = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
WARTEN = (2.0, 5.0, 12.0)
HARNESS_KONTEXT = 16384
ERSTES_TOKEN_S = 150.0


def denken_entfernen(text: str) -> str:
    sauber = DENKEN.sub("", text or "")
    if "<think>" in sauber.lower() and "</think>" not in sauber.lower():
        sauber = sauber[: sauber.lower().index("<think>")]
    return sauber.strip()


def voruebergehend(fehler: BaseException) -> bool:
    if isinstance(fehler, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    text = str(fehler).lower()
    return bool(STATUS.search(text)) or any(wort in text for wort in VORUEBERGEHEND)


def speicherfehler(fehler: BaseException) -> bool:
    text = str(fehler).lower()
    return any(wort in text for wort in SPEICHER)


@dataclass
class Antwort:
    text: str
    provider: str
    model: str
    hinweise: list[str] = field(default_factory=list)


@dataclass
class Zugang:
    provider: str
    model: str
    slot: str = "jon"
    kontext: int = 0
    klein: bool = False
    route: list[tuple[str, str]] = field(default_factory=list)

    def ollama_kontext(self) -> int:
        from app.services.ollama_service import get_ollama_service

        try:
            return int(get_ollama_service().chat_options().get("num_ctx") or 4096)
        except Exception:
            return 4096

    def fenster(self) -> int:
        if self.provider != "ollama":
            return 0
        eingestellt = self.ollama_kontext()
        return eingestellt if self.klein else max(eingestellt, HARNESS_KONTEXT)

    def zeichenbudget(self) -> int:
        if self.provider != "ollama":
            return 90000
        return max(5000, int((self.fenster() - self.ausgabe()) * 2.8) - 1500)

    def ausgabe(self) -> int:
        if self.provider != "ollama":
            return 8192
        return min(4096, max(1024, self.fenster() // 4))


async def route_bauen(zugang: Zugang) -> list[tuple[str, str]]:
    from app.providers.registry import get_registry
    from app.services.chat_service import attempt_plan_for, route_providers

    registry = get_registry()
    try:
        namen = await route_providers(registry, zugang.provider, zugang.model)
        plan = await attempt_plan_for(registry, zugang.provider, namen, zugang.model)
    except Exception:
        plan = []
    if (zugang.provider, zugang.model) not in plan:
        plan.insert(0, (zugang.provider, zugang.model))
    return plan[:4]


async def _einmal(name: str, model: str, system: str, user: str, zugang: Zugang) -> tuple[str, str]:
    from app.providers.registry import get_registry

    anbieter = get_registry().get(name)
    anfrage = ChatRequest(
        messages=[ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
        model=lebendes_modell(model, name),
        temperature=0.2,
        top_p=1.0,
        max_tokens=zugang.ausgabe(),
        tools=[],
        slot=zugang.slot,
        first_token_timeout=ERSTES_TOKEN_S,
        context_window=zugang.fenster() if name == "ollama" else 0,
    )
    inhalt: list[str] = []
    denken: list[str] = []
    async for teil in anbieter.stream(anfrage, None):
        if teil.kind == "content":
            inhalt.append(teil.delta)
        elif teil.kind == "reasoning":
            denken.append(teil.delta)
    return "".join(inhalt), "".join(denken)


async def anfragen(zugang: Zugang, system: str, user: str) -> Antwort:
    if not zugang.route:
        zugang.route = await route_bauen(zugang)
    hinweise: list[str] = []
    letzter: BaseException | None = None
    for name, model in list(zugang.route):
        for versuch in range(len(WARTEN) + 1):
            try:
                inhalt, denken = await asyncio.wait_for(_einmal(name, model, system, user, zugang), ERSTES_TOKEN_S + 300)
                text = denken_entfernen(inhalt) or denken_entfernen(denken) or denken.strip()
                if not text:
                    raise ValueError("leere Antwort vom Modell")
                if (name, model) != (zugang.provider, zugang.model):
                    hinweise.append(f"Ausweichmodell {model} ({name}) verwendet, weil {zugang.model} nicht antwortete.")
                return Antwort(text, name, model, hinweise)
            except asyncio.CancelledError:
                raise
            except Exception as fehler:
                letzter = fehler
                if name == "ollama" and not zugang.klein and speicherfehler(fehler):
                    zugang.klein = True
                    hinweise.append("Ollama hat zu wenig Speicher für ein großes Kontextfenster; der Harness arbeitet mit der eingestellten Kontextlänge weiter.")
                    raise KontextZuGross(str(fehler)) from fehler
                if not voruebergehend(fehler) or versuch == len(WARTEN):
                    break
                hinweise.append(f"{name} antwortet gerade nicht ({str(fehler)[:120]}). Neuer Versuch in {WARTEN[versuch]:.0f} s.")
                await asyncio.sleep(WARTEN[versuch])
    raise ModellNichtErreichbar(f"Kein Modell hat geantwortet. Letzter Fehler: {str(letzter)[:400]}")


class KontextZuGross(RuntimeError):
    pass


class ModellNichtErreichbar(RuntimeError):
    pass
