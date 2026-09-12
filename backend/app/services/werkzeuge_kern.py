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


@werkzeug("selbsteinschaetzung")
def _selbsteinschaetzung(box: Any, args: dict, name: str = "") -> str:
    from app.services.erwartung_service import get_erwartung_service
    from app.services.metakognition_service import get_metakognition_service

    dienst = get_erwartung_service()
    werkzeug_name = str(args.get("werkzeug", "")).strip()
    if werkzeug_name:
        return antwort(dienst.schaetzen(werkzeug_name, args.get("args") or {}))
    aufgabe = str(args.get("aufgabe", "")).strip()
    daten = dienst.stand()
    if aufgabe:
        daten["aufwand"] = get_metakognition_service().einschaetzen(aufgabe)
    return antwort(daten)


@werkzeug("ueberraschungen")
def _ueberraschungen(box: Any, args: dict, name: str = "") -> str:
    from app.services.erwartung_service import get_erwartung_service

    dienst = get_erwartung_service()
    tage = int(args.get("tage", 14) or 14)
    return antwort(
        {
            "kalibrierung": dienst.kalibrierung(tage),
            "ueberraschungen": dienst.ueberraschungen(int(args.get("limit", 10) or 10), tage),
        }
    )


@werkzeug("frage_merken")
def _frage_merken(box: Any, args: dict, name: str = "") -> str:
    from app.services.neugier_service import get_neugier_service

    return antwort(
        get_neugier_service().fragen(
            str(args.get("frage", "")),
            str(args.get("thema", "")),
            "werkzeug",
            float(args.get("dringlichkeit", 0.5) or 0.5),
        )
    )


@werkzeug("offene_fragen")
def _offene_fragen(box: Any, args: dict, name: str = "") -> str:
    from app.services.neugier_service import get_neugier_service

    dienst = get_neugier_service()
    return antwort(
        {
            "offen": dienst.offene(int(args.get("limit", 15) or 15)),
            "beantwortet": dienst.beantwortete(8),
            "stand": dienst.stand(),
        }
    )


@werkzeug_async("frage_klaeren")
async def _frage_klaeren(box: Any, args: dict, name: str = "") -> str:
    from app.services.neugier_service import get_neugier_service

    dienst = get_neugier_service()
    kennung = str(args.get("id", "")).strip()
    if kennung:
        return antwort(await dienst.beantworten(kennung))
    return antwort(await dienst.lauf(int(args.get("anzahl", 3) or 3)))


@werkzeug("fertigkeiten")
def _fertigkeiten(box: Any, args: dict, name: str = "") -> str:
    from app.services.fertigkeit_service import get_fertigkeit_service

    dienst = get_fertigkeit_service()
    aktion = str(args.get("aktion", "zeigen")).strip().lower()
    if aktion == "entdecken":
        return antwort({"vorschlaege": dienst.entdecken()})
    if aktion == "loeschen":
        return antwort({"geloescht": dienst.loeschen(str(args.get("name", "")))})
    if aktion == "lernen":
        return antwort(
            dienst.anlegen(
                str(args.get("name", "")),
                list(args.get("schritte") or []),
                str(args.get("beschreibung", "")),
                str(args.get("ausloeser", "")),
            )
        )
    suche = str(args.get("suche", "")).strip()
    if suche:
        return antwort({"treffer": dienst.passende(suche)})
    return antwort(dienst.stand())


@werkzeug_async("fertigkeit_nutzen")
async def _fertigkeit_nutzen(box: Any, args: dict, name: str = "") -> str:
    from app.services.fertigkeit_service import get_fertigkeit_service

    return antwort(
        await get_fertigkeit_service().ausfuehren(
            str(args.get("name", "")),
            dict(args.get("werte") or {}),
            bool(args.get("bestaetigt")),
        )
    )


@werkzeug_async("plan_machen")
async def _plan_machen(box: Any, args: dict, name: str = "") -> str:
    from app.services.planer_service import get_planer_service

    dienst = get_planer_service()
    plan = await dienst.entwerfen(
        str(args.get("auftrag", "")),
        str(args.get("ziel", "")),
        str(args.get("kontext", "")),
    )
    if plan.get("error") or not args.get("ausfuehren"):
        return antwort(plan)
    ereignisse = []
    async for eintrag in dienst.ausfuehren(
        plan["id"], bestaetigt=bool(args.get("bestaetigt"))
    ):
        ereignisse.append(eintrag)
    fertig = dienst.holen(plan["id"]) or plan
    fertig["ereignisse"] = ereignisse
    return antwort(fertig)


@werkzeug_async("plan_ausfuehren")
async def _plan_ausfuehren(box: Any, args: dict, name: str = "") -> str:
    from app.services.planer_service import get_planer_service

    dienst = get_planer_service()
    kennung = str(args.get("id", "")).strip()
    if not kennung:
        return antwort({"error": "Welchen Plan? Es fehlt die id."})
    if args.get("abbrechen"):
        return antwort(dienst.abbrechen(kennung) or {"error": "unbekannt"})
    ereignisse = []
    async for eintrag in dienst.ausfuehren(
        kennung, bestaetigt=bool(args.get("bestaetigt"))
    ):
        ereignisse.append(eintrag)
    fertig = dienst.holen(kennung) or {}
    fertig["ereignisse"] = ereignisse
    return antwort(fertig)


