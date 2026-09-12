from __future__ import annotations

import mimetypes
from datetime import datetime, timedelta
from pathlib import Path

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import Datei

ARTEN = {
    "pdf": "dokument",
    "docx": "dokument",
    "odt": "dokument",
    "txt": "dokument",
    "md": "dokument",
    "rtf": "dokument",
    "xlsx": "tabelle",
    "ods": "tabelle",
    "csv": "tabelle",
    "pptx": "praesentation",
    "odp": "praesentation",
    "png": "bild",
    "jpg": "bild",
    "jpeg": "bild",
    "webp": "bild",
    "gif": "bild",
    "svg": "bild",
    "bmp": "bild",
    "mp4": "video",
    "mov": "video",
    "mkv": "video",
    "webm": "video",
    "avi": "video",
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "flac": "audio",
    "m4a": "audio",
    "blend": "3d",
    "fbx": "3d",
    "obj": "3d",
    "glb": "3d",
    "gltf": "3d",
    "stl": "3d",
    "zip": "archiv",
    "7z": "archiv",
    "rar": "archiv",
    "tar": "archiv",
    "gz": "archiv",
}

ZUSATZ_TYPEN = {
    ".md": "text/markdown",
    ".blend": "application/x-blender",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".obj": "model/obj",
    ".stl": "model/stl",
    ".fbx": "application/octet-stream",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".ts": "text/typescript",
    ".tsx": "text/typescript",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}

AUFBEWAHRUNG_TAGE = 365

ZEITWOERTER = (
    "heute",
    "gestern",
    "vorgestern",
    "woche",
    "monat",
    "jahr",
    "montag",
    "dienstag",
    "mittwoch",
    "donnerstag",
    "freitag",
    "samstag",
    "sonntag",
    "vor ",
    "letzte",
    "letzten",
    "neulich",
    "kuerzlich",
    "kürzlich",
)


def _jetzt() -> datetime:
    return datetime.now()


def art_fuer(endung: str) -> str:
    return ARTEN.get(str(endung or "").lower().lstrip("."), "datei")


def mime_fuer(pfad: Path) -> str:
    endung = pfad.suffix.lower()
    if endung in ZUSATZ_TYPEN:
        return ZUSATZ_TYPEN[endung]
    geraten, _ = mimetypes.guess_type(pfad.name)
    return geraten or "application/octet-stream"


def lesbar(bytes_: int) -> str:
    wert = float(max(0, bytes_))
    for einheit in ("B", "KB", "MB", "GB"):
        if wert < 1024 or einheit == "GB":
            return f"{wert:.0f} {einheit}" if einheit == "B" else f"{wert:.1f} {einheit}"
        wert /= 1024
    return f"{wert:.1f} GB"


def karte(pfad: str | Path, projekt: str = "", titel: str = "") -> dict:
    ziel = Path(pfad)
    try:
        groesse = ziel.stat().st_size if ziel.exists() else 0
    except Exception:
        groesse = 0
    return {
        "type": "file",
        "name": ziel.name,
        "path": str(ziel),
        "mimeType": mime_fuer(ziel),
        "kind": art_fuer(ziel.suffix),
        "size": groesse,
        "sizeText": lesbar(groesse),
        "folder": str(ziel.parent),
        "project": projekt,
        "title": titel or ziel.stem,
        "exists": ziel.exists(),
        "actions": ["open", "download", "open_folder"],
    }


