from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta

from app.core.fehler import leise
from app.db.database import session_scope
from app.db.models import Frage

OFFEN = "offen"
BEANTWORTET = "beantwortet"
VERWORFEN = "verworfen"
GESCHEITERT = "gescheitert"

MAX_VERSUCHE = 2
MAX_OFFEN = 60
AEHNLICH = 0.88
AUFBEWAHRUNG_TAGE = 45

MARKER = (
    "weiss ich nicht",
    "weiß ich nicht",
    "keine ahnung",
    "bin mir nicht sicher",
    "bin nicht sicher",
    "vermutlich",
    "vermute ich",
    "koennte sein",
    "könnte sein",
    "muesste ich nachschauen",
    "müsste ich nachschauen",
    "kann ich nicht sagen",
    "unklar",
    "ich glaube",
)

ANTWORT_SYSTEM = (
    "Du bist Jons Wissensdienst. Du bekommst eine offene Frage und optional "
    "Suchergebnisse. Antworte auf Deutsch in hoechstens vier Saetzen, sachlich und "
    "konkret. Wenn die Quellen die Frage nicht klaeren, schreibe genau: UNKLAR. "
    "Erfinde nichts."
)


def _jetzt() -> datetime:
    return datetime.now()


def _saeubern(text: str) -> str:
    sauber = " ".join(str(text or "").split())
    return sauber[:400]


def _thema_aus(text: str) -> str:
    woerter = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9_.-]{4,}", text)][:4]
    return " ".join(woerter)[:120]


