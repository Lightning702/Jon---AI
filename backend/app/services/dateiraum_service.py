from __future__ import annotations

import os
import re
import sys
import threading
import unicodedata
from pathlib import Path

from app.core.fehler import leise

UNTERORDNER = (
    "Projects",
    "Documents",
    "PDFs",
    "Images",
    "Videos",
    "Audio",
    "Blender",
    "Code",
    "Downloads",
    "Generated",
    "Workspace",
    "Logs",
    "Temp",
    "Backups",
    "Config",
)

ART_ORDNER = {
    "pdf": "PDFs",
    "docx": "Documents",
    "odt": "Documents",
    "txt": "Documents",
    "md": "Documents",
    "rtf": "Documents",
    "xlsx": "Documents",
    "ods": "Documents",
    "csv": "Documents",
    "pptx": "Documents",
    "odp": "Documents",
    "png": "Images",
    "jpg": "Images",
    "jpeg": "Images",
    "webp": "Images",
    "gif": "Images",
    "svg": "Images",
    "bmp": "Images",
    "mp4": "Videos",
    "mov": "Videos",
    "mkv": "Videos",
    "webm": "Videos",
    "avi": "Videos",
    "mp3": "Audio",
    "wav": "Audio",
    "ogg": "Audio",
    "flac": "Audio",
    "m4a": "Audio",
    "blend": "Blender",
    "fbx": "Blender",
    "obj": "Blender",
    "glb": "Blender",
    "gltf": "Blender",
    "stl": "Blender",
    "py": "Code",
    "js": "Code",
    "ts": "Code",
    "tsx": "Code",
    "jsx": "Code",
    "html": "Code",
    "css": "Code",
    "json": "Code",
    "yaml": "Code",
    "yml": "Code",
    "xml": "Code",
    "sql": "Code",
    "c": "Code",
    "cpp": "Code",
    "h": "Code",
    "hpp": "Code",
    "java": "Code",
    "rs": "Code",
    "go": "Code",
    "dart": "Code",
    "sh": "Code",
    "ps1": "Code",
    "zip": "Downloads",
    "7z": "Downloads",
    "rar": "Downloads",
    "tar": "Downloads",
    "gz": "Downloads",
}

WORT_ORDNER = {
    "desktop": "desktop",
    "schreibtisch": "desktop",
    "dokumente": "dokumente",
    "documents": "dokumente",
    "downloads": "downloads",
    "download": "downloads",
    "bilder": "bilder",
    "pictures": "bilder",
    "fotos": "bilder",
    "videos": "videos",
    "filme": "videos",
    "musik": "musik",
    "music": "musik",
}

JON_WORT = re.compile(r"\b(jon[- ]?ordner|jon[- ]?verzeichnis)\b", re.IGNORECASE)

VERBOTEN_TEILE = {
    "windows",
    "system32",
    "syswow64",
    "program files",
    "program files (x86)",
    "programdata",
    "$recycle.bin",
    "system volume information",
    "boot",
    "efi",
}

VERBOTEN_ABSOLUT = (
    "/etc",
    "/bin",
    "/sbin",
    "/usr/bin",
    "/usr/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/var/log",
    "/system",
    "/library",
    "/private/etc",
)

UNGUELTIG = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_NAME = 110


def _heim() -> Path:
    return Path.home()


def bekannte_ordner() -> dict[str, Path]:
    heim = _heim()
    tabelle = {
        "desktop": heim / "Desktop",
        "dokumente": heim / "Documents",
        "downloads": heim / "Downloads",
        "bilder": heim / "Pictures",
        "videos": heim / "Videos",
        "musik": heim / "Music",
    }
    if sys.platform == "win32":
        eins = heim / "OneDrive"
        if eins.is_dir():
            for schluessel, name in (
                ("desktop", "Desktop"),
                ("dokumente", "Documents"),
                ("bilder", "Pictures"),
            ):
                umgeleitet = eins / name
                if umgeleitet.is_dir():
                    tabelle[schluessel] = umgeleitet
    if sys.platform == "darwin":
        tabelle["videos"] = heim / "Movies"
    return tabelle


def saeubern(name: str, standard: str = "Datei") -> str:
    roh = unicodedata.normalize("NFC", str(name or "").strip())
    roh = roh.replace("/", "-").replace("\\", "-")
    roh = UNGUELTIG.sub("", roh).strip(" .")
    roh = re.sub(r"\s+", " ", roh)
    if not roh:
        roh = standard
    if len(roh) > MAX_NAME:
        stamm = Path(roh)
        endung = stamm.suffix[:12]
        roh = stamm.stem[: MAX_NAME - len(endung)] + endung
    return roh


