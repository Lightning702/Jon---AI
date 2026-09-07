from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime

from app.core.config import DATA_DIR
from app.core.store import atomic_write_text

DATEI = DATA_DIR / "verlauf_zusammenfassungen.json"
MAX_ZEICHEN = 1400
MIN_NEUE = 2
MAX_QUELLE = 12000

SYSTEM = (
    "Du fuehrst ein laufendes Gedaechtnisprotokoll eines Gespraechs zwischen dem "
    "Nutzer und dem Assistenten Jon. Schreibe eine dichte, sachliche Zusammenfassung "
    "in deutschem Fliesstext, hoechstens 12 Saetze. Behalte unbedingt: getroffene "
    "Entscheidungen, zugesagte Aufgaben, genannte Namen, Zahlen, Pfade, Termine, "
    "offene Punkte und was der Nutzer ausdruecklich nicht will. Lass Hoeflichkeiten, "
    "Wiederholungen und Zwischenschritte weg. Keine Aufzaehlung, keine Ueberschrift, "
    "kein Vorwort - nur die Zusammenfassung."
)


class VerlaufService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._daten = self._laden()
        self._laeuft: set[str] = set()

    def _laden(self) -> dict:
        if DATEI.exists():
            try:
                roh = json.loads(DATEI.read_text(encoding="utf-8"))
                if isinstance(roh, dict):
                    return roh
            except Exception:
                return {}
        return {}

    def _sichern(self) -> None:
        try:
            atomic_write_text(
                DATEI,
                json.dumps(self._daten, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return

    def zusammenfassung(self, gespraech: str) -> str:
        if not gespraech:
            return ""
        with self._lock:
            eintrag = self._daten.get(gespraech) or {}
        return str(eintrag.get("text", ""))

    def stand(self, gespraech: str) -> int:
        with self._lock:
            eintrag = self._daten.get(gespraech) or {}
        return int(eintrag.get("stand", 0) or 0)

    def setzen(self, gespraech: str, text: str, stand: int) -> None:
        with self._lock:
            self._daten[gespraech] = {
                "text": text[:MAX_ZEICHEN],
                "stand": stand,
                "aktualisiert": datetime.now().isoformat(timespec="seconds"),
            }
            self._sichern()

    def loeschen(self, gespraech: str) -> None:
        with self._lock:
            if self._daten.pop(gespraech, None) is not None:
                self._sichern()

    async def _bauen(self, gespraech: str, roh: str, stand: int) -> None:
        from app.services.llm import complete

        try:
            alt = self.zusammenfassung(gespraech)
            frage = roh if not alt else f"Bisheriges Protokoll:\n{alt}\n\nNeu dazu:\n{roh}"
            text = await complete(SYSTEM, frage[:MAX_QUELLE], max_tokens=700, temperature=0.2)
            if text.strip():
                self.setzen(gespraech, text.strip(), stand)
        except Exception:
            return
        finally:
            with self._lock:
                self._laeuft.discard(gespraech)

    def planen(self, gespraech: str, nachrichten: list, stand: int) -> None:
        if not gespraech or not nachrichten:
            return
        if stand - self.stand(gespraech) < MIN_NEUE:
            return
        with self._lock:
            if gespraech in self._laeuft:
                return
            self._laeuft.add(gespraech)
        zeilen = []
        for nachricht in nachrichten[-40:]:
            rolle = getattr(nachricht, "role", "")
            inhalt = str(getattr(nachricht, "content", ""))[:1500]
            if rolle and inhalt:
                zeilen.append(f"{'Nutzer' if rolle == 'user' else 'Jon'}: {inhalt}")
        roh = "\n".join(zeilen)
        if not roh.strip():
            with self._lock:
                self._laeuft.discard(gespraech)
            return
        try:
            schleife = asyncio.get_running_loop()
        except RuntimeError:
            with self._lock:
                self._laeuft.discard(gespraech)
            return
        schleife.create_task(self._bauen(gespraech, roh, stand))


_service: VerlaufService | None = None


def get_verlauf_service() -> VerlaufService:
    global _service
    if _service is None:
        _service = VerlaufService()
    return _service
