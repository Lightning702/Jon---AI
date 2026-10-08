from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise

CACHE = DATA_DIR / "ansicht_cache"
BREITE = 1600
SEITEN_MAX = 300

FOLIEN_SKRIPT = r"""
param([string]$quelle, [string]$ziel, [int]$breite)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject PowerPoint.Application
$offen = $app.Presentations.Count
$p = $app.Presentations.Open($quelle, -1, 0, 0)
try {
  $w = [double]$p.PageSetup.SlideWidth
  $h = [double]$p.PageSetup.SlideHeight
  $hoehe = [int]($breite * $h / $w)
  $n = $p.Slides.Count
  for ($i = 1; $i -le $n; $i++) {
    $p.Slides.Item($i).Export((Join-Path $ziel ("seite-$i.png")), 'PNG', $breite, $hoehe)
  }
  Write-Output $n
} finally {
  $p.Close()
  if ($offen -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
"""

WORD_SKRIPT = r"""
param([string]$quelle, [string]$ziel)
$ErrorActionPreference = 'Stop'
$app = New-Object -ComObject Word.Application
$app.Visible = $false
$app.DisplayAlerts = 0
$offen = $app.Documents.Count
$d = $app.Documents.Open($quelle, $false, $true, $false)
try {
  $d.ExportAsFixedFormat($ziel, 17)
} finally {
  $d.Close(0)
  if ($offen -eq 0 -and $app.Documents.Count -eq 0) { $app.Quit() }
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
"""

_sperre = threading.Lock()
_stand: dict[str, dict] = {}
_stand_sperre = threading.Lock()


def _schluessel(pfad: Path) -> str:
    info = pfad.stat()
    roh = f"{pfad.resolve()}|{info.st_mtime_ns}|{info.st_size}"
    return hashlib.sha1(roh.encode("utf-8")).hexdigest()[:20]


def _com_da(programm: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{programm}.Application\\CLSID"))
        return True
    except OSError:
        return False


def _soffice() -> str:
    for name in ("soffice", "libreoffice"):
        gefunden = shutil.which(name)
        if gefunden:
            return gefunden
    for kandidat in (Path("C:/Program Files/LibreOffice/program/soffice.exe"), Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"), Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")):
        if kandidat.is_file():
            return str(kandidat)
    return ""


def moeglich(endung: str) -> bool:
    endung = endung.lower().lstrip(".")
    raster = _pdf_rasterer() is not None
    if endung == "pdf":
        return raster
    if endung in ("pptx", "ppt", "odp"):
        return _com_da("PowerPoint") or (raster and bool(_soffice()))
    if endung in ("docx", "doc", "odt", "rtf"):
        return raster and (_com_da("Word") or bool(_soffice()))
    return False


def _pdf_rasterer():
    try:
        import pypdfium2

        return pypdfium2
    except Exception:
        return "pdftoppm" if shutil.which("pdftoppm") else None


def _powershell(skript: str, *argumente: str, zeit: int = 240) -> str:
    datei = CACHE / f"skript-{threading.get_ident()}.ps1"
    datei.write_text(skript, encoding="utf-8-sig")
    try:
        ergebnis = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(datei), *argumente],
            capture_output=True, timeout=zeit, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    finally:
        datei.unlink(missing_ok=True)
    if ergebnis.returncode != 0:
        fehler = ergebnis.stderr.decode("utf-8", errors="replace") or ergebnis.stdout.decode("utf-8", errors="replace")
        raise RuntimeError(fehler.strip()[:400] or f"Exit {ergebnis.returncode}")
    return ergebnis.stdout.decode("utf-8", errors="replace").strip()


def _pdf_zu_bildern(pdf: Path, ziel: Path) -> int:
    rasterer = _pdf_rasterer()
    if rasterer is None:
        raise RuntimeError("Kein PDF-Renderer vorhanden.")
    if rasterer == "pdftoppm":
        subprocess.run(["pdftoppm", "-png", "-scale-to", str(BREITE), "-l", str(SEITEN_MAX), str(pdf), str(ziel / "roh")], check=True, capture_output=True, timeout=300)
        bilder = sorted(ziel.glob("roh*.png"), key=lambda p: int("".join(z for z in p.stem if z.isdigit()) or 0))
        for nummer, bild in enumerate(bilder, start=1):
            bild.rename(ziel / f"seite-{nummer}.png")
        return len(bilder)
    dokument = rasterer.PdfDocument(str(pdf))
    try:
        anzahl = min(len(dokument), SEITEN_MAX)
        for index in range(anzahl):
            seite = dokument[index]
            breite = seite.get_width() or 612
            bild = seite.render(scale=min(4.0, BREITE / breite)).to_pil()
            bild.convert("RGB").save(ziel / f"seite-{index + 1}.png", format="PNG", optimize=False)
            seite.close()
        return anzahl
    finally:
        dokument.close()


