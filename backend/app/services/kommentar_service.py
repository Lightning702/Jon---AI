from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text

DATEI = DATA_DIR / "datei_kommentare.json"
MAX_TEXT = 4000


def _schluessel(pfad: str | Path) -> str:
    try:
        return str(Path(pfad).expanduser().resolve()).lower()
    except OSError:
        return str(pfad).lower()


class KommentarService:
    def __init__(self, datei: Path | None = None) -> None:
        self.datei = Path(datei or DATEI)
        self._lock = threading.Lock()

    def _laden(self) -> dict:
        try:
            daten = json.loads(self.datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return daten if isinstance(daten, dict) else {}

    def _speichern(self, daten: dict) -> None:
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.datei, json.dumps(daten, ensure_ascii=False))

    def liste(self, pfad: str | Path, offen: bool = False) -> list[dict]:
        eintraege = self._laden().get(_schluessel(pfad), [])
        if offen:
            eintraege = [e for e in eintraege if not e.get("erledigt")]
        return sorted(eintraege, key=lambda e: (int((e.get("stelle") or {}).get("folie") or (e.get("stelle") or {}).get("seite") or 0), e.get("zeit", 0)))

    def anlegen(self, pfad: str | Path, text: str, stelle: dict | None = None, autor: str = "nutzer") -> dict:
        inhalt = str(text or "").strip()[:MAX_TEXT]
        if not inhalt:
            raise ValueError("Der Kommentar ist leer.")
        sauber = {k: v for k, v in (stelle or {}).items() if k in ("art", "folie", "seite", "form", "block", "blatt", "zelle", "zeile", "x", "y", "auszug", "bezeichnung") and v not in (None, "")}
        if "auszug" in sauber:
            sauber["auszug"] = str(sauber["auszug"])[:300]
        eintrag = {"id": uuid.uuid4().hex[:10], "text": inhalt, "stelle": sauber, "autor": autor, "zeit": time.time(), "erledigt": False}
        with self._lock:
            daten = self._laden()
            daten.setdefault(_schluessel(pfad), []).append(eintrag)
            self._speichern(daten)
        return eintrag

    def aendern(self, kennung: str, erledigt: bool | None = None, text: str | None = None, antwort: str | None = None) -> dict | None:
        with self._lock:
            daten = self._laden()
            for eintraege in daten.values():
                for eintrag in eintraege:
                    if eintrag.get("id") != kennung:
                        continue
                    if erledigt is not None:
                        eintrag["erledigt"] = bool(erledigt)
                    if text is not None and text.strip():
                        eintrag["text"] = text.strip()[:MAX_TEXT]
                    if antwort is not None:
                        eintrag["antwort"] = antwort.strip()[:MAX_TEXT]
                    self._speichern(daten)
                    return eintrag
        return None

    def loeschen(self, kennung: str) -> bool:
        with self._lock:
            daten = self._laden()
            for schluessel, eintraege in list(daten.items()):
                rest = [e for e in eintraege if e.get("id") != kennung]
                if len(rest) != len(eintraege):
                    if rest:
                        daten[schluessel] = rest
                    else:
                        daten.pop(schluessel)
                    self._speichern(daten)
                    return True
        return False


def beschreibung(stelle: dict) -> str:
    teile = []
    if stelle.get("folie"):
        teile.append(f"Folie {stelle['folie']}")
    if stelle.get("seite"):
        teile.append(f"Seite {stelle['seite']}")
    if stelle.get("blatt"):
        teile.append(f"Blatt {stelle['blatt']}")
    if stelle.get("zelle"):
        teile.append(f"Zelle {stelle['zelle']}")
    if stelle.get("form") not in (None, ""):
        teile.append(f"Element {stelle['form']}")
    if stelle.get("block") not in (None, ""):
        teile.append(f"Absatz {stelle['block']}")
    if stelle.get("zeile"):
        teile.append(f"Zeile {stelle['zeile']}")
    if stelle.get("bezeichnung"):
        teile.append(str(stelle["bezeichnung"]))
    if stelle.get("auszug"):
        teile.append(f"„{str(stelle['auszug'])[:120]}“")
    return ", ".join(teile) or "ganze Datei"


_service: KommentarService | None = None


def get_kommentar_service() -> KommentarService:
    global _service
    if _service is None:
        _service = KommentarService()
    return _service