@werkzeug("datei_erstellen")
def _datei_erstellen(box: Any, args: dict, name: str = "") -> str:
    from app.services.dokument_service import get_dokument_service

    return antwort(
        get_dokument_service().erstellen(
            str(args.get("art", "txt")),
            str(args.get("titel", "")),
            args.get("inhalt", ""),
            str(args.get("ort", "")),
            str(args.get("dateiname", "")),
            str(args.get("projekt", "")),
            quelle=getattr(box, "_source", "app"),
        )
    )


@werkzeug("ordner_anlegen")
def _ordner_anlegen(box: Any, args: dict, name: str = "") -> str:
    from app.services.dateiraum_service import get_dateiraum_service

    wunsch = str(args.get("ort", "")).strip()
    ordner = str(args.get("name", "")).strip()
    ziel = f"{wunsch}/{ordner}" if wunsch and ordner else (wunsch or ordner)
    ergebnis = get_dateiraum_service().zielordner(ziel)
    if ergebnis.get("error"):
        return antwort(ergebnis)
    return antwort({"ok": True, "ordner": ergebnis["pfad"]})


@werkzeug("datei_oeffnen")
def _datei_oeffnen(box: Any, args: dict, name: str = "") -> str:
    from app.services import plattform
    from app.services.dateiraum_service import get_dateiraum_service
    from pathlib import Path

    ziel = Path(str(args.get("pfad", ""))).expanduser()
    erlaubt, grund = get_dateiraum_service().frei(ziel)
    if not erlaubt:
        return antwort({"error": grund})
    if args.get("ordner"):
        return antwort(plattform.ordner_oeffnen(ziel))
    return antwort(plattform.datei_oeffnen(ziel))


@werkzeug("ordner_oeffnen")
def _ordner_oeffnen(box: Any, args: dict, name: str = "") -> str:
    from app.services import plattform
    from app.services.dateiraum_service import get_dateiraum_service
    from pathlib import Path

    roh = str(args.get("pfad", "")).strip()
    if not roh:
        ziel = get_dateiraum_service().sicherstellen()
    else:
        gewuenscht = get_dateiraum_service().zielordner(roh)
        if gewuenscht.get("error"):
            ziel = Path(roh).expanduser()
        else:
            ziel = Path(gewuenscht["pfad"])
    erlaubt, grund = get_dateiraum_service().frei(ziel)
    if not erlaubt:
        return antwort({"error": grund})
    return antwort(plattform.ordner_oeffnen(ziel))


@werkzeug("dateien_finden")
def _dateien_finden(box: Any, args: dict, name: str = "") -> str:
    from app.services.dateiindex_service import get_dateiindex_service, karte

    dienst = get_dateiindex_service()
    frage = str(args.get("frage", "")).strip()
    grenze = int(args.get("limit", 10) or 10)
    treffer = (
        dienst.suchen(frage, grenze)
        if frage
        else dienst.liste(str(args.get("art", "")), limit=grenze)
    )
    return antwort(
        {
            "gefunden": len(treffer),
            "dateien": [
                karte(e["pfad"], e.get("projekt", ""), e.get("titel", ""))
                for e in treffer
                if e.get("vorhanden", True)
            ],
            "treffer": treffer,
        }
    )


@werkzeug("dateiraum")
def _dateiraum(box: Any, args: dict, name: str = "") -> str:
    from app.services.dateiindex_service import get_dateiindex_service
    from app.services.dateiraum_service import get_dateiraum_service

    return antwort(
        {
            "raum": get_dateiraum_service().stand(),
            "index": get_dateiindex_service().stand(),
        }
    )


@werkzeug("umgebung")
def _umgebung(box: Any, args: dict, name: str = "") -> str:
    from app.services.umgebung_service import get_umgebung_service

    return antwort(get_umgebung_service().pruefen(bool(args.get("neu"))))


@werkzeug_async("blender_szene")
async def _blender_szene(box: Any, args: dict, name: str = "") -> str:
    from app.services.blender_service import get_blender_service

    return antwort(
        await get_blender_service().szene(
            str(args.get("auftrag", "")),
            str(args.get("projekt", "")),
            str(args.get("ort", "")),
            bool(args.get("rendern", True)),
            str(args.get("export", "")),
            quelle=getattr(box, "_source", "app"),
        )
    )


@werkzeug("blender_render")
def _blender_render(box: Any, args: dict, name: str = "") -> str:
    from app.services.blender_service import get_blender_service

    return antwort(
        get_blender_service().rendern(
            str(args.get("datei", "")),
            int(args.get("breite", 1280) or 1280),
            int(args.get("hoehe", 720) or 720),
        )
    )


@werkzeug("blender_export")
def _blender_export(box: Any, args: dict, name: str = "") -> str:
    from app.services.blender_service import get_blender_service

    dienst = get_blender_service()
    if args.get("oeffnen"):
        return antwort(dienst.oeffnen(str(args.get("datei", ""))))
    return antwort(
        dienst.exportieren(str(args.get("datei", "")), str(args.get("format", "glb")))
    )


@werkzeug("desktop_verknuepfung")
def _desktop_verknuepfung(box: Any, args: dict, name: str = "") -> str:
    from app.services import verknuepfung_service

    aktion = str(args.get("aktion", "anlegen")).strip().lower()
    if aktion in ("entfernen", "loeschen", "weg"):
        return antwort(verknuepfung_service.entfernen())
    if aktion in ("status", "pruefen", "zeigen"):
        return antwort(verknuepfung_service.stand())
    return antwort(verknuepfung_service.anlegen(str(args.get("ziel", ""))))
