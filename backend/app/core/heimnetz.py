from __future__ import annotations


def lan_aktiv() -> bool:
    from app.core.config import get_settings

    if get_settings().jon_lan:
        return True
    try:
        from app.services.settings_service import get_settings_service

        return bool(get_settings_service().get().get("heimnetz"))
    except Exception:
        return False
