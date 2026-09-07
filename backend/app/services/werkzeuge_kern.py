from __future__ import annotations

from typing import Any

from app.services.werkzeug_register import antwort, praefix, werkzeug, werkzeug_async


@praefix("browser_")
def _browser(box: Any, args: dict, name: str = "") -> str:
    from app.services.browser.werkzeuge import ausfuehren_json

    return ausfuehren_json(name.removeprefix("browser_"), args)


@werkzeug("browser_wahl")
def _browser_wahl(box: Any, args: dict, name: str = "") -> str:
    from app.services.browserwahl import name as browsername
    from app.services.browserwahl import verfuegbare, wahl
    from app.services.settings_service import get_settings_service

    dienst = get_settings_service()
    aenderung: dict = {}
    wunsch = str(args.get("browser", "")).strip().lower()
    speicher = str(args.get("speicher", "")).strip().lower()
    if wunsch:
        erlaubt = {e["wert"] for e in verfuegbare()}
        if wunsch not in erlaubt:
            return antwort(
                {
                    "ok": False,
                    "fehler": f"Unbekannter Browser: {wunsch}",
                    "moeglich": sorted(erlaubt),
                }
            )
        aenderung["web_browser"] = wunsch
    if speicher in ("ram", "festplatte"):
        aenderung["browser_speicher"] = speicher
        aenderung["browser_persistent"] = speicher == "festplatte"
    if aenderung:
        dienst.update(aenderung)
    werte = dienst.get()
    return antwort(
        {
            "ok": True,
            "browser": wahl(),
            "browser_name": browsername(),
            "speicher": werte.get("browser_speicher", "festplatte"),
            "verfuegbar": verfuegbare(),
            "geaendert": aenderung,
        }
    )


@werkzeug("rueckgaengig")
def _rueckgaengig(box: Any, args: dict, name: str = "") -> str:
    from app.services.rueckgaengig_service import get_rueckgaengig_service

    dienst = get_rueckgaengig_service()
    if args.get("nur_zeigen"):
        return antwort({"eintraege": dienst.liste()})
    return antwort(dienst.rueckgaengig(str(args.get("id", ""))))


@werkzeug("netz_status")
def _netz_status(box: Any, args: dict, name: str = "") -> str:
    from app.services.netz_service import online, stand

    online(erzwingen=bool(args.get("neu")))
    return antwort(stand())


@werkzeug("was_war")
def _was_war(box: Any, args: dict, name: str = "") -> str:
    from app.services.ereignis_service import get_ereignis_service

    dienst = get_ereignis_service()
    raum = str(args.get("zeitraum", "heute")).strip() or "heute"
    bild = dienst.tagesbild(raum)
    thema = str(args.get("thema", "")).strip()
    if thema:
        bild["treffer"] = dienst.suchen(thema, limit=12)
    return antwort(bild)


@werkzeug("verlauf_heute")
def _verlauf_heute(box: Any, args: dict, name: str = "") -> str:
    from app.services.ereignis_service import get_ereignis_service

    return antwort(get_ereignis_service().tagesbild("heute"))


@werkzeug_async("browser_task")
async def _browser_task(box: Any, args: dict, name: str = "") -> str:
    from app.services.browser.agent import auftrag_ausfuehren

    grenze = args.get("max_schritte")
    return antwort(
        await auftrag_ausfuehren(
            str(args.get("auftrag", "")),
            dry_run=bool(args.get("dry_run")),
            max_schritte=int(grenze) if grenze else None,
        )
    )


@werkzeug("ziel")
def _ziel(box: Any, args: dict, name: str = "") -> str:
    from app.services.ziel_service import get_ziel_service

    dienst = get_ziel_service()
    aktion = str(args.get("aktion", "liste")).strip().lower()
    if aktion == "anlegen":
        return antwort(
            dienst.anlegen(
                str(args.get("titel", "")),
                str(args.get("beschreibung", "")),
                str(args.get("frist", "")),
                str(args.get("naechster_schritt", "")),
                float(args.get("wichtigkeit", 0.5) or 0.5),
            )
        )
    if aktion == "aktualisieren":
        return antwort(
            dienst.aktualisieren(
                str(args.get("id", "")),
                str(args.get("zustand", "")),
                str(args.get("naechster_schritt", "")),
                float(args["fortschritt"]) if args.get("fortschritt") is not None else None,
                str(args.get("frist", "")),
                str(args.get("beschreibung", "")),
            )
        )
    if aktion == "loeschen":
        return antwort({"geloescht": dienst.loeschen(str(args.get("id", "")))})
    if aktion == "faellig":
        return antwort({"faellig": dienst.faellig(int(args.get("tage", 2) or 2))})
    return antwort({"ziele": dienst.bereit()})


