from __future__ import annotations

import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise

SCREENSHOT_TAGE = 14
SCREENSHOT_MAX = 200
PROFIL_MAX_MB = 800
SITZUNG_LEERLAUF_S = 1800
CACHE_ORDNER = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "Service Worker/CacheStorage",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "GrShaderCache",
    "ShaderCache",
)


def _groesse_mb(pfad: Path) -> float:
    gesamt = 0
    try:
        for datei in pfad.rglob("*"):
            if datei.is_file():
                gesamt += datei.stat().st_size
    except Exception as _fehler:
        leise(_fehler, "services/pflege_service")
    return round(gesamt / (1024 * 1024), 1)


def screenshots_aufraeumen(tage: int = SCREENSHOT_TAGE) -> dict:
    ordner = DATA_DIR / "browser"
    if not ordner.exists():
        return {"geloescht": 0, "behalten": 0}
    grenze = datetime.now() - timedelta(days=max(1, tage))
    dateien = sorted(
        ordner.glob("screenshot-*.png"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    geloescht = 0
    for nummer, datei in enumerate(dateien):
        zu_alt = datetime.fromtimestamp(datei.stat().st_mtime) < grenze
        zu_viele = nummer >= SCREENSHOT_MAX
        if zu_alt or zu_viele:
            try:
                datei.unlink()
                geloescht += 1
            except Exception as _fehler:
                leise(_fehler, "services/pflege_service")
    return {"geloescht": geloescht, "behalten": len(dateien) - geloescht}


def profil_aufraeumen(grenze_mb: int = PROFIL_MAX_MB) -> dict:
    basis = DATA_DIR / "browser"
    if not basis.exists():
        return {"geleert": [], "groesse_mb": 0.0}
    geleert: list[str] = []
    gesamt = 0.0
    for profil in list(basis.glob("profil*")):
        if not profil.is_dir():
            continue
        groesse = _groesse_mb(profil)
        gesamt += groesse
        if groesse < grenze_mb:
            continue
        for name in CACHE_ORDNER:
            ziel = profil / name
            if ziel.exists():
                try:
                    shutil.rmtree(ziel, ignore_errors=True)
                    geleert.append(f"{profil.name}/{name}")
                except Exception as _fehler:
                    leise(_fehler, "services/pflege_service")
    return {"geleert": geleert, "groesse_mb": round(gesamt, 1)}


def leerlauf_browser_schliessen(leerlauf: int = SITZUNG_LEERLAUF_S) -> list[str]:
    from app.services.browser.manager import alle_manager
    from app.services.browser.sitzung import alter, vergessen

    geschlossen: list[str] = []
    for schluessel, manager in alle_manager().items():
        if not manager.offen:
            continue
        if alter(schluessel) < leerlauf:
            continue
        try:
            manager.schliessen()
            vergessen(schluessel)
            geschlossen.append(schluessel)
        except Exception as _fehler:
            leise(_fehler, "services/pflege_service")
    return geschlossen


def alles(tage: int = SCREENSHOT_TAGE) -> dict:
    start = time.time()
    ergebnis = {
        "screenshots": screenshots_aufraeumen(tage),
        "profile": profil_aufraeumen(),
        "browser_geschlossen": leerlauf_browser_schliessen(),
    }
    try:
        from app.services.auftrag_service import get_auftrag_service
        from app.services.ereignis_service import get_ereignis_service

        ergebnis["auftraege"] = get_auftrag_service().aufraeumen()
        ergebnis["ereignisse"] = get_ereignis_service().aufraeumen()
    except Exception as _fehler:
        leise(_fehler, "services/pflege_service")
    ergebnis["dauer"] = round(time.time() - start, 2)
    return ergebnis
