from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.core.config import DATA_DIR

ORDNER = DATA_DIR / "design"
MAX_GROESSE = 300 * 1024 * 1024
BILDER = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
}
VIDEOS = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".ogv": "video/ogg",
}
GUELTIG = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{2,5}$")


def typ(pfad: Path) -> str:
    endung = pfad.suffix.lower()
    return BILDER.get(endung) or VIDEOS.get(endung) or "application/octet-stream"


class DesignService:
    def ordner(self) -> Path:
        ORDNER.mkdir(parents=True, exist_ok=True)
        return ORDNER

    def _eintrag(self, pfad: Path) -> dict:
        info = pfad.stat()
        return {
            "name": pfad.name,
            "art": "video" if pfad.suffix.lower() in VIDEOS else "bild",
            "groesse": info.st_size,
            "zeit": info.st_mtime,
        }

    async def hochladen(self, name: str, stream) -> dict:
        endung = Path(name or "").suffix.lower()
        if endung not in BILDER and endung not in VIDEOS:
            raise ValueError("Erlaubt sind Bilder (JPG, PNG, WEBP, GIF, AVIF, BMP) und Videos (MP4, WEBM, MOV).")
        pfad = self.ordner() / f"{uuid.uuid4().hex}{endung}"
        groesse = 0
        try:
            with pfad.open("xb") as ziel:
                async for stueck in stream:
                    groesse += len(stueck)
                    if groesse > MAX_GROESSE:
                        raise ValueError("Die Datei ist größer als 300 MB.")
                    ziel.write(stueck)
            if not groesse:
                raise ValueError("Die Datei ist leer.")
        except BaseException:
            pfad.unlink(missing_ok=True)
            raise
        return self._eintrag(pfad)

    def finden(self, name: str) -> Path | None:
        if not GUELTIG.match(name or ""):
            return None
        if Path(name).suffix.lower() not in BILDER and Path(name).suffix.lower() not in VIDEOS:
            return None
        pfad = ORDNER / name
        if not pfad.is_file() or pfad.is_symlink():
            return None
        return pfad

    def liste(self) -> list[dict]:
        if not ORDNER.is_dir():
            return []
        dateien = [self.finden(p.name) for p in ORDNER.iterdir()]
        eintraege = [self._eintrag(p) for p in dateien if p is not None]
        return sorted(eintraege, key=lambda e: e["zeit"], reverse=True)

    def loeschen(self, name: str) -> bool:
        pfad = self.finden(name)
        if pfad is None:
            return False
        pfad.unlink(missing_ok=True)
        return True


_service: DesignService | None = None


def get_design_service() -> DesignService:
    global _service
    if _service is None:
        _service = DesignService()
    return _service