class DateiraumService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bereit = False

    def wurzel(self) -> Path:
        eigene = ""
        try:
            from app.services.settings_service import get_settings_service

            eigene = str(get_settings_service().get().get("jon_ordner", "") or "")
        except Exception as fehler:
            leise(fehler, "services/dateiraum_service")
        if eigene.strip():
            return Path(eigene).expanduser()
        return _heim() / "Jon"

    def sicherstellen(self) -> Path:
        wurzel = self.wurzel()
        with self._lock:
            try:
                wurzel.mkdir(parents=True, exist_ok=True)
                for name in UNTERORDNER:
                    (wurzel / name).mkdir(exist_ok=True)
                self._bereit = True
            except Exception as fehler:
                leise(fehler, "services/dateiraum_service")
        return wurzel

    def ordner(self, name: str) -> Path:
        wurzel = self.sicherstellen()
        ziel = wurzel / name if name in UNTERORDNER else wurzel / "Generated"
        ziel.mkdir(parents=True, exist_ok=True)
        return ziel

    def ordner_fuer_art(self, endung: str) -> Path:
        sauber = str(endung or "").lower().lstrip(".")
        return self.ordner(ART_ORDNER.get(sauber, "Generated"))

    def erlaubte_wurzeln(self) -> list[Path]:
        wurzeln = [self.wurzel(), _heim()]
        try:
            from app.services.settings_service import get_settings_service

            roh = get_settings_service().get().get("freigegebene_ordner", []) or []
            for eintrag in roh:
                pfad = Path(str(eintrag)).expanduser()
                if pfad.is_dir():
                    wurzeln.append(pfad)
        except Exception as fehler:
            leise(fehler, "services/dateiraum_service")
        aufgeloest = []
        for pfad in wurzeln:
            try:
                aufgeloest.append(pfad.resolve())
            except Exception as fehler:
                leise(fehler, "services/dateiraum_service")
        return aufgeloest

    @staticmethod
    def gesperrt(pfad: Path) -> str:
        try:
            text = str(pfad.resolve()).replace("\\", "/").lower()
        except Exception:
            text = str(pfad).replace("\\", "/").lower()
        for anfang in VERBOTEN_ABSOLUT:
            if text == anfang or text.startswith(anfang + "/"):
                return f"Systembereich {anfang} ist gesperrt."
        teile = {t.lower() for t in Path(text).parts}
        treffer = teile & VERBOTEN_TEILE
        if treffer:
            return f"Systemordner {sorted(treffer)[0]} ist gesperrt."
        return ""

    def frei(self, pfad: Path) -> tuple[bool, str]:
        try:
            ziel = pfad.resolve()
        except Exception as exc:
            return False, f"Pfad nicht auflösbar: {exc}"
        sperre = self.gesperrt(ziel)
        if sperre:
            return False, sperre
        for wurzel in self.erlaubte_wurzeln():
            if ziel == wurzel or wurzel in ziel.parents:
                return True, ""
        return (
            False,
            "Dieser Ort liegt ausserhalb der freigegebenen Bereiche. Frei sind Jons "
            "Ordner, dein Benutzerordner und ausdruecklich freigegebene Projektordner.",
        )

    def _wunsch_basis(self, wunsch: str) -> tuple[Path | None, str]:
        text = str(wunsch or "").strip()
        if not text:
            return None, ""
        if JON_WORT.search(text):
            rest = JON_WORT.sub("", text).strip(" /\\-")
            return self.sicherstellen(), rest
        pfad = Path(text).expanduser()
        if pfad.is_absolute():
            return pfad, ""
        teile = [t for t in re.split(r"[\\/]+", text) if t.strip()]
        if not teile:
            return None, ""
        kopf = teile[0].strip().lower()
        bekannt = bekannte_ordner()
        if kopf in WORT_ORDNER:
            basis = bekannt[WORT_ORDNER[kopf]]
            return basis, "/".join(teile[1:])
        for name in UNTERORDNER:
            if kopf == name.lower():
                return self.ordner(name), "/".join(teile[1:])
        return None, text

    def zielordner(self, wunsch: str = "", endung: str = "") -> dict:
        basis, rest = self._wunsch_basis(wunsch)
        if basis is None:
            if rest:
                ziel = self.ordner("Generated") / rest
            else:
                ziel = self.ordner_fuer_art(endung)
        else:
            ziel = basis
            for teil in [t for t in re.split(r"[\\/]+", rest) if t.strip()]:
                ziel = ziel / saeubern(teil, "Ordner")
        erlaubt, grund = self.frei(ziel)
        if not erlaubt:
            return {"error": grund, "pfad": str(ziel)}
        try:
            ziel.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return {"error": f"Ordner liess sich nicht anlegen: {exc}", "pfad": str(ziel)}
        return {"pfad": str(ziel.resolve()), "neu": True}

    def eindeutig(self, ordner: Path, name: str) -> Path:
        sauber = saeubern(name)
        ziel = ordner / sauber
        if not ziel.exists():
            return ziel
        stamm, endung = ziel.stem, ziel.suffix
        for nummer in range(2, 500):
            kandidat = ordner / f"{stamm}-{nummer}{endung}"
            if not kandidat.exists():
                return kandidat
        return ordner / f"{stamm}-{os.getpid()}{endung}"

    def zielpfad(
        self, dateiname: str, wunsch: str = "", ueberschreiben: bool = False
    ) -> dict:
        sauber = saeubern(dateiname)
        endung = Path(sauber).suffix.lstrip(".")
        ordner = self.zielordner(wunsch, endung)
        if ordner.get("error"):
            return ordner
        basis = Path(ordner["pfad"])
        ziel = basis / sauber if ueberschreiben else self.eindeutig(basis, sauber)
        erlaubt, grund = self.frei(ziel)
        if not erlaubt:
            return {"error": grund, "pfad": str(ziel)}
        return {"pfad": str(ziel), "ordner": str(basis), "name": ziel.name}

    def stand(self) -> dict:
        wurzel = self.sicherstellen()
        ordner = []
        for name in UNTERORDNER:
            ziel = wurzel / name
            try:
                anzahl = len([p for p in ziel.iterdir() if p.is_file()])
            except Exception:
                anzahl = 0
            ordner.append({"name": name, "pfad": str(ziel), "dateien": anzahl})
        return {
            "wurzel": str(wurzel),
            "ordner": ordner,
            "bekannt": {k: str(v) for k, v in bekannte_ordner().items()},
            "freigegeben": [str(p) for p in self.erlaubte_wurzeln()],
        }


_service: DateiraumService | None = None


def get_dateiraum_service() -> DateiraumService:
    global _service
    if _service is None:
        _service = DateiraumService()
    return _service