@werkzeug("weltmodell")
def _weltmodell(box: Any, args: dict, name: str = "") -> str:
    from app.services.weltmodell_service import get_weltmodell_service

    dienst = get_weltmodell_service()
    aktion = str(args.get("aktion", "liste")).strip().lower()
    if aktion == "merken":
        return antwort(
            dienst.merken(
                str(args.get("name", "")),
                str(args.get("art", "sache")),
                str(args.get("beschreibung", "")),
                wichtigkeit=float(args.get("wichtigkeit", 0.5) or 0.5),
            )
        )
    if aktion == "umfeld":
        return antwort(dienst.umfeld(str(args.get("name", ""))))
    if aktion == "verbinden":
        return antwort(
            dienst.verbinden(
                str(args.get("name", "")),
                str(args.get("ziel", "")),
                str(args.get("beziehung", "gehoert_zu")),
            )
        )
    return antwort({"entitaeten": dienst.alle(str(args.get("art", "")), 60)})


@werkzeug("notizblock")
def _notizblock(box: Any, args: dict, name: str = "") -> str:
    from app.services.notizblock_service import get_notizblock_service

    dienst = get_notizblock_service()
    bereich = str(args.get("bereich", "allgemein")) or "allgemein"
    aktion = str(args.get("aktion", "lesen")).strip().lower()
    if aktion == "schreiben":
        return antwort(dienst.schreiben(str(args.get("inhalt", "")), bereich))
    if aktion == "ergaenzen":
        return antwort(dienst.ergaenzen(str(args.get("inhalt", "")), bereich))
    if aktion == "leeren":
        return antwort({"geleert": dienst.leeren(bereich)})
    return antwort({"bereich": bereich, "inhalt": dienst.lesen(bereich)})


@werkzeug("selbstbild")
def _selbstbild(box: Any, args: dict, name: str = "") -> str:
    from app.services.selbst_service import get_selbst_service

    dienst = get_selbst_service()
    aufgabe = str(args.get("aufgabe", "")).strip()
    if aufgabe:
        return antwort(dienst.kann_ich(aufgabe))
    return antwort(dienst.selbstbild())


@werkzeug("erfahrung")
def _erfahrung(box: Any, args: dict, name: str = "") -> str:
    from app.services.erfahrung_service import get_erfahrung_service

    dienst = get_erfahrung_service()
    bereich = str(args.get("bereich", "")).strip()
    if str(args.get("aktion", "")).lower() == "notieren":
        return antwort(
            dienst.notieren(
                bereich or "werkzeug:allgemein",
                str(args.get("text", "")),
                str(args.get("art", "klappt")),
            )
        )
    if bereich:
        return antwort({"bereich": bereich, "erfahrungen": dienst.fuer(bereich)})
    return antwort({"erfahrungen": dienst.alle(40)})


@werkzeug("weltzustand")
def _weltzustand(box: Any, args: dict, name: str = "") -> str:
    from app.services.handlungsraum_service import get_handlungsraum_service

    return antwort(get_handlungsraum_service().zustand())


@werkzeug_async("gedaechtnis_pflegen")
async def _gedaechtnis_pflegen(box: Any, args: dict, name: str = "") -> str:
    from app.services.konsolidierung_service import get_konsolidierung_service

    return antwort(
        await get_konsolidierung_service().lauf(str(args.get("tag", "gestern")))
    )


@werkzeug_async("initiative")
async def _initiative(box: Any, args: dict, name: str = "") -> str:
    from app.services.initiative_service import get_initiative_service

    dienst = get_initiative_service()
    aktion = str(args.get("aktion", "liste")).strip().lower()
    if aktion == "lauf":
        return antwort(await dienst.lauf(erzwingen=True))
    if aktion == "ausfuehren":
        return antwort(await dienst.ausfuehren(str(args.get("id", ""))))
    if aktion in ("annehmen", "verwerfen"):
        return antwort(dienst.entscheiden(str(args.get("id", "")), aktion == "annehmen"))
    return antwort({"vorschlaege": dienst.alle()})


@werkzeug_async("team")
async def _team(box: Any, args: dict, name: str = "") -> str:
    from app.services.agenten_service import get_agenten_service

    return antwort(
        await get_agenten_service().bearbeiten(
            str(args.get("aufgabe", "")), int(args.get("agenten", 3) or 3)
        )
    )


@werkzeug_async("lernen")
async def _lernen(box: Any, args: dict, name: str = "") -> str:
    from app.services.lernen_service import get_lernen_service

    dienst = get_lernen_service()
    aktion = str(args.get("aktion", "muster")).strip().lower()
    if aktion == "skill":
        return antwort(await dienst.skill_aus_lauf(str(args.get("id", "")), str(args.get("titel", ""))))
    if aktion == "training":
        return antwort(dienst.trainingsdaten())
    if aktion == "auswerten":
        return antwort(await dienst.lernen())
    return antwort({"muster": dienst.muster(), "antimuster": dienst.antimuster()})
