from __future__ import annotations

__all__ = ["get_manager", "get_guard", "get_zustand", "ausfuehren", "auftrag_ausfuehren"]


def get_manager():
    from app.services.browser.manager import get_manager as _fn

    return _fn()


def get_guard():
    from app.services.browser.sicherheit import get_guard as _fn

    return _fn()


def get_zustand():
    from app.services.browser.zustand import get_zustand as _fn

    return _fn()


def ausfuehren(op: str, args: dict, nur_lesen: bool = False) -> dict:
    from app.services.browser.werkzeuge import ausfuehren as _fn

    return _fn(op, args, nur_lesen=nur_lesen)


async def auftrag_ausfuehren(auftrag: str, dry_run: bool = False, max_schritte=None):
    from app.services.browser.agent import auftrag_ausfuehren as _fn

    return await _fn(auftrag, dry_run=dry_run, max_schritte=max_schritte)
