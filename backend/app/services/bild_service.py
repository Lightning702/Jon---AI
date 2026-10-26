from __future__ import annotations

import asyncio
from pathlib import Path


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
    from app.services import sehen

    ziel = Path(pfad).expanduser()
    if not ziel.is_file():
        return {"error": f"Die Datei {pfad} gibt es nicht."}
    endung = ziel.suffix.lower()
    if endung not in BILD_ARTEN and endung not in VIDEO_ARTEN:
        return {"error": "Das ist weder ein Bild noch ein Video."}
    if endung in VIDEO_ARTEN:
        ergebnis = await sehen.video_beschreiben(ziel, frage)
        quelle = "video"
    else:
        try:
            jpeg, quelle = await asyncio.to_thread(_als_jpeg, ziel)
        except Exception as exc:
            return {"error": str(exc)}
        aufgabe = PROMPT
        if frage.strip():
            aufgabe += f"\nDie Person moechte besonders wissen: {frage.strip()}"
        ergebnis = await sehen.beschreiben([jpeg], aufgabe, "bild", max_tokens=600)
    if not ergebnis.get("text"):
        return {"error": "Ansehen fehlgeschlagen: " + str(ergebnis.get("fehler") or "kein Bildmodell erreichbar")}
    antwort = {
        "beschreibung": ergebnis["text"],
        "quelle": quelle,
        "datei": str(ziel),
        "groesse": ziel.stat().st_size,
        "modell": ergebnis.get("modell", ""),
    }
    if quelle == "video":
        antwort.update({"standbilder": ergebnis.get("bilder", 0), "dauer_s": ergebnis.get("dauer", 0)})
    return antwort
