from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

Handler = Callable[[Any, dict, str], str]
AsyncHandler = Callable[[Any, dict, str], Awaitable[str]]

REGISTER: dict[str, Handler] = {}
ASYNC_REGISTER: dict[str, AsyncHandler] = {}
PRAEFIXE: list[tuple[str, Handler]] = []


def werkzeug(*namen: str) -> Callable[[Handler], Handler]:
    def deko(funktion: Handler) -> Handler:
        for name in namen:
            REGISTER[name] = funktion
        return funktion

    return deko


def werkzeug_async(*namen: str) -> Callable[[AsyncHandler], AsyncHandler]:
    def deko(funktion: AsyncHandler) -> AsyncHandler:
        for name in namen:
            ASYNC_REGISTER[name] = funktion
        return funktion

    return deko


def praefix(anfang: str) -> Callable[[Handler], Handler]:
    def deko(funktion: Handler) -> Handler:
        PRAEFIXE.append((anfang, funktion))
        return funktion

    return deko


def finden(name: str) -> Handler | None:
    treffer = REGISTER.get(name)
    if treffer is not None:
        return treffer
    for anfang, funktion in PRAEFIXE:
        if name.startswith(anfang):
            return funktion
    return None


def finden_async(name: str) -> AsyncHandler | None:
    return ASYNC_REGISTER.get(name)


def antwort(daten: Any) -> str:
    if isinstance(daten, str):
        return daten
    return json.dumps(daten, ensure_ascii=False, default=str)


def namen() -> set[str]:
    return set(REGISTER) | set(ASYNC_REGISTER)


def laden() -> None:
    from app.services import werkzeuge_kern  # noqa: F401