class DateiindexService:
    def _zeile(self, eintrag: Datei) -> dict:
        return {
            "id": eintrag.id,
            "pfad": eintrag.pfad,
            "name": eintrag.name,
            "endung": eintrag.endung,
            "art": eintrag.art,
            "groesse": int(eintrag.groesse or 0),
            "groesse_text": lesbar(int(eintrag.groesse or 0)),
            "titel": eintrag.titel or "",
            "beschreibung": eintrag.beschreibung or "",
            "projekt": eintrag.projekt or "",
            "auftrag": eintrag.auftrag or "",
            "quelle": eintrag.quelle,
            "vorhanden": bool(eintrag.vorhanden),
            "erstellt": eintrag.erstellt.isoformat(timespec="seconds")
            if eintrag.erstellt
            else "",
        }

    def merken(
        self,
        pfad: str | Path,
        titel: str = "",
        beschreibung: str = "",
        projekt: str = "",
        auftrag: str = "",
        quelle: str = "app",
    ) -> dict:
        ziel = Path(pfad)
        try:
            groesse = ziel.stat().st_size if ziel.exists() else 0
        except Exception:
            groesse = 0
        endung = ziel.suffix.lower().lstrip(".")
        try:
            with session_scope() as session:
                vorhanden = (
                    session.query(Datei).filter(Datei.pfad == str(ziel)).first()
                )
                eintrag = vorhanden or Datei(pfad=str(ziel))
                eintrag.name = ziel.name[:220]
                eintrag.endung = endung[:16]
                eintrag.art = art_fuer(endung)
                eintrag.groesse = groesse
                eintrag.titel = (titel or ziel.stem)[:300]
                if beschreibung:
                    eintrag.beschreibung = beschreibung[:1000]
                if projekt:
                    eintrag.projekt = projekt[:120]
                if auftrag:
                    eintrag.auftrag = auftrag[:64]
                eintrag.quelle = (quelle or "app")[:24]
                eintrag.vorhanden = 1 if ziel.exists() else 0
                eintrag.gesehen = _jetzt()
                if vorhanden is None:
                    session.add(eintrag)
                session.flush()
                return self._zeile(eintrag)
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            return karte(ziel, projekt, titel)

    def karte_und_merken(
        self,
        pfad: str | Path,
        titel: str = "",
        beschreibung: str = "",
        projekt: str = "",
        auftrag: str = "",
        quelle: str = "app",
    ) -> dict:
        self.merken(pfad, titel, beschreibung, projekt, auftrag, quelle)
        return karte(pfad, projekt, titel)

    def vergessen(self, kennung: str) -> bool:
        try:
            with session_scope() as session:
                eintrag = session.get(Datei, kennung)
                if eintrag is None:
                    return False
                session.delete(eintrag)
                return True
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            return False

    def liste(self, art: str = "", projekt: str = "", limit: int = 50) -> list[dict]:
        try:
            with session_scope() as session:
                frage = session.query(Datei)
                if art:
                    frage = frage.filter(Datei.art == art)
                if projekt:
                    frage = frage.filter(Datei.projekt == projekt)
                zeilen = (
                    frage.order_by(Datei.erstellt.desc()).limit(max(1, limit)).all()
                )
                return [self._zeile(z) for z in zeilen]
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            return []

    def suchen(self, frage: str, limit: int = 12) -> list[dict]:
        text = str(frage or "").strip()
        if not text:
            return self.liste(limit=limit)
        klein = text.lower()
        zeitraum = None
        if any(wort in klein for wort in ZEITWOERTER):
            try:
                from app.services.zeitraum import verstehen

                erkannt = verstehen(text)
                zeitraum = (erkannt.von, erkannt.bis)
            except Exception as fehler:
                leise(fehler, "services/dateiindex_service")
        gesucht_art = ""
        for endung, art in ARTEN.items():
            if endung in klein or art in klein:
                gesucht_art = art
                break
        try:
            with session_scope() as session:
                abfrage = session.query(Datei).filter(Datei.vorhanden == 1)
                if gesucht_art:
                    abfrage = abfrage.filter(Datei.art == gesucht_art)
                if zeitraum:
                    abfrage = abfrage.filter(
                        Datei.erstellt >= zeitraum[0], Datei.erstellt <= zeitraum[1]
                    )
                kandidaten = [
                    self._zeile(z)
                    for z in abfrage.order_by(Datei.erstellt.desc()).limit(400).all()
                ]
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            return []
        if not kandidaten:
            return []
        try:
            from app.services.semantik import aehnlichkeit, vektor

            ziel = vektor(text)
            bewertet = []
            for eintrag in kandidaten:
                beschreibung = " ".join(
                    [
                        eintrag["titel"],
                        eintrag["name"],
                        eintrag["beschreibung"],
                        eintrag["projekt"],
                        eintrag["art"],
                    ]
                )
                wert = aehnlichkeit(ziel, vektor(beschreibung))
                eintrag = dict(eintrag)
                eintrag["passung"] = round(wert, 2)
                bewertet.append(eintrag)
            bewertet.sort(key=lambda e: -e["passung"])
            treffer = [e for e in bewertet if e["passung"] > 0.42][:limit]
            return treffer or bewertet[:limit]
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            return kandidaten[:limit]

    def pruefen(self) -> dict:
        weg = 0
        try:
            with session_scope() as session:
                for eintrag in session.query(Datei).filter(Datei.vorhanden == 1).all():
                    if not Path(eintrag.pfad).exists():
                        eintrag.vorhanden = 0
                        weg += 1
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
        return {"verschwunden": weg}

    def stand(self) -> dict:
        try:
            with session_scope() as session:
                gesamt = session.query(Datei).count()
                da = session.query(Datei).filter(Datei.vorhanden == 1).count()
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            gesamt, da = 0, 0
        nach_art: dict[str, int] = {}
        for eintrag in self.liste(limit=500):
            nach_art[eintrag["art"]] = nach_art.get(eintrag["art"], 0) + 1
        return {
            "gesamt": gesamt,
            "vorhanden": da,
            "nach_art": nach_art,
            "neueste": self.liste(limit=10),
        }

    def aufraeumen(self, tage: int = AUFBEWAHRUNG_TAGE) -> int:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        try:
            with session_scope() as session:
                return int(
                    session.query(Datei)
                    .filter(Datei.erstellt < grenze, Datei.vorhanden == 0)
                    .delete(synchronize_session=False)
                    or 0
                )
        except Exception as fehler:
            leise(fehler, "services/dateiindex_service")
            return 0


_service: DateiindexService | None = None


def get_dateiindex_service() -> DateiindexService:
    global _service
    if _service is None:
        _service = DateiindexService()
    return _service