def _office_zu_pdf(quelle: Path, ziel: Path) -> Path:
    programm = _soffice()
    if not programm:
        raise RuntimeError("Weder Microsoft Office noch LibreOffice gefunden.")
    subprocess.run([programm, "--headless", "--convert-to", "pdf", "--outdir", str(ziel), str(quelle)], check=True, capture_output=True, timeout=300)
    pdf = ziel / (quelle.stem + ".pdf")
    if not pdf.is_file():
        raise RuntimeError("LibreOffice hat keine PDF erzeugt.")
    return pdf


def _rendern(pfad: Path, ordner: Path) -> int:
    endung = pfad.suffix.lower().lstrip(".")
    kopie = ordner / f"quelle{pfad.suffix.lower()}"
    shutil.copy2(pfad, kopie)
    try:
        if endung == "pdf":
            return _pdf_zu_bildern(kopie, ordner)
        if endung in ("pptx", "ppt", "odp") and _com_da("PowerPoint"):
            try:
                return int(_powershell(FOLIEN_SKRIPT, str(kopie), str(ordner), str(BREITE)).splitlines()[-1])
            except Exception as fehler:
                leise(fehler, "services/office_render")
                if not _soffice():
                    raise
        if endung in ("docx", "doc", "odt", "rtf") and _com_da("Word"):
            pdf = ordner / "druck.pdf"
            try:
                _powershell(WORD_SKRIPT, str(kopie), str(pdf))
                return _pdf_zu_bildern(pdf, ordner)
            except Exception as fehler:
                leise(fehler, "services/office_render")
                if not _soffice():
                    raise
        return _pdf_zu_bildern(_office_zu_pdf(kopie, ordner), ordner)
    finally:
        kopie.unlink(missing_ok=True)


def _arbeiten(pfad: Path, schluessel: str) -> None:
    ordner = CACHE / schluessel
    try:
        with _sperre:
            ordner.mkdir(parents=True, exist_ok=True)
            for alt in ordner.glob("seite-*.png"):
                alt.unlink(missing_ok=True)
            anzahl = _rendern(pfad, ordner)
            (ordner / "fertig.json").write_text(json.dumps({"seiten": anzahl, "zeit": time.time()}), encoding="utf-8")
        with _stand_sperre:
            _stand[schluessel] = {"status": "fertig", "seiten": anzahl}
        _aufraeumen()
    except Exception as fehler:
        leise(fehler, "services/office_render")
        with _stand_sperre:
            _stand[schluessel] = {"status": "fehler", "fehler": str(fehler)[:300]}


def _aufraeumen() -> None:
    try:
        ordner = sorted((o for o in CACHE.iterdir() if o.is_dir()), key=lambda o: o.stat().st_mtime, reverse=True)
    except OSError:
        return
    for alt in ordner[40:]:
        shutil.rmtree(alt, ignore_errors=True)


def stand(pfad: Path, starten: bool = True) -> dict:
    if not moeglich(pfad.suffix):
        return {"status": "nicht_moeglich"}
    schluessel = _schluessel(pfad)
    fertig = CACHE / schluessel / "fertig.json"
    if fertig.is_file():
        try:
            daten = json.loads(fertig.read_text(encoding="utf-8"))
            return {"status": "fertig", "seiten": int(daten.get("seiten", 0)), "version": schluessel}
        except Exception as fehler:
            leise(fehler, "services/office_render")
    with _stand_sperre:
        bekannt = _stand.get(schluessel)
        if bekannt and bekannt["status"] == "laeuft":
            return {**bekannt, "version": schluessel}
        if bekannt and bekannt["status"] == "fehler":
            return {**bekannt, "version": schluessel}
        if not starten:
            return {"status": "offen", "version": schluessel}
        _stand[schluessel] = {"status": "laeuft"}
    CACHE.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_arbeiten, args=(pfad, schluessel), daemon=True, name="jon-ansicht").start()
    return {"status": "laeuft", "version": schluessel}


def seitenbild(pfad: Path, nummer: int) -> Path:
    bild = CACHE / _schluessel(pfad) / f"seite-{int(nummer)}.png"
    if not bild.is_file():
        raise FileNotFoundError("Diese Seite ist noch nicht gerendert.")
    return bild
