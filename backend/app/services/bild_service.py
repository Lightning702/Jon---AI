from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from app.core.config import get_settings
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.registry import get_registry
from app.services.screen_service import VISION_DEFAULTS
from app.services.settings_service import get_settings_service

BILD_ARTEN = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
VIDEO_ARTEN = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".3gp"}
KANTE_MAX = 1600
PROMPT = (
    "Beschreibe praezise und freundlich auf Deutsch, was auf diesem Bild zu "
    "sehen ist: Motiv, Personen (ohne zu raten, wer sie sind), Umgebung, "
    "Text im Bild, Stimmung. Beginne sofort mit der Beschreibung."
)


def _als_jpeg(pfad: Path) -> tuple[bytes, str]:
    import cv2

    endung = pfad.suffix.lower()
    if endung in VIDEO_ARTEN:
        aufnahme = cv2.VideoCapture(str(pfad))
        try:
            bilder = aufnahme.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            if bilder > 2:
                aufnahme.set(cv2.CAP_PROP_POS_FRAMES, int(bilder // 2))
            gelesen, rahmen = aufnahme.read()
        finally:
            aufnahme.release()
        if not gelesen or rahmen is None:
            raise ValueError("Aus diesem Video liess sich kein Bild holen.")
        quelle = "video"
    else:
        rahmen = cv2.imread(str(pfad))
        if rahmen is None:
            raise ValueError("Diese Bilddatei konnte ich nicht oeffnen.")
        quelle = "bild"
    hoehe, breite = rahmen.shape[:2]
    kante = max(hoehe, breite)
    if kante > KANTE_MAX:
        faktor = KANTE_MAX / kante
        rahmen = cv2.resize(
            rahmen,
            (int(breite * faktor), int(hoehe * faktor)),
            interpolation=cv2.INTER_AREA,
        )
    erfolg, puffer = cv2.imencode(".jpg", rahmen, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not erfolg:
        raise ValueError("Das Bild liess sich nicht umwandeln.")
    return puffer.tobytes(), quelle


async def ansehen(pfad: str, frage: str = "") -> dict:
    ziel = Path(pfad).expanduser()
    if not ziel.is_file():
        return {"error": f"Die Datei {pfad} gibt es nicht."}
    endung = ziel.suffix.lower()
    if endung not in BILD_ARTEN and endung not in VIDEO_ARTEN:
        return {"error": "Das ist weder ein Bild noch ein Video."}

    settings = get_settings()
    nutzer = get_settings_service()
    gewaehlt, modell = nutzer.selection()
    anbieter_name = gewaehlt or settings.default_provider
    sicht = (
        nutzer.get().get("vision_model")
        or VISION_DEFAULTS.get(anbieter_name)
        or modell
        or settings.jon_model
    )
    anbieter = get_registry().all().get(anbieter_name)
    if not isinstance(anbieter, OpenAICompatibleProvider):
        return {
            "error": "Zum Ansehen brauche ich einen OpenAI-kompatiblen Anbieter "
            "mit Vision-Modell (z.B. NVIDIA, OpenAI, OpenRouter)."
        }
    if not anbieter.available():
        return {"error": f"Kein API-Key fuer {anbieter_name}."}

    try:
        jpeg, quelle = await asyncio.to_thread(_als_jpeg, ziel)
    except Exception as exc:
        return {"error": str(exc)}

    daten_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
    aufgabe = PROMPT
    if quelle == "video":
        aufgabe += "\nDas ist ein Standbild aus der Mitte eines Videos."
    if frage.strip():
        aufgabe += f"\nDie Person moechte besonders wissen: {frage.strip()}"
    try:
        text = await anbieter.describe_image(sicht, daten_url, aufgabe, max_tokens=600)
    except Exception as exc:
        return {"error": f"Ansehen fehlgeschlagen: {exc}"}
    return {
        "beschreibung": text.strip(),
        "quelle": quelle,
        "datei": str(ziel),
        "groesse": ziel.stat().st_size,
    }
