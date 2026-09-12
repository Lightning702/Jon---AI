from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import Aufgabe

WARTET = "wartet"
LAEUFT = "laeuft"
PAUSIERT = "pausiert"
BRAUCHT_FREIGABE = "braucht_freigabe"
FERTIG = "fertig"
GESCHEITERT = "gescheitert"
ABGEBROCHEN = "abgebrochen"

OFFEN = (WARTET, LAEUFT, BRAUCHT_FREIGABE, PAUSIERT)

MAX_PROTOKOLL = 120
MAX_LAEUFE = 3
STANDARD_BUDGET = 20
AUFBEWAHRUNG_TAGE = 30


def _jetzt() -> datetime:
    return datetime.now()


def _kurz(text: str, grenze: int = 300) -> str:
    sauber = " ".join(str(text or "").split())
    return sauber if len(sauber) <= grenze else sauber[: grenze - 1] + "…"


class AufgabenService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._laeuft: str = ""

    def _zeile(self, eintrag: Aufgabe) -> dict:
        try:
            protokoll = json.loads(eintrag.protokoll or "[]")
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            protokoll = []
        try:
            freigabe = json.loads(eintrag.offene_freigabe or "{}")
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            freigabe = {}
        try:
            abnahme = json.loads(eintrag.abnahme or "{}")
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            abnahme = {}
        return {
            "id": eintrag.id,
            "auftrag": eintrag.auftrag,
            "titel": eintrag.titel or _kurz(eintrag.auftrag, 80),
            "zustand": eintrag.zustand,
            "prioritaet": int(eintrag.prioritaet or 5),
            "plan": eintrag.plan or "",
            "fortschritt": round(float(eintrag.fortschritt or 0.0), 2),
            "budget_minuten": int(eintrag.budget_minuten or STANDARD_BUDGET),
            "verbraucht_minuten": round(float(eintrag.verbraucht or 0.0) / 60, 1),
            "laeufe": int(eintrag.laeufe or 0),
            "protokoll": protokoll,
            "ergebnis": eintrag.ergebnis or "",
            "fehler": eintrag.fehler or "",
            "offene_freigabe": freigabe,
            "abnahme": abnahme,
            "unbeaufsichtigt": bool(eintrag.unbeaufsichtigt),
            "quelle": eintrag.quelle,
            "erstellt": eintrag.erstellt.isoformat(timespec="seconds")
            if eintrag.erstellt
            else "",
            "beendet": eintrag.beendet.isoformat(timespec="seconds")
            if eintrag.beendet
            else "",
        }

    def anlegen(
        self,
        auftrag: str,
        budget_minuten: int = STANDARD_BUDGET,
        prioritaet: int = 5,
        titel: str = "",
        quelle: str = "app",
        gespraech: str = "",
        unbeaufsichtigt: bool = True,
    ) -> dict:
        sauber = " ".join(str(auftrag or "").split())[:2000]
        if len(sauber) < 4:
            return {"error": "Die Aufgabe ist zu kurz."}
        with session_scope() as session:
            eintrag = Aufgabe(
                auftrag=sauber,
                titel=(titel or _kurz(sauber, 80))[:200],
                budget_minuten=max(1, min(240, int(budget_minuten or STANDARD_BUDGET))),
                prioritaet=max(1, min(9, int(prioritaet or 5))),
                quelle=(quelle or "app")[:24],
                gespraech=str(gespraech or "")[:32],
                unbeaufsichtigt=1 if unbeaufsichtigt else 0,
                protokoll=json.dumps(
                    [
                        {
                            "zeit": _jetzt().isoformat(timespec="seconds"),
                            "text": "Aufgabe angenommen.",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            session.add(eintrag)
            session.flush()
            return self._zeile(eintrag)

    def protokollieren(self, kennung: str, text: str, art: str = "info") -> None:
        if not kennung or not str(text or "").strip():
            return
        try:
            with session_scope() as session:
                eintrag = session.get(Aufgabe, kennung)
                if eintrag is None:
                    return
                try:
                    zeilen = json.loads(eintrag.protokoll or "[]")
                except Exception:
                    zeilen = []
                zeilen.append(
                    {
                        "zeit": _jetzt().isoformat(timespec="seconds"),
                        "art": art,
                        "text": _kurz(text, 400),
                    }
                )
                eintrag.protokoll = json.dumps(
                    zeilen[-MAX_PROTOKOLL:], ensure_ascii=False
                )
                eintrag.aktualisiert = _jetzt()
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")

    def _setzen(self, kennung: str, **werte) -> dict | None:
        try:
            with session_scope() as session:
                eintrag = session.get(Aufgabe, kennung)
                if eintrag is None:
                    return None
                for name, wert in werte.items():
                    if hasattr(eintrag, name):
                        setattr(eintrag, name, wert)
                eintrag.aktualisiert = _jetzt()
                return self._zeile(eintrag)
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            return None

    def holen(self, kennung: str) -> dict | None:
        with session_scope() as session:
            eintrag = session.get(Aufgabe, kennung)
            return self._zeile(eintrag) if eintrag is not None else None

    def liste(self, zustaende: tuple[str, ...] = (), limit: int = 40) -> list[dict]:
        with session_scope() as session:
            frage = session.query(Aufgabe)
            if zustaende:
                frage = frage.filter(Aufgabe.zustand.in_(zustaende))
            zeilen = (
                frage.order_by(
                    Aufgabe.prioritaet.asc(), Aufgabe.erstellt.asc()
                )
                .limit(max(1, limit))
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def naechste(self) -> dict | None:
        with session_scope() as session:
            eintrag = (
                session.query(Aufgabe)
                .filter(Aufgabe.zustand == WARTET, Aufgabe.laeufe < MAX_LAEUFE)
                .order_by(Aufgabe.prioritaet.asc(), Aufgabe.erstellt.asc())
                .first()
            )
            return self._zeile(eintrag) if eintrag is not None else None

    def pausieren(self, kennung: str) -> dict | None:
        self.protokollieren(kennung, "Vom Nutzer pausiert.", "nutzer")
        return self._setzen(kennung, zustand=PAUSIERT)

    def fortsetzen(self, kennung: str) -> dict | None:
        self.protokollieren(kennung, "Wieder freigegeben.", "nutzer")
        return self._setzen(kennung, zustand=WARTET)

    def abbrechen(self, kennung: str) -> dict | None:
        aufgabe = self.holen(kennung)
        if aufgabe and aufgabe.get("plan"):
            try:
                from app.services.planer_service import get_planer_service

                get_planer_service().abbrechen(aufgabe["plan"])
            except Exception as fehler:
                leise(fehler, "services/aufgaben_service")
        self.protokollieren(kennung, "Vom Nutzer abgebrochen.", "nutzer")
        return self._setzen(kennung, zustand=ABGEBROCHEN, beendet=_jetzt())

    def freigeben(self, kennung: str, erlaubt: bool = True) -> dict | None:
        aufgabe = self.holen(kennung)
        if aufgabe is None:
            return None
        if not erlaubt:
            self.protokollieren(kennung, "Freigabe verweigert - Aufgabe beendet.", "nutzer")
            return self._setzen(
                kennung,
                zustand=GESCHEITERT,
                fehler="Die noetige Freigabe wurde verweigert.",
                beendet=_jetzt(),
            )
        self.protokollieren(kennung, "Freigabe erteilt - Jon macht weiter.", "nutzer")
        return self._setzen(
            kennung, zustand=WARTET, unbeaufsichtigt=0, offene_freigabe="{}"
        )

    def unterbrochene_aufnehmen(self) -> int:
        try:
            with session_scope() as session:
                zeilen = session.query(Aufgabe).filter(Aufgabe.zustand == LAEUFT).all()
                for eintrag in zeilen:
                    eintrag.zustand = WARTET
                    eintrag.aktualisiert = _jetzt()
                anzahl = len(zeilen)
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            return 0
        return anzahl

    async def lauf(self, kennung: str = "") -> dict:
        with self._lock:
            if self._laeuft:
                return {"ok": False, "grund": "laeuft bereits", "aufgabe": self._laeuft}
        aufgabe = self.holen(kennung) if kennung else self.naechste()
        if aufgabe is None:
            return {"ok": True, "leer": True}
        if aufgabe["zustand"] not in (WARTET,):
            return {"ok": False, "grund": f"Zustand {aufgabe['zustand']}"}
        with self._lock:
            self._laeuft = aufgabe["id"]
        try:
            return await self._bearbeiten(aufgabe)
        finally:
            with self._lock:
                self._laeuft = ""

    async def _bearbeiten(self, aufgabe: dict) -> dict:
        from app.services.approval_service import unbeaufsichtigt, zuruecksetzen
        from app.services.planer_service import get_planer_service

        kennung = aufgabe["id"]
        begonnen = time.monotonic()
        grenze = aufgabe["budget_minuten"] * 60
        self._setzen(
            kennung,
            zustand=LAEUFT,
            gestartet=_jetzt(),
            laeufe=aufgabe["laeufe"] + 1,
            fehler="",
        )
        self.protokollieren(kennung, f"Start, Budget {aufgabe['budget_minuten']} Minuten.")
        planer = get_planer_service()
        marke = unbeaufsichtigt(bool(aufgabe["unbeaufsichtigt"]))
        try:
            plan = aufgabe.get("plan") and planer.holen(aufgabe["plan"])
            if not plan or plan.get("zustand") in ("fertig", "abgebrochen"):
                plan = await planer.entwerfen(
                    aufgabe["auftrag"], kontext=self._kontext(aufgabe), quelle="aufgabe"
                )
                if plan.get("error"):
                    return self._beenden(kennung, False, fehler=plan["error"])
                self._setzen(kennung, plan=plan["id"])
                self.protokollieren(
                    kennung,
                    "Plan steht: "
                    + " · ".join(s["titel"] for s in plan["schritte"][:6]),
                    "plan",
                )
            ergebnis = ""
            async for ereignis in planer.ausfuehren(
                plan["id"], bestaetigt=not aufgabe["unbeaufsichtigt"], quelle="aufgabe"
            ):
                art = ereignis.get("art")
                if art == "freigabe":
                    return self._parken(kennung, ereignis)
                if art == "schritt" and ereignis.get("status") != "laeuft":
                    zeichen = "ok" if ereignis.get("status") == "fertig" else "fehler"
                    self.protokollieren(
                        kennung, f"{ereignis['titel']}: {zeichen}", "schritt"
                    )
                    stand = planer.holen(plan["id"])
                    if stand:
                        self._setzen(kennung, fortschritt=stand["fortschritt"])
                if art == "umplanung":
                    self.protokollieren(kennung, ereignis.get("text", "Neu geplant."), "plan")
                if art == "ende":
                    ergebnis = ereignis.get("text", "")
                    if not ereignis.get("ok"):
                        return self._beenden(
                            kennung, False, fehler=ergebnis, dauer=time.monotonic() - begonnen
                        )
                if time.monotonic() - begonnen > grenze:
                    planer.abbrechen(plan["id"])
                    self.protokollieren(kennung, "Zeitbudget aufgebraucht.", "budget")
                    return self._beenden(
                        kennung,
                        False,
                        fehler="Das Zeitbudget war aufgebraucht, bevor alles fertig war.",
                        dauer=time.monotonic() - begonnen,
                        weiter=True,
                    )
            abnahme = await self._abnehmen(aufgabe, plan["id"], ergebnis)
            return self._beenden(
                kennung,
                bool(abnahme.get("fertig", True)),
                ergebnis=ergebnis,
                fehler="" if abnahme.get("fertig", True) else abnahme.get("fehlt", ""),
                dauer=time.monotonic() - begonnen,
                abnahme=abnahme,
            )
        except Exception as exc:
            leise(exc, "services/aufgaben_service")
            return self._beenden(
                kennung, False, fehler=str(exc)[:400], dauer=time.monotonic() - begonnen
            )
        finally:
            zuruecksetzen(marke)

    def _kontext(self, aufgabe: dict) -> str:
        teile = []
        try:
            from app.services.handlungsraum_service import get_handlungsraum_service

            teile.append(get_handlungsraum_service().prompt_block())
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
        if aufgabe["laeufe"]:
            teile.append(
                f"Dies ist Versuch {aufgabe['laeufe'] + 1}. Frueher gescheitert an: "
                f"{aufgabe.get('fehler', 'unbekannt')}"
            )
        return "\n\n".join(t for t in teile if t)

    def _parken(self, kennung: str, ereignis: dict) -> dict:
        werkzeuge = ", ".join(ereignis.get("werkzeuge", [])) or "riskante Schritte"
        self.protokollieren(
            kennung,
            f"Wartet auf deine Freigabe fuer: {werkzeuge}",
            "freigabe",
        )
        self._setzen(
            kennung,
            zustand=BRAUCHT_FREIGABE,
            offene_freigabe=json.dumps(
                {
                    "schritte": ereignis.get("schritte", []),
                    "werkzeuge": ereignis.get("werkzeuge", []),
                    "text": ereignis.get("text", ""),
                },
                ensure_ascii=False,
            ),
        )
        return {"ok": True, "freigabe": True, "aufgabe": self.holen(kennung)}

    async def _abnehmen(self, aufgabe: dict, plan: str, ergebnis: str) -> dict:
        try:
            from app.services.abnahme_service import get_abnahme_service

            return await get_abnahme_service().pruefen(aufgabe["auftrag"], plan, ergebnis)
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            return {"fertig": True, "grund": "Abnahme uebersprungen."}

    def _beenden(
        self,
        kennung: str,
        gelungen: bool,
        ergebnis: str = "",
        fehler: str = "",
        dauer: float = 0.0,
        weiter: bool = False,
        abnahme: dict | None = None,
    ) -> dict:
        aufgabe = self.holen(kennung) or {}
        nochmal = weiter or (
            not gelungen and aufgabe.get("laeufe", 0) < MAX_LAEUFE
        )
        zustand = FERTIG if gelungen else (WARTET if nochmal else GESCHEITERT)
        self._setzen(
            kennung,
            zustand=zustand,
            ergebnis=_kurz(ergebnis, 3000),
            fehler=_kurz(fehler, 800),
            verbraucht=float(aufgabe.get("verbraucht_minuten", 0)) * 60 + dauer,
            beendet=_jetzt() if zustand in (FERTIG, GESCHEITERT) else None,
            abnahme=json.dumps(abnahme or {}, ensure_ascii=False),
        )
        if gelungen:
            self.protokollieren(kennung, "Fertig.", "ende")
        elif nochmal:
            self.protokollieren(
                kennung, f"Abgebrochen ({fehler[:120]}) - Jon versucht es erneut.", "ende"
            )
        else:
            self.protokollieren(kennung, f"Gescheitert: {fehler[:160]}", "ende")
        try:
            from app.services.ereignis_service import get_ereignis_service

            get_ereignis_service().notieren(
                "aufgabe",
                f"Aufgabe '{aufgabe.get('titel', '')}' {'fertig' if gelungen else 'offen'}",
                (ergebnis or fehler)[:300],
                quelle="aufgabe",
                bedeutung=0.6,
                gelungen=gelungen,
            )
        except Exception as fehler_:
            leise(fehler_, "services/aufgaben_service")
        return {"ok": gelungen, "aufgabe": self.holen(kennung)}

    def stand(self) -> dict:
        offen = self.liste(OFFEN, 30)
        with session_scope() as session:
            fertig = session.query(Aufgabe).filter(Aufgabe.zustand == FERTIG).count()
            gescheitert = (
                session.query(Aufgabe).filter(Aufgabe.zustand == GESCHEITERT).count()
            )
        return {
            "laeuft": self._laeuft,
            "offen": offen,
            "wartet": len([a for a in offen if a["zustand"] == WARTET]),
            "braucht_freigabe": [
                a for a in offen if a["zustand"] == BRAUCHT_FREIGABE
            ],
            "fertig": fertig,
            "gescheitert": gescheitert,
        }

    def prompt_block(self, limit: int = 4) -> str:
        offen = self.liste(OFFEN, limit)
        if not offen:
            return ""
        zeilen = []
        for aufgabe in offen:
            stand = aufgabe["zustand"]
            zusatz = (
                " - wartet auf deine Freigabe"
                if stand == BRAUCHT_FREIGABE
                else f" - {int(aufgabe['fortschritt'] * 100)}% fertig"
                if stand == LAEUFT
                else ""
            )
            zeilen.append(f"- {aufgabe['titel']} ({stand}{zusatz})")
        return (
            "Aufgaben, an denen du selbstaendig arbeitest - sag Bescheid, wenn eine "
            "davon gerade dran ist:\n" + "\n".join(zeilen)
        )

    def aufraeumen(self, tage: int = AUFBEWAHRUNG_TAGE) -> int:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        try:
            with session_scope() as session:
                return int(
                    session.query(Aufgabe)
                    .filter(
                        Aufgabe.erstellt < grenze,
                        Aufgabe.zustand.in_((FERTIG, GESCHEITERT, ABGEBROCHEN)),
                    )
                    .delete(synchronize_session=False)
                    or 0
                )
        except Exception as fehler:
            leise(fehler, "services/aufgaben_service")
            return 0


_service: AufgabenService | None = None


def get_aufgaben_service() -> AufgabenService:
    global _service
    if _service is None:
        _service = AufgabenService()
    return _service
