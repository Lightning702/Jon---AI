from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import ActionLog, Erwartung

SCHWELLE = 0.45
STARK = 0.7
CACHE_SEKUNDEN = 120
FENSTER_TAGE = 30
MIN_BEOBACHTUNGEN = 3
AUFBEWAHRUNG_TAGE = 60
GRUNDVERTRAUEN = 0.78
GRUNDVERTRAUEN_UNSICHER = 0.6

UNSICHERE = (
    "run_powershell",
    "run_cmd",
    "browser_",
    "android_",
    "phone_",
    "download",
    "mail_",
    "websuche",
)


def _jetzt() -> datetime:
    return datetime.now()


def _unsicher(werkzeug: str) -> bool:
    return any(werkzeug.startswith(teil) or werkzeug == teil for teil in UNSICHERE)


class ErwartungService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._quoten: dict[str, tuple[float, int]] = {}
        self._quoten_zeit = 0.0
        self._dauern: dict[str, tuple[float, int]] = {}
        self._dauern_zeit = 0.0

    def _zeile(self, eintrag: Erwartung) -> dict:
        return {
            "id": eintrag.id,
            "zeit": eintrag.zeit.isoformat(timespec="seconds") if eintrag.zeit else "",
            "werkzeug": eintrag.werkzeug,
            "bereich": eintrag.bereich or "",
            "erwartet": eintrag.erwartet or "",
            "zutrauen": round(float(eintrag.zutrauen or 0.0), 2),
            "dauer_erwartet": round(float(eintrag.dauer_erwartet or 0.0), 2),
            "offen": bool(eintrag.offen),
            "gelungen": bool(eintrag.gelungen),
            "dauer": round(float(eintrag.dauer or 0.0), 2),
            "ueberraschung": round(float(eintrag.ueberraschung or 0.0), 2),
            "notiz": eintrag.notiz or "",
        }

    def _erfolgsquoten(self) -> dict[str, tuple[float, int]]:
        jetzt = time.time()
        if self._quoten and jetzt - self._quoten_zeit < CACHE_SEKUNDEN:
            return self._quoten
        quoten: dict[str, tuple[float, int]] = {}
        try:
            grenze = _jetzt() - timedelta(days=FENSTER_TAGE)
            with session_scope() as session:
                zeilen = (
                    session.query(ActionLog.tool, ActionLog.ok)
                    .filter(ActionLog.created_at >= grenze)
                    .all()
                )
            roh: dict[str, list[int]] = {}
            for werkzeug, ok in zeilen:
                roh.setdefault(str(werkzeug), []).append(1 if ok else 0)
            for werkzeug, werte in roh.items():
                quoten[werkzeug] = (sum(werte) / len(werte), len(werte))
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
        self._quoten = quoten
        self._quoten_zeit = jetzt
        return quoten

    def _dauerwerte(self) -> dict[str, tuple[float, int]]:
        jetzt = time.time()
        if self._dauern and jetzt - self._dauern_zeit < CACHE_SEKUNDEN:
            return self._dauern
        werte: dict[str, tuple[float, int]] = {}
        try:
            grenze = _jetzt() - timedelta(days=FENSTER_TAGE)
            with session_scope() as session:
                zeilen = (
                    session.query(Erwartung.werkzeug, Erwartung.dauer)
                    .filter(
                        Erwartung.zeit >= grenze,
                        Erwartung.offen == 0,
                        Erwartung.dauer > 0,
                    )
                    .all()
                )
            roh: dict[str, list[float]] = {}
            for werkzeug, dauer in zeilen:
                roh.setdefault(str(werkzeug), []).append(float(dauer or 0.0))
            for werkzeug, liste in roh.items():
                werte[werkzeug] = (sum(liste) / len(liste), len(liste))
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
        self._dauern = werte
        self._dauern_zeit = jetzt
        return werte

    def _grundwert(self, werkzeug: str) -> float:
        return GRUNDVERTRAUEN_UNSICHER if _unsicher(werkzeug) else GRUNDVERTRAUEN

    def schaetzen(self, werkzeug: str, args: dict | None = None) -> dict:
        quoten = self._erfolgsquoten()
        quote, anzahl = quoten.get(werkzeug, (0.0, 0))
        grund = self._grundwert(werkzeug)
        if anzahl >= MIN_BEOBACHTUNGEN:
            gewicht = min(1.0, anzahl / 12.0)
            zutrauen = grund * (1 - gewicht) + quote * gewicht
            basis = f"{int(quote * 100)}% Erfolg in {anzahl} Laeufen"
        else:
            zutrauen = grund
            basis = "kaum Erfahrung, Schaetzung aus dem Bauch"
        bereich = ""
        try:
            from app.services.erfahrung_service import (
                KLAPPT_NICHT,
                bereich_fuer,
                get_erfahrung_service,
            )

            bereich = bereich_fuer(werkzeug, args or {})
            schlechte = [
                e
                for e in get_erfahrung_service().fuer(bereich, 8)
                if e.get("art") == KLAPPT_NICHT
            ]
            if schlechte:
                zutrauen -= min(0.25, 0.06 * len(schlechte))
                basis += f", {len(schlechte)} Stolpersteine im Bereich {bereich}"
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
        dauer, dauer_anzahl = self._dauerwerte().get(werkzeug, (0.0, 0))
        zutrauen = round(max(0.05, min(0.98, zutrauen)), 2)
        return {
            "werkzeug": werkzeug,
            "bereich": bereich,
            "zutrauen": zutrauen,
            "dauer_erwartet": round(dauer, 2)
            if dauer_anzahl >= MIN_BEOBACHTUNGEN
            else 0.0,
            "erwartet": f"{werkzeug} gelingt mit {int(zutrauen * 100)}% ({basis})",
        }

    def vorhersagen(
        self, werkzeug: str, args: dict | None = None, quelle: str = "app"
    ) -> str:
        if not werkzeug:
            return ""
        try:
            schaetzung = self.schaetzen(werkzeug, args)
            with session_scope() as session:
                eintrag = Erwartung(
                    werkzeug=werkzeug[:64],
                    bereich=str(schaetzung.get("bereich", ""))[:80],
                    erwartet=str(schaetzung.get("erwartet", ""))[:400],
                    zutrauen=float(schaetzung.get("zutrauen", 0.5)),
                    dauer_erwartet=float(schaetzung.get("dauer_erwartet", 0.0)),
                    quelle=(quelle or "app")[:24],
                )
                session.add(eintrag)
                session.flush()
                return eintrag.id
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
            return ""

    @staticmethod
    def _ueberraschung(
        zutrauen: float, ok: bool, dauer: float, erwartet: float
    ) -> float:
        wert = abs((1.0 if ok else 0.0) - zutrauen)
        if erwartet > 0.5 and dauer > 0:
            abweichung = abs(dauer - erwartet) / max(erwartet, 0.5)
            wert = max(wert, min(1.0, abweichung) * 0.45)
        return round(min(1.0, wert), 2)

    def abgleichen(
        self, kennung: str, ok: bool, ergebnis: str = "", dauer: float = 0.0
    ) -> dict:
        if not kennung:
            return {}
        try:
            with session_scope() as session:
                eintrag = session.get(Erwartung, kennung)
                if eintrag is None or not eintrag.offen:
                    return {}
                zutrauen = float(eintrag.zutrauen or 0.5)
                erwartet_dauer = float(eintrag.dauer_erwartet or 0.0)
                ueberraschung = self._ueberraschung(zutrauen, ok, dauer, erwartet_dauer)
                eintrag.offen = 0
                eintrag.gelungen = 1 if ok else 0
                eintrag.dauer = round(float(dauer or 0.0), 2)
                eintrag.ueberraschung = ueberraschung
                eintrag.notiz = " ".join(str(ergebnis or "").split())[:300]
                daten = self._zeile(eintrag)
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
            return {}
        if daten.get("ueberraschung", 0.0) >= SCHWELLE:
            self._lernen(daten, ok)
        return daten

    def _lernen(self, daten: dict, ok: bool) -> None:
        werkzeug = daten.get("werkzeug", "")
        bereich = daten.get("bereich", "") or werkzeug
        wert = float(daten.get("ueberraschung", 0.0))
        richtung = "klappte unerwartet" if ok else "scheiterte unerwartet"
        notiz = str(daten.get("notiz", ""))[:160]
        zutrauen = int(float(daten.get("zutrauen", 0)) * 100)
        text = f"{werkzeug} {richtung} (erwartet waren {zutrauen}%): {notiz}"
        try:
            from app.services.erfahrung_service import (
                KLAPPT,
                KLAPPT_NICHT,
                get_erfahrung_service,
            )

            get_erfahrung_service().notieren(
                bereich, text, KLAPPT if ok else KLAPPT_NICHT, min(0.95, 0.5 + wert)
            )
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
        try:
            from app.services.ereignis_service import get_ereignis_service

            get_ereignis_service().notieren(
                "ueberraschung",
                f"{werkzeug} {richtung}",
                text,
                quelle="denken",
                bedeutung=min(0.9, 0.4 + wert),
                gelungen=ok,
            )
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
        if wert >= STARK and not ok:
            try:
                from app.services.neugier_service import get_neugier_service

                get_neugier_service().fragen(
                    f"Warum scheitert {werkzeug} zurzeit, obwohl es frueher lief? "
                    f"Letzter Fehler: {notiz}",
                    thema=bereich,
                    quelle="ueberraschung",
                    dringlichkeit=min(0.95, 0.5 + wert),
                )
            except Exception as fehler:
                leise(fehler, "services/erwartung_service")

    def kalibrierung(self, tage: int = 14) -> dict:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        try:
            with session_scope() as session:
                zeilen = (
                    session.query(
                        Erwartung.werkzeug,
                        Erwartung.zutrauen,
                        Erwartung.gelungen,
                        Erwartung.ueberraschung,
                    )
                    .filter(Erwartung.zeit >= grenze, Erwartung.offen == 0)
                    .all()
                )
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
            zeilen = []
        if not zeilen:
            return {
                "anzahl": 0,
                "brier": None,
                "treffer": None,
                "ueberraschung": 0.0,
                "schwaechste": [],
                "text": "Noch keine Vorhersagen zum Vergleichen.",
            }
        summe = 0.0
        treffer = 0
        ueberraschungen = 0.0
        je_werkzeug: dict[str, list[float]] = {}
        for werkzeug, zutrauen, gelungen, ueberraschung in zeilen:
            p = float(zutrauen or 0.5)
            tat = 1.0 if gelungen else 0.0
            summe += (p - tat) ** 2
            if (p >= 0.5) == (tat >= 0.5):
                treffer += 1
            ueberraschungen += float(ueberraschung or 0.0)
            je_werkzeug.setdefault(str(werkzeug), []).append(
                float(ueberraschung or 0.0)
            )
        anzahl = len(zeilen)
        brier = round(summe / anzahl, 3)
        schwaechste = sorted(
            (
                {
                    "werkzeug": name,
                    "ueberraschung": round(sum(werte) / len(werte), 2),
                    "anzahl": len(werte),
                }
                for name, werte in je_werkzeug.items()
                if len(werte) >= 2
            ),
            key=lambda e: e["ueberraschung"],
            reverse=True,
        )[:5]
        guete = (
            "Jon schaetzt sich gut ein"
            if brier <= 0.12
            else "Jon schaetzt sich brauchbar ein"
            if brier <= 0.25
            else "Jon ueberschaetzt oder unterschaetzt sich haeufig"
        )
        return {
            "anzahl": anzahl,
            "brier": brier,
            "treffer": round(treffer / anzahl, 2),
            "ueberraschung": round(ueberraschungen / anzahl, 2),
            "schwaechste": schwaechste,
            "text": f"{guete} (Brier {brier} aus {anzahl} Vorhersagen).",
        }

    def ueberraschungen(self, limit: int = 15, tage: int = 14) -> list[dict]:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        try:
            with session_scope() as session:
                zeilen = (
                    session.query(Erwartung)
                    .filter(
                        Erwartung.zeit >= grenze,
                        Erwartung.offen == 0,
                        Erwartung.ueberraschung >= SCHWELLE,
                    )
                    .order_by(Erwartung.ueberraschung.desc(), Erwartung.zeit.desc())
                    .limit(limit)
                    .all()
                )
                return [self._zeile(z) for z in zeilen]
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
            return []

    def stand(self) -> dict:
        return {
            "kalibrierung": self.kalibrierung(),
            "ueberraschungen": self.ueberraschungen(8),
        }

    def prompt_block(self, limit: int = 3) -> str:
        eintraege = self.ueberraschungen(limit, tage=7)
        if not eintraege:
            return ""
        zeilen = [
            f"- {e['werkzeug']}: {(e['notiz'] or e['erwartet'])[:120]}"
            for e in eintraege
        ]
        return "Das hat dich zuletzt ueberrascht - rechne diesmal damit:\n" + "\n".join(
            zeilen
        )

    def aufraeumen(self, tage: int = AUFBEWAHRUNG_TAGE) -> int:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        try:
            with session_scope() as session:
                anzahl = (
                    session.query(Erwartung)
                    .filter(Erwartung.zeit < grenze)
                    .delete(synchronize_session=False)
                )
                return int(anzahl or 0)
        except Exception as fehler:
            leise(fehler, "services/erwartung_service")
            return 0


_service: ErwartungService | None = None


def get_erwartung_service() -> ErwartungService:
    global _service
    if _service is None:
        _service = ErwartungService()
    return _service
