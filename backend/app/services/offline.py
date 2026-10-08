from __future__ import annotations

import re

LOKALE_ANBIETER = {"ollama", "lmstudio", "lokalserver"}
LOKALE_STUDIO = {"lokal", "lokalserver"}
GESPERRT = {
    "web_search", "http_get", "download_file", "get_weather", "youtube_transkript", "deep_learning", "maps",
    "open_url", "bild_suche", "spotify_play", "spotify_search", "spotify_now_playing", "send_friend_message",
    "telegram_send", "call_user", "schedule_call", "send_email", "team",
}
MELDUNG = (
    "Der Offline-Modus ist an: Jon bleibt komplett lokal und nutzt kein Internet. "
    "Diese Aktion braucht das Netz - schalte den Offline-Modus in den Einstellungen aus, "
    "wenn du sie ausführen willst."
)


def aktiv() -> bool:
    try:
        from app.services.settings_service import get_settings_service

        return bool(get_settings_service().get().get("offline_modus", False))
    except Exception:
        return False


def lokal(provider: str, model: str = "") -> bool:
    if re.search(r"[:-]cloud\b", str(model), re.I):
        return False
    return provider in LOKALE_ANBIETER or str(model).startswith("share:")


def gesperrt(werkzeug: str) -> bool:
    return aktiv() and (werkzeug in GESPERRT or werkzeug.startswith("browser_") or werkzeug.startswith("android_"))


def lokales_modell() -> tuple[str, str]:
    from app.services.aufgaben_modelle import zuordnung

    for aufgabe in ("text", "code"):
        eintrag = zuordnung().get(aufgabe) or {}
        if lokal(str(eintrag.get("provider", "")), str(eintrag.get("model", ""))) and eintrag.get("model"):
            return str(eintrag["provider"]), str(eintrag["model"])
    try:
        from app.services.ollama_service import get_ollama_service

        gewaehlt = get_ollama_service().selected_model()
        if gewaehlt:
            return "ollama", gewaehlt
    except Exception:
        pass
    from app.providers.lokal_server import einstellung

    if einstellung()[0]:
        return "lokalserver", ""
    return "ollama", ""


def lokal_erzwingen(provider: str, model: str) -> tuple[str, str]:
    if not aktiv() or lokal(provider, model):
        return provider, model
    return lokales_modell()
