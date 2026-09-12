from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.services.auftrag_service import get_auftrag_service
from app.services.benchmark_service import get_benchmark_service
from app.services.budget_service import get_budget_service
from app.services.ereignis_service import get_ereignis_service
from app.services.erwartung_service import get_erwartung_service
from app.services.fertigkeit_service import get_fertigkeit_service
from app.services.handlungsraum_service import get_handlungsraum_service
from app.services.initiative_service import get_initiative_service
from app.services.konsolidierung_service import get_konsolidierung_service
from app.services.metakognition_service import get_metakognition_service
from app.services.neugier_service import get_neugier_service
from app.services.planer_service import get_planer_service
from app.services.selbst_service import get_selbst_service
from app.services.weltmodell_service import get_weltmodell_service
from app.services.ziel_service import get_ziel_service

router = APIRouter(prefix="/api/denken")


@router.get("/zustand")
async def zustand() -> dict:
    return get_handlungsraum_service().zustand()


@router.get("/ziele")
async def ziele() -> dict:
    dienst = get_ziel_service()
    return {"offen": dienst.liste(), "faellig": dienst.faellig(3)}


@router.post("/ziele")
async def ziel_anlegen(payload: dict) -> dict:
    ergebnis = get_ziel_service().anlegen(
        str(payload.get("titel", "")),
        str(payload.get("beschreibung", "")),
        str(payload.get("frist", "")),
        str(payload.get("naechster_schritt", "")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.patch("/ziele/{kennung}")
async def ziel_aendern(kennung: str, payload: dict) -> dict:
    ergebnis = get_ziel_service().aktualisieren(
        kennung,
        str(payload.get("zustand", "")),
        str(payload.get("naechster_schritt", "")),
        payload.get("fortschritt"),
        str(payload.get("frist", "")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=404, detail=ergebnis["error"])
    return ergebnis


@router.delete("/ziele/{kennung}")
async def ziel_loeschen(kennung: str) -> dict:
    return {"geloescht": get_ziel_service().loeschen(kennung)}


@router.get("/verlauf")
async def verlauf(zeitraum: str = "heute", thema: str = "") -> dict:
    dienst = get_ereignis_service()
    bild = dienst.tagesbild(zeitraum)
    if thema:
        bild["treffer"] = dienst.suchen(thema, limit=15)
    return bild


@router.get("/initiative")
async def initiative() -> dict:
    dienst = get_initiative_service()
    return {"vorschlaege": dienst.alle(), "offen": dienst.offene()}


@router.post("/initiative/lauf")
async def initiative_lauf() -> dict:
    return await get_initiative_service().lauf(erzwingen=True)


@router.post("/initiative/{kennung}")
async def initiative_entscheiden(kennung: str, payload: dict) -> dict:
    dienst = get_initiative_service()
    if payload.get("ausfuehren"):
        return await dienst.ausfuehren(kennung)
    ergebnis = dienst.entscheiden(kennung, bool(payload.get("angenommen", True)))
    if ergebnis.get("error"):
        raise HTTPException(status_code=404, detail=ergebnis["error"])
    return ergebnis


@router.get("/selbstbild")
async def selbstbild(aufgabe: str = "") -> dict:
    dienst = get_selbst_service()
    return dienst.kann_ich(aufgabe) if aufgabe else dienst.selbstbild()


@router.get("/weltmodell")
async def weltmodell(art: str = "", name: str = "") -> dict:
    dienst = get_weltmodell_service()
    if name:
        return dienst.umfeld(name)
    return {"entitaeten": dienst.alle(art, 200)}


@router.get("/auftraege")
async def auftraege() -> dict:
    dienst = get_auftrag_service()
    return {"offen": dienst.offene(), "alle": dienst.liste(limit=25)}


@router.get("/budget")
async def budget() -> dict:
    return get_budget_service().stand()


@router.post("/konsolidieren")
async def konsolidieren(payload: dict | None = None) -> dict:
    tag = str((payload or {}).get("tag", "gestern"))
    return await get_konsolidierung_service().lauf(tag)


@router.get("/benchmark")
async def benchmark(bereich: str = "") -> dict:
    return await asyncio.to_thread(get_benchmark_service().lauf, bereich)


@router.get("/erwartung")
async def erwartung(tage: int = 14) -> dict:
    dienst = get_erwartung_service()
    return {
        "kalibrierung": dienst.kalibrierung(tage),
        "ueberraschungen": dienst.ueberraschungen(20, tage),
    }


@router.get("/erwartung/{werkzeug}")
async def erwartung_werkzeug(werkzeug: str) -> dict:
    return get_erwartung_service().schaetzen(werkzeug)


@router.get("/fragen")
async def fragen() -> dict:
    dienst = get_neugier_service()
    return {
        "offen": dienst.offene(30),
        "beantwortet": dienst.beantwortete(20),
        "stand": dienst.stand(),
    }


@router.post("/fragen")
async def frage_anlegen(payload: dict) -> dict:
    ergebnis = get_neugier_service().fragen(
        str(payload.get("text", "")),
        str(payload.get("thema", "")),
        "nutzer",
        float(payload.get("dringlichkeit", 0.6) or 0.6),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/fragen/lauf")
async def fragen_lauf(payload: dict | None = None) -> dict:
    anzahl = int((payload or {}).get("anzahl", 3) or 3)
    return await get_neugier_service().lauf(anzahl)


@router.post("/fragen/{kennung}")
async def frage_klaeren(kennung: str) -> dict:
    ergebnis = await get_neugier_service().beantworten(kennung)
    if ergebnis.get("error"):
        raise HTTPException(status_code=404, detail=ergebnis["error"])
    return ergebnis


@router.delete("/fragen/{kennung}")
async def frage_verwerfen(kennung: str) -> dict:
    return {"verworfen": get_neugier_service().verwerfen(kennung)}


@router.get("/fertigkeiten")
async def fertigkeiten() -> dict:
    return get_fertigkeit_service().stand()


@router.get("/fertigkeiten/vorschlaege")
async def fertigkeit_vorschlaege() -> dict:
    dienst = get_fertigkeit_service()
    return {"vorschlaege": await asyncio.to_thread(dienst.entdecken)}


@router.post("/fertigkeiten")
async def fertigkeit_anlegen(payload: dict) -> dict:
    ergebnis = get_fertigkeit_service().anlegen(
        str(payload.get("name", "")),
        list(payload.get("schritte") or []),
        str(payload.get("beschreibung", "")),
        str(payload.get("ausloeser", "")),
        str(payload.get("quelle", "nutzer")),
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/fertigkeiten/{name}/ausfuehren")
async def fertigkeit_ausfuehren(name: str, payload: dict | None = None) -> dict:
    daten = payload or {}
    return await get_fertigkeit_service().ausfuehren(
        name,
        dict(daten.get("werte") or {}),
        bool(daten.get("bestaetigt")),
        quelle="app",
    )


@router.delete("/fertigkeiten/{name}")
async def fertigkeit_loeschen(name: str) -> dict:
    return {"geloescht": get_fertigkeit_service().loeschen(name)}


@router.get("/plaene")
async def plaene() -> dict:
    return {"plaene": get_planer_service().liste()}


@router.get("/plaene/{kennung}")
async def plan(kennung: str) -> dict:
    daten = get_planer_service().holen(kennung)
    if daten is None:
        raise HTTPException(status_code=404, detail="Diesen Plan kenne ich nicht.")
    return daten


@router.post("/plaene")
async def plan_anlegen(payload: dict) -> dict:
    ergebnis = await get_planer_service().entwerfen(
        str(payload.get("auftrag", "")),
        str(payload.get("ziel", "")),
        str(payload.get("kontext", "")),
        "app",
    )
    if ergebnis.get("error"):
        raise HTTPException(status_code=400, detail=ergebnis["error"])
    return ergebnis


@router.post("/plaene/{kennung}/lauf")
async def plan_lauf(kennung: str, payload: dict | None = None) -> dict:
    dienst = get_planer_service()
    ereignisse = []
    async for eintrag in dienst.ausfuehren(
        kennung, bestaetigt=bool((payload or {}).get("bestaetigt"))
    ):
        ereignisse.append(eintrag)
    daten = dienst.holen(kennung) or {}
    daten["ereignisse"] = ereignisse
    return daten


@router.delete("/plaene/{kennung}")
async def plan_abbrechen(kennung: str) -> dict:
    daten = get_planer_service().abbrechen(kennung)
    if daten is None:
        raise HTTPException(status_code=404, detail="Diesen Plan kenne ich nicht.")
    return daten


@router.get("/aufwand")
async def aufwand(text: str = "") -> dict:
    dienst = get_metakognition_service()
    if text.strip():
        return dienst.einschaetzen(text)
    return dienst.stand()


@router.get("/aufmerksamkeit")
async def aufmerksamkeit(text: str = "") -> dict:
    from app.services.aufmerksamkeit_service import get_aufmerksamkeit_service

    daten = get_aufmerksamkeit_service().waehlen(text)
    daten.pop("bloecke", None)
    return daten
