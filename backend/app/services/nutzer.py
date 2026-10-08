from __future__ import annotations


def nutzername() -> str:
    try:
        from app.services.settings_service import get_settings_service

        return str(get_settings_service().get().get("p2p_username", "") or "").strip()[:40]
    except Exception:
        return ""


def anrede(ersatz: str = "") -> str:
    return nutzername() or ersatz


def bezeichnung() -> str:
    name = nutzername()
    return f"dem Nutzer {name}" if name else "dem Nutzer"


def gruss(text: str) -> str:
    name = nutzername()
    return text.replace("{name}", f" {name}" if name else "")