class NeugierService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def _zeile(self, eintrag: Frage) -> dict:
        return {
            "id": eintrag.id,
            "text": eintrag.text,
            "thema": eintrag.thema or "",
            "quelle": eintrag.quelle,
            "dringlichkeit": round(float(eintrag.dringlichkeit or 0.5), 2),
            "zustand": eintrag.zustand,
            "antwort": eintrag.antwort or "",
            "versuche": int(eintrag.versuche or 0),
            "erstellt": eintrag.erstellt.isoformat(timespec="seconds")
            if eintrag.erstellt
            else "",
        }

    def _doppelt(self, text: str) -> Frage | None:
        from app.services.semantik import aehnlichkeit, vektor

        try:
            neu = vektor(text)
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
            neu = []
        with session_scope() as session:
            offene = (
                session.query(Frage)
                .filter(Frage.zustand.in_((OFFEN, BEANTWORTET)))
                .order_by(Frage.erstellt.desc())
                .limit(80)
                .all()
            )
            for eintrag in offene:
                if eintrag.text.strip().lower() == text.strip().lower():
                    return eintrag
                if not neu:
                    continue
                try:
                    if aehnlichkeit(neu, vektor(eintrag.text)) >= AEHNLICH:
                        return eintrag
                except Exception as fehler:
                    leise(fehler, "services/neugier_service")
        return None

    def fragen(
        self,
        text: str,
        thema: str = "",
        quelle: str = "chat",
        dringlichkeit: float = 0.5,
    ) -> dict:
        sauber = _saeubern(text)
        if len(sauber) < 8:
            return {"error": "leer"}
        vorhanden = self._doppelt(sauber)
        if vorhanden is not None:
            with session_scope() as session:
                eintrag = session.get(Frage, vorhanden.id)
                if eintrag is None:
                    return {"error": "weg"}
                eintrag.dringlichkeit = min(
                    1.0, float(eintrag.dringlichkeit or 0.5) + 0.08
                )
                return self._zeile(eintrag)
        with session_scope() as session:
            eintrag = Frage(
                text=sauber,
                thema=(thema or _thema_aus(sauber))[:120],
                quelle=(quelle or "chat")[:24],
                dringlichkeit=max(0.0, min(1.0, float(dringlichkeit))),
            )
            session.add(eintrag)
            session.flush()
            daten = self._zeile(eintrag)
        self._kappen()
        return daten

    def _kappen(self) -> None:
        try:
            with session_scope() as session:
                offene = (
                    session.query(Frage)
                    .filter(Frage.zustand == OFFEN)
                    .order_by(Frage.dringlichkeit.desc(), Frage.erstellt.desc())
                    .all()
                )
                for eintrag in offene[MAX_OFFEN:]:
                    eintrag.zustand = VERWORFEN
        except Exception as fehler:
            leise(fehler, "services/neugier_service")

    def aus_antwort(self, auftrag: str, antwort: str) -> dict:
        text = (antwort or "").lower()
        treffer = [m for m in MARKER if m in text]
        if not treffer:
            return {}
        kern = _saeubern(auftrag)
        if len(kern) < 8:
            return {}
        frage = kern if kern.rstrip().endswith("?") else f"{kern}?"
        return self.fragen(
            frage,
            thema=_thema_aus(kern),
            quelle="unsicherheit",
            dringlichkeit=min(0.9, 0.45 + 0.1 * len(treffer)),
        )

    def aus_konflikten(self, limit: int = 5) -> list[dict]:
        neu: list[dict] = []
        try:
            from app.services.memory_service import MemoryService

            for konflikt in MemoryService().konflikte()[:limit]:
                a = str(konflikt.get("a", {}).get("content", ""))[:120]
                b = str(konflikt.get("b", {}).get("content", ""))[:120]
                if not a or not b:
                    continue
                ergebnis = self.fragen(
                    f"Was stimmt wirklich: '{a}' oder '{b}'?",
                    thema=_thema_aus(a),
                    quelle="widerspruch",
                    dringlichkeit=0.7,
                )
                if ergebnis.get("id"):
                    neu.append(ergebnis)
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
        return neu

    def aus_weltmodell(self, limit: int = 3) -> list[dict]:
        neu: list[dict] = []
        try:
            from app.services.weltmodell_service import get_weltmodell_service

            for eintrag in get_weltmodell_service().alle(limit=200):
                if len(neu) >= limit:
                    break
                if (eintrag.get("beschreibung") or "").strip():
                    continue
                if float(eintrag.get("wichtigkeit", 0.5)) < 0.5:
                    continue
                name = str(eintrag.get("name", ""))[:80]
                if not name:
                    continue
                ergebnis = self.fragen(
                    f"Was sollte ich ueber {name} wissen, das ich noch nicht notiert habe?",
                    thema=name,
                    quelle="weltmodell",
                    dringlichkeit=0.35,
                )
                if ergebnis.get("id"):
                    neu.append(ergebnis)
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
        return neu

    def offene(self, limit: int = 20) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Frage)
                .filter(Frage.zustand == OFFEN)
                .order_by(Frage.dringlichkeit.desc(), Frage.erstellt.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def alle(self, limit: int = 60) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Frage)
                .order_by(Frage.erstellt.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def beantwortete(self, limit: int = 20) -> list[dict]:
        with session_scope() as session:
            zeilen = (
                session.query(Frage)
                .filter(Frage.zustand == BEANTWORTET)
                .order_by(Frage.beantwortet.desc())
                .limit(limit)
                .all()
            )
            return [self._zeile(z) for z in zeilen]

    def verwerfen(self, kennung: str) -> bool:
        with session_scope() as session:
            eintrag = session.get(Frage, kennung)
            if eintrag is None:
                return False
            eintrag.zustand = VERWORFEN
            return True

    def merken(self, kennung: str, antwort: str, gescheitert: bool = False) -> dict:
        with session_scope() as session:
            eintrag = session.get(Frage, kennung)
            if eintrag is None:
                return {"error": "unbekannt"}
            eintrag.versuche = int(eintrag.versuche or 0) + 1
            if gescheitert:
                eintrag.zustand = (
                    GESCHEITERT if eintrag.versuche >= MAX_VERSUCHE else OFFEN
                )
            else:
                eintrag.zustand = BEANTWORTET
                eintrag.antwort = _saeubern(antwort)[:400]
                eintrag.beantwortet = _jetzt()
            return self._zeile(eintrag)

    async def beantworten(self, kennung: str) -> dict:
        with session_scope() as session:
            eintrag = session.get(Frage, kennung)
            if eintrag is None:
                return {"error": "unbekannt"}
            frage = eintrag.text
            thema = eintrag.thema or ""
        quellen = ""
        try:
            from app.services.websearch_service import search_web

            ergebnis = await search_web(frage, limit=4, read=False)
            treffer = ergebnis.get("treffer") or []
            quellen = "\n".join(
                f"- {t.get('title', '')}: {t.get('snippet', '')}"[:300]
                for t in treffer[:4]
            )
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
        from app.services.llm import complete

        eingabe = frage if not quellen else f"{frage}\n\nSuchergebnisse:\n{quellen}"
        try:
            antwort = await complete(
                ANTWORT_SYSTEM, eingabe, max_tokens=500, temperature=0.3
            )
        except Exception as exc:
            return self.merken(kennung, str(exc), gescheitert=True)
        sauber = _saeubern(antwort)
        if not sauber or sauber.upper().startswith("UNKLAR"):
            return self.merken(kennung, "", gescheitert=True)
        daten = self.merken(kennung, sauber)
        try:
            from app.services.memory_service import MemoryService

            MemoryService().add(
                f"{frage} -> {sauber}", source="neugier", wichtigkeit=0.5
            )
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
        try:
            from app.services.ereignis_service import get_ereignis_service

            get_ereignis_service().notieren(
                "neugier",
                f"Wissensluecke geschlossen: {frage[:120]}",
                sauber[:300],
                quelle="denken",
                bedeutung=0.45,
            )
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
        daten["thema"] = thema
        return daten

    async def lauf(self, anzahl: int = 3) -> dict:
        self.aus_konflikten()
        offen = self.offene(limit=max(1, anzahl))
        beantwortet = 0
        for eintrag in offen:
            ergebnis = await self.beantworten(eintrag["id"])
            if ergebnis.get("zustand") == BEANTWORTET:
                beantwortet += 1
        return {"geprueft": len(offen), "beantwortet": beantwortet}

    def prompt_block(self, text: str = "", limit: int = 3) -> str:
        offen = self.offene(limit=20)
        if not offen:
            return ""
        gewaehlt = offen[:limit]
        if text.strip():
            try:
                from app.services.semantik import aehnlichkeit, vektor

                ziel = vektor(text)
                bewertet = sorted(
                    offen,
                    key=lambda e: aehnlichkeit(ziel, vektor(e["text"])),
                    reverse=True,
                )
                gewaehlt = [
                    e
                    for e in bewertet
                    if aehnlichkeit(ziel, vektor(e["text"])) > 0.5
                ][:limit]
            except Exception as fehler:
                leise(fehler, "services/neugier_service")
        if not gewaehlt:
            return ""
        zeilen = [f"- {e['text']}" for e in gewaehlt]
        return (
            "Offene Fragen, die du noch nicht beantworten kannst - sag ehrlich, wenn "
            "eine davon gerade dran ist:\n" + "\n".join(zeilen)
        )

    def stand(self) -> dict:
        with session_scope() as session:
            gesamt = session.query(Frage).count()
            offen = session.query(Frage).filter(Frage.zustand == OFFEN).count()
            fertig = (
                session.query(Frage).filter(Frage.zustand == BEANTWORTET).count()
            )
        return {
            "gesamt": gesamt,
            "offen": offen,
            "beantwortet": fertig,
            "naechste": self.offene(5),
        }

    def aufraeumen(self, tage: int = AUFBEWAHRUNG_TAGE) -> int:
        grenze = _jetzt() - timedelta(days=max(1, tage))
        try:
            with session_scope() as session:
                return int(
                    session.query(Frage)
                    .filter(
                        Frage.erstellt < grenze,
                        Frage.zustand.in_((VERWORFEN, GESCHEITERT)),
                    )
                    .delete(synchronize_session=False)
                    or 0
                )
        except Exception as fehler:
            leise(fehler, "services/neugier_service")
            return 0


_service: NeugierService | None = None


def get_neugier_service() -> NeugierService:
    global _service
    if _service is None:
        _service = NeugierService()
    return _service
