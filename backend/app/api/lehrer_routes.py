from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.lehrer_service import get_lehrer_service

router = APIRouter(prefix="/api/lehrer")


class KursNeu(BaseModel):
    fach: str = Field(min_length=2, max_length=160)
    ziel: str = Field(default="", max_length=300)
    niveau: str = Field(default="", max_length=120)
    termin: str = Field(default="", max_length=20)
    dateien: list[str] = Field(default_factory=list, max_length=40)


class Antwort(BaseModel):
    aufgabe: str = Field(min_length=6, max_length=20)
    antwort: str = Field(default="", max_length=6000)


class Frage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    lektion: int | None = None


class Erklaeren(BaseModel):
    lektion: int
    art: str = Field(default="einfacher", max_length=200)


def _fehler(fehler: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(fehler))


@router.get("/kurse")
async def kurse() -> dict:
    return {"kurse": get_lehrer_service().liste()}


@router.post("/kurse")
async def kurs_neu(daten: KursNeu) -> dict:
    from app.services.dateiraum_service import get_dateiraum_service

    raum = get_dateiraum_service()
    sicher = []
    for pfad in daten.dateien:
        try:
            from pathlib import Path

            erlaubt, _grund = raum.frei(Path(pfad).expanduser())
        except Exception:
            erlaubt = False
        if erlaubt:
            sicher.append(pfad)
    dienst = get_lehrer_service()
    try:
        kurs = dienst.erstellen(daten.fach, daten.ziel, daten.niveau, daten.termin, sicher)
    except ValueError as fehler:
        raise _fehler(fehler)
    dienst.starten(kurs)
    return dienst.kurz(kurs)


@router.get("/kurse/{kennung}")
async def kurs(kennung: str) -> dict:
    try:
        return get_lehrer_service().ansicht(kennung)
    except ValueError as fehler:
        raise HTTPException(status_code=404, detail=str(fehler))


@router.delete("/kurse/{kennung}")
async def kurs_weg(kennung: str) -> dict:
    try:
        return get_lehrer_service().entfernen(kennung)
    except ValueError as fehler:
        raise _fehler(fehler)


@router.post("/kurse/{kennung}/neu-bauen")
async def neu_bauen(kennung: str) -> dict:
    dienst = get_lehrer_service()
    try:
        kurs = dienst.laden(kennung)
    except ValueError as fehler:
        raise _fehler(fehler)
    kurs.update(status="baut", fortschritt=0, schritt="Lerndateien werden gelesen", fehler="")
    dienst.speichern(kurs)
    dienst.starten(kurs)
    return dienst.kurz(kurs)


@router.get("/kurse/{kennung}/aufgabe")
async def aufgabe(kennung: str, lektion: int | None = None) -> dict:
    try:
        return await get_lehrer_service().naechste(kennung, lektion)
    except ValueError as fehler:
        raise _fehler(fehler)


@router.post("/kurse/{kennung}/antwort")
async def antwort(kennung: str, daten: Antwort) -> dict:
    try:
        return await get_lehrer_service().antworten(kennung, daten.aufgabe, daten.antwort)
    except ValueError as fehler:
        raise _fehler(fehler)


@router.post("/kurse/{kennung}/frage")
async def frage(kennung: str, daten: Frage) -> dict:
    try:
        return await get_lehrer_service().fragen(kennung, daten.text, daten.lektion)
    except ValueError as fehler:
        raise _fehler(fehler)


@router.post("/kurse/{kennung}/erklaeren")
async def erklaeren(kennung: str, daten: Erklaeren) -> dict:
    try:
        return await get_lehrer_service().erklaeren(kennung, daten.lektion, daten.art)
    except ValueError as fehler:
        raise _fehler(fehler)


@router.get("/kurse/{kennung}/probetest")
async def probetest(kennung: str, anzahl: int = 10) -> dict:
    try:
        return get_lehrer_service().probetest(kennung, max(3, min(anzahl, 30)))
    except ValueError as fehler:
        raise _fehler(fehler)


@router.post("/kurse/{kennung}/mehr")
async def mehr(kennung: str, request: Request) -> dict:
    try:
        daten = await request.json()
    except ValueError:
        daten = {}
    lektion = int((daten or {}).get("lektion") or 1)
    neu = await get_lehrer_service().mehr_aufgaben(kennung, lektion, 5, str((daten or {}).get("schwerpunkt") or ""))
    return {"neu": len(neu)}
