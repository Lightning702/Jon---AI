from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from app.db.database import session_scope
from app.db.models import Memory
from app.services.semantik import aehnlichkeit, normieren, vektor

AEHNLICH_SCHWELLE = 0.9
KONFLIKT_SCHWELLE = 0.62
RELEVANZ_SCHWELLE = 0.14
PROMPT_GRENZE = 14
VERFALL_TAGE = 150
VERFALL_WICHTIGKEIT = 0.45


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


class MemoryService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vektoren: dict[str, list[float]] = {}
        self._stand = 0

    @staticmethod
    def _kern(text: str) -> str:
        woerter = [w for w in normieren(text).split() if len(w) > 2]
        return " ".join(woerter[:3])

    def _zeile(self, r: Memory) -> dict:
        return {
            "id": r.id,
            "content": r.content,
            "source": r.source,
            "created_at": r.created_at.isoformat(),
            "wichtigkeit": float(getattr(r, "wichtigkeit", 0.5) or 0.5),
            "nutzungen": int(getattr(r, "nutzungen", 0) or 0),
        }

    def _index(self) -> dict[str, tuple[str, list[float]]]:
        eintraege = self.list(1000)
        with self._lock:
            aktuell: dict[str, tuple[str, list[float]]] = {}
            for eintrag in eintraege:
                kennung = eintrag["id"]
                werte = self._vektoren.get(kennung)
                if werte is None:
                    werte = vektor(eintrag["content"])
                    self._vektoren[kennung] = werte
                aktuell[kennung] = (eintrag["content"], werte)
            self._vektoren = {k: v[1] for k, v in aktuell.items()}
            return aktuell

    def _vergessen_index(self, kennung: str) -> None:
        with self._lock:
            self._vektoren.pop(kennung, None)

    def add(self, content: str, source: str = "chat", wichtigkeit: float = 0.5) -> dict:
        text = content.strip()
        if not text:
            return {"error": "leerer Inhalt"}
        text = text[:1000]
        neu = vektor(text)
        aehnlich: tuple[str, float] = ("", 0.0)
        for kennung, (inhalt, werte) in self._index().items():
            if inhalt == text:
                return {"id": kennung, "content": inhalt, "duplicate": True}
            wert = aehnlichkeit(neu, werte)
            if wert > aehnlich[1]:
                aehnlich = (kennung, wert)
        gleiches_thema = False
        if aehnlich[0]:
            for kennung, (inhalt, _werte) in self._index().items():
                if kennung == aehnlich[0]:
                    gleiches_thema = self._kern(inhalt) == self._kern(text)
                    break
        if aehnlich[0] and aehnlich[1] >= AEHNLICH_SCHWELLE and gleiches_thema:
            with session_scope() as session:
                alt = session.get(Memory, aehnlich[0])
                if alt is not None:
                    vorher = alt.content
                    alt.content = text
                    alt.source = source
                    alt.wichtigkeit = max(
                        float(getattr(alt, "wichtigkeit", 0.5) or 0.5), wichtigkeit
                    )
                    alt.created_at = _jetzt()
                    self._vergessen_index(aehnlich[0])
                    return {
                        "id": alt.id,
                        "content": text,
                        "duplicate": False,
                        "ersetzt": vorher,
                    }
        with session_scope() as session:
            mem = Memory(content=text, source=source, wichtigkeit=wichtigkeit)
            session.add(mem)
            session.flush()
            return {"id": mem.id, "content": mem.content, "duplicate": False}

    def list(self, limit: int = 200) -> list[dict]:
        with session_scope() as session:
            rows = (
                session.query(Memory)
                .order_by(Memory.created_at.asc())
                .limit(limit)
                .all()
            )
            return [self._zeile(r) for r in rows]

    def relevante(self, text: str, limit: int = PROMPT_GRENZE) -> list[dict]:
        frage = str(text or "").strip()
        alle = {e["id"]: e for e in self.list(1000)}
        if not frage:
            geordnet = sorted(
                alle.values(),
                key=lambda e: (e["wichtigkeit"], e["created_at"]),
                reverse=True,
            )
            return geordnet[:limit]
        gefragt = vektor(frage)
        bewertet: list[tuple[float, dict]] = []
        for kennung, (_inhalt, werte) in self._index().items():
            eintrag = alle.get(kennung)
            if eintrag is None:
                continue
            wert = aehnlichkeit(gefragt, werte)
            schub = 0.12 * eintrag["wichtigkeit"] + min(0.08, 0.01 * eintrag["nutzungen"])
            bewertet.append((wert + schub, eintrag))
        bewertet.sort(key=lambda paar: paar[0], reverse=True)
        treffer = [e for wert, e in bewertet if wert >= RELEVANZ_SCHWELLE][:limit]
        if len(treffer) < 4:
            wichtig = sorted(
                alle.values(), key=lambda e: e["wichtigkeit"], reverse=True
            )
            for eintrag in wichtig:
                if eintrag not in treffer:
                    treffer.append(eintrag)
                if len(treffer) >= min(limit, 6):
                    break
        self._benutzt([e["id"] for e in treffer])
        return treffer

    def konflikte(self, schwelle: float = KONFLIKT_SCHWELLE) -> list[dict]:
        eintraege = list(self._index().items())
        inhalte = {e["id"]: e for e in self.list(1000)}
        gefunden: list[dict] = []
        for stelle, (kennung, (inhalt, werte)) in enumerate(eintraege):
            for anderes, (inhalt2, werte2) in eintraege[stelle + 1 :]:
                wert = aehnlichkeit(werte, werte2)
                if wert < schwelle or inhalt == inhalt2:
                    continue
                if self._kern(inhalt) != self._kern(inhalt2):
                    continue
                gefunden.append(
                    {
                        "a": {"id": kennung, "content": inhalt},
                        "b": {"id": anderes, "content": inhalt2},
                        "aehnlichkeit": round(wert, 3),
                        "juenger": kennung
                        if inhalte.get(kennung, {}).get("created_at", "")
                        > inhalte.get(anderes, {}).get("created_at", "")
                        else anderes,
                    }
                )
        return gefunden[:40]

    def _benutzt(self, kennungen: list[str]) -> None:
        if not kennungen:
            return
        try:
            with session_scope() as session:
                for kennung in kennungen:
                    mem = session.get(Memory, kennung)
                    if mem is None:
                        continue
                    mem.nutzungen = int(getattr(mem, "nutzungen", 0) or 0) + 1
                    mem.zuletzt_genutzt = _jetzt()
        except Exception:
            return

    def search(self, query: str, limit: int = 50) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return self.list(limit)
        wortweise = [m for m in self.list(1000) if q in m["content"].lower()]
        if wortweise:
            return wortweise[:limit]
        return self.relevante(query, limit=limit)

    def delete(self, memory_id: str) -> bool:
        with session_scope() as session:
            mem = session.get(Memory, memory_id)
            if mem is None:
                return False
            session.delete(mem)
        self._vergessen_index(memory_id)
        return True

    def forget(self, query: str) -> int:
        q = query.strip().lower()
        if not q:
            return 0
        removed = 0
        betroffen: list[str] = []
        with session_scope() as session:
            for mem in session.query(Memory).all():
                if q in mem.content.lower():
                    betroffen.append(mem.id)
                    session.delete(mem)
                    removed += 1
        for kennung in betroffen:
            self._vergessen_index(kennung)
        return removed

    def clear(self) -> int:
        with session_scope() as session:
            count = session.query(Memory).count()
            session.query(Memory).delete()
        with self._lock:
            self._vektoren.clear()
        return count

    def aufraeumen(self, tage: int = VERFALL_TAGE) -> int:
        grenze = _jetzt() - timedelta(days=max(7, tage))
        entfernt = 0
        betroffen: list[str] = []
        with session_scope() as session:
            for mem in session.query(Memory).all():
                erstellt = mem.created_at
                if erstellt.tzinfo is None:
                    erstellt = erstellt.replace(tzinfo=timezone.utc)
                if erstellt > grenze:
                    continue
                if int(getattr(mem, "nutzungen", 0) or 0) > 0:
                    continue
                if float(getattr(mem, "wichtigkeit", 0.5) or 0.5) >= VERFALL_WICHTIGKEIT:
                    continue
                betroffen.append(mem.id)
                session.delete(mem)
                entfernt += 1
        for kennung in betroffen:
            self._vergessen_index(kennung)
        return entfernt

    def prompt_block(self, limit: int = PROMPT_GRENZE, text: str = "") -> str:
        items = self.relevante(text, limit=limit)
        if not items:
            return ""
        lines = "\n".join(f"- {m['content']}" for m in items)
        return (
            "Das weisst du dauerhaft ueber den Nutzer und aus frueheren Gespraechen "
            "(nutze es aktiv, ohne es staendig zu erwaehnen):\n" + lines
        )
