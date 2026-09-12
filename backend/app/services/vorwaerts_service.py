from __future__ import annotations

import json
from pathlib import Path

from app.core.fehler import leise

DATEI_WERKZEUGE = {
    "write_file",
    "append_file",
    "datei_erstellen",
    "make_dir",
    "ordner_anlegen",
    "delete_path",
    "move_path",
    "copy_path",
    "unzip",
    "zip_paths",
    "download_file",
    "create_image",
    "create_pptx",
    "blender_szene",
    "blender_render",
    "blender_export",
}

LESEND = {
    "read_file",
    "list_dir",
    "search_files",
    "read_pdf",
    "read_pptx",
    "dateien_finden",
    "dateiraum",
    "umgebung",
    "netz_status",
    "was_war",
    "verlauf_heute",
}


def _pfade(werkzeug: str, args: dict) -> list[Path]:
    gefunden: list[Path] = []
    for schluessel in ("path", "pfad", "destination", "source", "datei", "ziel"):
        wert = args.get(schluessel)
        if isinstance(wert, str) and wert.strip():
            gefunden.append(Path(wert).expanduser())
    for schluessel in ("sources", "paths", "dateien"):
        for wert in args.get(schluessel) or []:
            if isinstance(wert, str) and wert.strip():
                gefunden.append(Path(wert).expanduser())
    return gefunden


def _dateiname_raten(werkzeug: str, args: dict) -> str:
    name = str(args.get("dateiname") or args.get("titel") or "").strip()
    art = str(args.get("art") or "").strip().lstrip(".")
    if werkzeug == "datei_erstellen" and name:
        return name if Path(name).suffix else f"{name}.{art or 'txt'}"
    if werkzeug == "create_pptx":
        return f"{str(args.get('title', 'Praesentation'))}.pptx"
    return ""


class VorwaertsService:
    def vorhersagen(self, werkzeug: str, args: dict | None = None) -> dict:
        werte = args or {}
        if werkzeug in LESEND:
            return {
                "werkzeug": werkzeug,
                "veraendert": False,
                "erwartung": "liest nur, nichts aendert sich",
                "pruefbar": False,
            }
        if werkzeug not in DATEI_WERKZEUGE:
            return {
                "werkzeug": werkzeug,
                "veraendert": True,
                "erwartung": "Wirkung ausserhalb des Dateisystems",
                "pruefbar": False,
            }
        pfade = _pfade(werkzeug, werte)
        geraten = _dateiname_raten(werkzeug, werte)
        entsteht: list[str] = []
        verschwindet: list[str] = []
        if werkzeug in ("delete_path",):
            verschwindet = [str(p) for p in pfade]
        elif werkzeug == "move_path":
            if len(pfade) >= 2:
                verschwindet = [str(pfade[0])]
                entsteht = [str(pfade[1])]
        elif werkzeug in ("make_dir", "ordner_anlegen"):
            entsteht = [str(p) for p in pfade] or [str(werte.get("name", ""))]
        else:
            entsteht = [str(p) for p in pfade]
            if geraten and not entsteht:
                entsteht = [geraten]
        vorher = {str(p): p.exists() for p in pfade}
        return {
            "werkzeug": werkzeug,
            "veraendert": True,
            "entsteht": [e for e in entsteht if e],
            "verschwindet": [v for v in verschwindet if v],
            "vorher": vorher,
            "erwartung": self._satz(werkzeug, entsteht, verschwindet),
            "pruefbar": bool(entsteht or verschwindet),
        }

    @staticmethod
    def _satz(werkzeug: str, entsteht: list[str], verschwindet: list[str]) -> str:
        teile = []
        if entsteht:
            teile.append("danach gibt es " + ", ".join(Path(e).name for e in entsteht[:3]))
        if verschwindet:
            teile.append(
                "danach fehlt " + ", ".join(Path(v).name for v in verschwindet[:3])
            )
        return f"{werkzeug}: " + (" und ".join(teile) or "Wirkung unklar")

    def abgleichen(self, vorhersage: dict, ergebnis: str = "") -> dict:
        if not vorhersage or not vorhersage.get("pruefbar"):
            return {}
        falsch: list[str] = []
        for pfad in vorhersage.get("entsteht", []):
            if pfad and not Path(pfad).exists():
                falsch.append(f"{Path(pfad).name} ist nicht entstanden")
        for pfad in vorhersage.get("verschwindet", []):
            if pfad and Path(pfad).exists():
                falsch.append(f"{Path(pfad).name} ist noch da")
        getroffen = not falsch
        return {
            "getroffen": getroffen,
            "abweichungen": falsch,
            "werkzeug": vorhersage.get("werkzeug", ""),
        }

    def lernen(self, abgleich: dict) -> None:
        if not abgleich or abgleich.get("getroffen", True):
            return
        werkzeug = abgleich.get("werkzeug", "")
        text = (
            f"{werkzeug} meldete Erfolg, aber: "
            + "; ".join(abgleich.get("abweichungen", [])[:3])
        )
        try:
            from app.services.erfahrung_service import (
                KLAPPT_NICHT,
                get_erfahrung_service,
            )

            get_erfahrung_service().notieren(
                f"werkzeug:{werkzeug}", text, KLAPPT_NICHT, 0.85
            )
        except Exception as fehler:
            leise(fehler, "services/vorwaerts_service")
        try:
            from app.services.ereignis_service import get_ereignis_service

            get_ereignis_service().notieren(
                "ueberraschung",
                f"{werkzeug} hat die Welt nicht wie erwartet veraendert",
                text,
                quelle="denken",
                bedeutung=0.75,
                gelungen=False,
            )
        except Exception as fehler:
            leise(fehler, "services/vorwaerts_service")

    def durchspielen(self, schritte: list[dict]) -> dict:
        welt: dict[str, bool] = {}
        ablauf = []
        probleme = []
        for stelle, schritt in enumerate(schritte, 1):
            werkzeug = str(schritt.get("werkzeug", ""))
            args = schritt.get("args") or {}
            sicht = self.vorhersagen(werkzeug, args)
            for pfad in sicht.get("verschwindet", []):
                if welt.get(pfad) is False:
                    probleme.append(
                        f"Schritt {stelle} loescht {Path(pfad).name}, das vorher schon weg war"
                    )
                welt[pfad] = False
            for pfad in sicht.get("entsteht", []):
                welt[pfad] = True
            for schluessel, da in (sicht.get("vorher") or {}).items():
                if welt.get(schluessel) is False and da:
                    probleme.append(
                        f"Schritt {stelle} braucht {Path(schluessel).name}, "
                        "das ein frueherer Schritt entfernt hat"
                    )
            ablauf.append({"schritt": stelle, "erwartung": sicht.get("erwartung", "")})
        return {
            "schritte": ablauf,
            "am_ende_da": sorted([p for p, da in welt.items() if da]),
            "am_ende_weg": sorted([p for p, da in welt.items() if not da]),
            "probleme": probleme,
        }


_service: VorwaertsService | None = None


def get_vorwaerts_service() -> VorwaertsService:
    global _service
    if _service is None:
        _service = VorwaertsService()
    return _service
