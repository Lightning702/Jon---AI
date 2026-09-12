from __future__ import annotations

import json
import re
import threading
from datetime import date, datetime, timedelta

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

STAND_DATEI = DATA_DIR / "konsolidierung.json"

TAG_SYSTEM = (
    "Du bist Jons Gedaechtnis. Du bekommst die Ereignisse eines Tages und schreibst "
    "daraus einen kurzen Rueckblick in deutschem Fliesstext (hoechstens 8 Saetze): "
    "was gemacht wurde, was geklappt hat, was schiefging und was offen blieb. "
    "Danach schreibst du eine Zeile 'FAKTEN:' und darunter maximal 6 Zeilen mit "
    "dauerhaft merkenswerten Tatsachen ueber den Nutzer oder seine Projekte, jede "
    "Zeile beginnt mit '- '. Nur Dinge, die auch naechste Woche noch gelten. "
    "Danach eine Zeile 'MORGEN:' und darunter maximal 4 Zeilen mit dem, was daraus "
    "als naechstes ansteht, jede Zeile beginnt mit '- '."
)

KONFLIKT_SYSTEM = (
    "Zwei gespeicherte Tatsachen ueber denselben Gegenstand widersprechen sich "
    "moeglicherweise. Antworte mit genau einem Wort: 'A' wenn nur die erste gilt, "
    "'B' wenn nur die zweite gilt, 'BEIDE' wenn beide nebeneinander stimmen koennen."
)


def _heute() -> date:
    return date.today()


class KonsolidierungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._laeuft = False
        self._stand = self._laden()

    def _laden(self) -> dict:
        if STAND_DATEI.exists():
            try:
                roh = json.loads(STAND_DATEI.read_text(encoding="utf-8"))
                if isinstance(roh, dict):
                    return roh
            except Exception as _fehler:
                leise(_fehler, "services/konsolidierung_service")
        return {"letzter_tag": "", "laeufe": 0, "letzter_bericht": ""}

    def _sichern(self) -> None:
        try:
            atomic_write_text(
                STAND_DATEI,
                json.dumps(self._stand, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as _fehler:
            leise(_fehler, "services/konsolidierung_service")

    def faellig(self) -> bool:
        gestern = (_heute() - timedelta(days=1)).isoformat()
        with self._lock:
            return self._stand.get("letzter_tag", "") != gestern

    def stand(self) -> dict:
        with self._lock:
            return dict(self._stand)

    async def _konflikte_klaeren(self, grenze: int = 6) -> list[str]:
        from app.services.llm import complete
        from app.services.memory_service import MemoryService

        speicher = MemoryService()
        entschieden: list[str] = []
        for konflikt in speicher.konflikte()[:grenze]:
            frage = (
                f"A: {konflikt['a']['content']}\nB: {konflikt['b']['content']}\n"
                "Welche gilt?"
            )
            try:
                antwort = (await complete(KONFLIKT_SYSTEM, frage, max_tokens=12)).strip()
            except Exception as _fehler:
                leise(_fehler, "services/konsolidierung_service")
                continue
            wahl = antwort.upper()[:5]
            if wahl.startswith("A"):
                speicher.delete(konflikt["b"]["id"])
                entschieden.append(f"verworfen: {konflikt['b']['content'][:60]}")
            elif wahl.startswith("B"):
                speicher.delete(konflikt["a"]["id"])
                entschieden.append(f"verworfen: {konflikt['a']['content'][:60]}")
        return entschieden

    @staticmethod
    def _abschnitte(text: str) -> tuple[str, list[str], list[str]]:
        rueckblick = text
        fakten: list[str] = []
        morgen: list[str] = []
        teile = re.split(r"(?im)^\s*(FAKTEN|MORGEN)\s*:\s*$", text)
        if len(teile) >= 3:
            rueckblick = teile[0].strip()
            for stelle in range(1, len(teile) - 1, 2):
                marke = teile[stelle].upper()
                block = teile[stelle + 1]
                zeilen = [
                    z.strip("-• \t")
                    for z in block.splitlines()
                    if z.strip().startswith(("-", "•"))
                ]
                if marke == "FAKTEN":
                    fakten = [z for z in zeilen if len(z) > 4][:6]
                else:
                    morgen = [z for z in zeilen if len(z) > 4][:4]
        return rueckblick.strip(), fakten, morgen

    async def lauf(self, tag: str = "gestern") -> dict:
        with self._lock:
            if self._laeuft:
                return {"ok": False, "grund": "laeuft bereits"}
            self._laeuft = True
        try:
            return await self._lauf_intern(tag)
        finally:
            with self._lock:
                self._laeuft = False

    async def _lauf_intern(self, tag: str) -> dict:
        from app.services.ereignis_service import get_ereignis_service
        from app.services.llm import complete
        from app.services.memory_service import MemoryService
        from app.services.weltmodell_service import get_weltmodell_service
        from app.services.ziel_service import get_ziel_service

        ereignisse = get_ereignis_service()
        bild = ereignisse.tagesbild(tag)
        if not bild["anzahl"]:
            with self._lock:
                self._stand["letzter_tag"] = (_heute() - timedelta(days=1)).isoformat()
                self._sichern()
            return {"ok": True, "leer": True, "zeitraum": bild["zeitraum"]}

        zeilen = [
            f"{e['zeit']} [{e['art']}] {e['titel']}: {e['detail'][:160]}"
            for e in ereignisse.spanne(
                datetime.fromisoformat(bild["zeitraum"]["von"]),
                datetime.fromisoformat(bild["zeitraum"]["bis"]),
                limit=300,
            )
        ]
        roh = "\n".join(zeilen)[:14000]
        try:
            antwort = await complete(
                TAG_SYSTEM,
                f"Tag: {bild['zeitraum']['beschreibung']}\n\nEreignisse:\n{roh}",
                max_tokens=1200,
                temperature=0.3,
            )
        except Exception as exc:
            return {"ok": False, "fehler": str(exc)}

        rueckblick, fakten, morgen = self._abschnitte(antwort)
        speicher = MemoryService()
        gemerkt = []
        for satz in fakten:
            ergebnis = speicher.add(satz, source="konsolidierung", wichtigkeit=0.65)
            if not ergebnis.get("duplicate"):
                gemerkt.append(satz)
        welt = get_weltmodell_service()
        for satz in fakten:
            welt.erkennen(satz)

        ziele = get_ziel_service()
        neue_ziele = []
        for satz in morgen:
            ziel = ziele.anlegen(
                satz[:200],
                beschreibung=f"Aus dem Rueckblick auf {bild['zeitraum']['beschreibung']}",
                wichtigkeit=0.5,
                quelle="konsolidierung",
            )
            if ziel.get("id"):
                neue_ziele.append(ziel["titel"])

        konflikte = await self._konflikte_klaeren()
        vergessen = speicher.aufraeumen()
        alt = ereignisse.aufraeumen()
        nacharbeit = await self._nacharbeit()

        if rueckblick:
            ereignisse.notieren(
                "erkenntnis",
                f"Rueckblick {bild['zeitraum']['beschreibung']}",
                rueckblick,
                quelle="konsolidierung",
                bedeutung=0.85,
            )

        with self._lock:
            self._stand["letzter_tag"] = (_heute() - timedelta(days=1)).isoformat()
            self._stand["laeufe"] = int(self._stand.get("laeufe", 0)) + 1
            self._stand["letzter_bericht"] = rueckblick[:1500]
            self._sichern()

        return {
            "ok": True,
            "zeitraum": bild["zeitraum"],
            "ereignisse": bild["anzahl"],
            "rueckblick": rueckblick,
            "gemerkt": gemerkt,
            "neue_ziele": neue_ziele,
            "konflikte_geklaert": konflikte,
            "vergessen": vergessen,
            "alte_ereignisse_entfernt": alt,
            **nacharbeit,
        }

    async def _nacharbeit(self) -> dict:
        bericht: dict = {}
        try:
            from app.services.erwartung_service import get_erwartung_service

            bericht["kalibrierung"] = get_erwartung_service().kalibrierung(7)
        except Exception as _fehler:
            leise(_fehler, "services/konsolidierung_service")
        try:
            from app.services.neugier_service import get_neugier_service
            from app.services.settings_service import get_settings_service

            dienst = get_neugier_service()
            dienst.aus_konflikten()
            dienst.aus_weltmodell()
            einstellungen = get_settings_service().get()
            if einstellungen.get("neugier_auto", False):
                bericht["fragen"] = await dienst.lauf(
                    int(einstellungen.get("neugier_pro_lauf", 3) or 3)
                )
            else:
                bericht["fragen"] = {"offen": len(dienst.offene(50))}
        except Exception as _fehler:
            leise(_fehler, "services/konsolidierung_service")
        try:
            from app.services.fertigkeit_service import get_fertigkeit_service

            bericht["fertigkeit_vorschlaege"] = [
                v["name"] for v in get_fertigkeit_service().entdecken()[:5]
            ]
        except Exception as _fehler:
            leise(_fehler, "services/konsolidierung_service")
        return bericht


_service: KonsolidierungService | None = None


def get_konsolidierung_service() -> KonsolidierungService:
    global _service
    if _service is None:
        _service = KonsolidierungService()
    return _service
