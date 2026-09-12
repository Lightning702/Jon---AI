from __future__ import annotations

from dataclasses import dataclass

from app.core.fehler import leise

BUDGET = 2600
MIN_NUTZEN = 0.18


@dataclass
class Kandidat:
    name: str
    text: str
    grund: float
    bezug: str = ""

    @property
    def kosten(self) -> int:
        return max(1, len(self.text))


def _relevanz(text: str, bezug: str) -> float:
    if not bezug.strip() or not text.strip():
        return 0.5
    try:
        from app.services.semantik import aehnlichkeit, vektor

        return max(0.0, min(1.0, aehnlichkeit(vektor(text), vektor(bezug))))
    except Exception as fehler:
        leise(fehler, "services/aufmerksamkeit_service")
        return 0.5


class AufmerksamkeitService:
    def _kandidaten(self, text: str) -> list[Kandidat]:
        kandidaten: list[Kandidat] = []

        def dazu(name: str, grund: float, lader, *args) -> None:
            try:
                block = lader(*args)
            except Exception as fehler:
                leise(fehler, "services/aufmerksamkeit_service")
                return
            if block and str(block).strip():
                kandidaten.append(Kandidat(name, str(block).strip(), grund, text))

        from app.services.erwartung_service import get_erwartung_service
        from app.services.fertigkeit_service import get_fertigkeit_service
        from app.services.handlungsraum_service import get_handlungsraum_service
        from app.services.neugier_service import get_neugier_service
        from app.services.notizblock_service import get_notizblock_service
        from app.services.weltmodell_service import get_weltmodell_service
        from app.services.ziel_service import get_ziel_service

        dazu("notizblock", 0.95, get_notizblock_service().prompt_block)
        dazu("ziele", 0.85, get_ziel_service().prompt_block)
        dazu("fertigkeiten", 0.8, get_fertigkeit_service().prompt_block, text)
        dazu("weltmodell", 0.7, get_weltmodell_service().prompt_block, text)
        dazu("handlungsraum", 0.55, get_handlungsraum_service().prompt_block)
        dazu("ueberraschungen", 0.6, get_erwartung_service().prompt_block)
        dazu("neugier", 0.45, get_neugier_service().prompt_block, text)
        try:
            from app.services.erfahrung_service import get_erfahrung_service
            from app.services.tool_index import passende_werkzeuge

            treffer = sorted(passende_werkzeuge(text, top_k=3))
            dienst = get_erfahrung_service()
            for werkzeug in treffer[:2]:
                block = dienst.prompt_block(f"werkzeug:{werkzeug}", 3)
                if block.strip():
                    kandidaten.append(
                        Kandidat(f"erfahrung:{werkzeug}", block.strip(), 0.65, text)
                    )
        except Exception as fehler:
            leise(fehler, "services/aufmerksamkeit_service")
        return kandidaten

    def waehlen(self, text: str = "", budget: int = BUDGET) -> dict:
        kandidaten = self._kandidaten(text)
        bewertet = []
        for kandidat in kandidaten:
            wert = kandidat.grund * (0.45 + 0.55 * _relevanz(kandidat.text, text))
            bewertet.append((wert, wert / kandidat.kosten, kandidat))
        bewertet.sort(key=lambda e: e[1], reverse=True)
        gewaehlt: list[Kandidat] = []
        verworfen: list[dict] = []
        rest = max(200, budget)
        for wert, nutzen, kandidat in bewertet:
            if kandidat.kosten <= rest and wert >= MIN_NUTZEN:
                gewaehlt.append(kandidat)
                rest -= kandidat.kosten
            else:
                verworfen.append(
                    {
                        "name": kandidat.name,
                        "wert": round(wert, 2),
                        "kosten": kandidat.kosten,
                    }
                )
        return {
            "bloecke": [k.text for k in gewaehlt],
            "gewaehlt": [
                {"name": k.name, "kosten": k.kosten, "grund": k.grund} for k in gewaehlt
            ],
            "verworfen": verworfen,
            "budget": budget,
            "verbraucht": budget - rest,
        }

    def bloecke(self, text: str = "", budget: int = BUDGET) -> list[str]:
        return self.waehlen(text, budget)["bloecke"]


_service: AufmerksamkeitService | None = None


def get_aufmerksamkeit_service() -> AufmerksamkeitService:
    global _service
    if _service is None:
        _service = AufmerksamkeitService()
    return _service
