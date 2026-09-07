from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta

from app.core.config import DATA_DIR
from app.core.fehler import leise

TRAINING_ORDNER = DATA_DIR / "training"
MIN_SCHRITTE = 3
MIN_WIEDERHOLUNGEN = 2

SKILL_SYSTEM = (
    "Du schreibst eine kurze Arbeitsanleitung (Skill) fuer den Assistenten Jon, "
    "damit er eine wiederkehrende Aufgabe beim naechsten Mal schneller und sicherer "
    "loest. Du bekommst die tatsaechlich ausgefuehrten Schritte eines erfolgreichen "
    "Laufs.\n"
    "Schreibe Markdown auf Deutsch: eine Ueberschrift, ein Satz wann der Skill gilt, "
    "dann nummerierte Schritte mit den echten Werkzeugnamen, dann 'Fallen' mit dem, "
    "was schiefgehen kann. Hoechstens 30 Zeilen. Keine erfundenen Werkzeuge."
)


def _jetzt() -> datetime:
    return datetime.now()


def _dateiname(text: str) -> str:
    sauber = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (sauber or "gelernt")[:48]


class LernenService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def muster(self, tage: int = 21, mindest: int = MIN_WIEDERHOLUNGEN) -> list[dict]:
        from app.services.ereignis_service import get_ereignis_service

        dienst = get_ereignis_service()
        bis = _jetzt()
        von = bis - timedelta(days=max(1, tage))
        eintraege = [
            e
            for e in dienst.spanne(von, bis, limit=4000)
            if e["art"] in ("werkzeug", "browser")
        ]
        folgen: dict[tuple, int] = {}
        fenster: list[str] = []
        letzte_zeit = ""
        for eintrag in eintraege:
            if letzte_zeit and eintrag["zeit"][:13] != letzte_zeit[:13]:
                fenster = []
            letzte_zeit = eintrag["zeit"]
            fenster.append(eintrag["titel"])
            fenster = fenster[-4:]
            if len(fenster) >= MIN_SCHRITTE:
                folgen[tuple(fenster[-MIN_SCHRITTE:])] = (
                    folgen.get(tuple(fenster[-MIN_SCHRITTE:]), 0) + 1
                )
        ergebnis = [
            {"schritte": list(folge), "wie_oft": anzahl}
            for folge, anzahl in folgen.items()
            if anzahl >= mindest
        ]
        ergebnis.sort(key=lambda e: e["wie_oft"], reverse=True)
        return ergebnis[:10]

    async def skill_aus_lauf(self, auftrag_id: str = "", titel: str = "") -> dict:
        from app.services.auftrag_service import get_auftrag_service
        from app.services.ereignis_service import get_ereignis_service
        from app.services.llm import complete
        from app.services.skill_service import SkillService

        auftraege = get_auftrag_service()
        auftrag = auftraege.holen(auftrag_id) if auftrag_id else None
        if auftrag is None:
            fertige = [a for a in auftraege.liste(("fertig",), 10)]
            if not fertige:
                return {"ok": False, "fehler": "Kein abgeschlossener Auftrag da."}
            auftrag = fertige[0]
        ereignisse = get_ereignis_service()
        bis = _jetzt()
        von = bis - timedelta(days=3)
        schritte = [
            f"{e['titel']}: {e['detail'][:120]}"
            for e in ereignisse.spanne(von, bis, limit=400)
            if e["art"] in ("werkzeug", "browser") and e["gelungen"]
        ][-25:]
        if len(schritte) < MIN_SCHRITTE:
            return {"ok": False, "fehler": "Zu wenige Schritte zum Lernen."}
        name = _dateiname(titel or auftrag.get("titel", "gelernt"))
        frage = (
            f"Aufgabe: {auftrag.get('titel', '')}\n\nAusgefuehrte Schritte:\n"
            + "\n".join(f"{n}. {s}" for n, s in enumerate(schritte, start=1))
        )
        try:
            text = await complete(SKILL_SYSTEM, frage, max_tokens=900, temperature=0.3)
        except Exception as exc:
            return {"ok": False, "fehler": str(exc)}
        if not text.strip():
            return {"ok": False, "fehler": "Leere Antwort."}
        ergebnis = SkillService().write(name, text.strip())
        ereignisse.notieren(
            "erkenntnis",
            f"Neuer Skill gelernt: {name}",
            text.strip()[:400],
            quelle="lernen",
            bedeutung=0.8,
        )
        return {"ok": True, "skill": name, "datei": ergebnis, "inhalt": text[:1500]}

    def antimuster(self, tage: int = 21, mindest: int = 2) -> list[dict]:
        from app.services.ereignis_service import get_ereignis_service

        dienst = get_ereignis_service()
        bis = _jetzt()
        von = bis - timedelta(days=max(1, tage))
        fehler: dict[str, dict] = {}
        for eintrag in dienst.spanne(von, bis, arten=("fehler",), limit=2000):
            stand = fehler.setdefault(
                eintrag["titel"], {"wie_oft": 0, "beispiel": eintrag["detail"][:200]}
            )
            stand["wie_oft"] += 1
        ergebnis = [
            {"werkzeug": name, **stand}
            for name, stand in fehler.items()
            if stand["wie_oft"] >= mindest
        ]
        ergebnis.sort(key=lambda e: e["wie_oft"], reverse=True)
        return ergebnis[:10]

    def trainingsdaten(self, grenze: int = 500) -> dict:
        from app.db.database import session_scope
        from app.db.models import Conversation, Message

        TRAINING_ORDNER.mkdir(parents=True, exist_ok=True)
        ziel = TRAINING_ORDNER / f"jon-{_jetzt().strftime('%Y%m%d')}.jsonl"
        anzahl = 0
        try:
            with session_scope() as session:
                gespraeche = (
                    session.query(Conversation)
                    .order_by(Conversation.updated_at.desc())
                    .limit(200)
                    .all()
                )
                zeilen: list[str] = []
                for gespraech in gespraeche:
                    nachrichten = sorted(
                        gespraech.messages, key=lambda m: m.position
                    )
                    paare = []
                    letzte_frage = ""
                    for nachricht in nachrichten:
                        if nachricht.role == "user":
                            letzte_frage = nachricht.content
                        elif nachricht.role == "assistant" and letzte_frage:
                            paare.append(
                                {
                                    "messages": [
                                        {"role": "user", "content": letzte_frage[:4000]},
                                        {
                                            "role": "assistant",
                                            "content": nachricht.content[:4000],
                                        },
                                    ]
                                }
                            )
                            letzte_frage = ""
                    for paar in paare:
                        if anzahl >= grenze:
                            break
                        zeilen.append(json.dumps(paar, ensure_ascii=False))
                        anzahl += 1
            ziel.write_text("\n".join(zeilen), encoding="utf-8")
        except Exception as exc:
            leise(exc, "services/lernen_service")
            return {"ok": False, "fehler": str(exc)}
        return {
            "ok": True,
            "datei": str(ziel),
            "beispiele": anzahl,
            "hinweis": (
                "Diese Datei ist im JSONL-Format und laesst sich fuer ein LoRA-"
                "Feintuning eines lokalen Modells verwenden."
            ),
        }

    async def lernen(self) -> dict:
        from app.services.erfahrung_service import KLAPPT_NICHT, get_erfahrung_service

        erfahrung = get_erfahrung_service()
        gelernt = []
        for eintrag in self.antimuster():
            erfahrung.notieren(
                f"werkzeug:{eintrag['werkzeug']}",
                f"Scheitert oefter ({eintrag['wie_oft']}x): {eintrag['beispiel']}",
                KLAPPT_NICHT,
                0.75,
            )
            gelernt.append(eintrag["werkzeug"])
        return {
            "ok": True,
            "muster": self.muster(),
            "antimuster_gelernt": gelernt,
        }


_service: LernenService | None = None


def get_lernen_service() -> LernenService:
    global _service
    if _service is None:
        _service = LernenService()
    return _service
