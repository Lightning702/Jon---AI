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


@werkzeug("geraete")
def _geraete(box: Any, args: dict, name: str = "") -> str:
    from app.services.verbund_service import get_verbund_service

    return antwort({"geraete": get_verbund_service().geraete()})


@werkzeug_async("geraet_fragen")
async def _geraet_fragen(box: Any, args: dict, name: str = "") -> str:
    from app.services.verbund_service import VerbundFehler, get_verbund_service

    dienst = get_verbund_service()
    try:
        eintrag = dienst.finden(str(args.get("geraet", "")))
        text = await dienst.fragen(eintrag["id"], str(args.get("frage", "")))
    except VerbundFehler as fehler:
        return antwort({"ok": False, "fehler": str(fehler)})
    return antwort({"ok": True, "geraet": eintrag.get("name", ""), "antwort": text})


@werkzeug_async("uebertragung")
async def _uebertragung(box: Any, args: dict, name: str = "") -> str:
    import asyncio

    from app.services.live_service import LiveFehler, get_live_service

    dienst = get_live_service()
    aktion = str(args.get("aktion", "start")).strip().lower()
    if aktion in ("stop", "stopp", "ende", "aus"):
        return antwort(dienst.stoppen())
    if aktion in ("stand", "status"):
        return antwort(dienst.stand())
    welcher = str(args.get("welcher", "alle")).strip() or "alle"
    ziel = str(args.get("geraet", "")).strip()
    if ziel:
        from app.services.verbund_service import VerbundFehler, get_verbund_service

        verbund = get_verbund_service()
        try:
            eintrag = verbund.finden(ziel)
            await verbund.bildschirm(eintrag["id"], welcher)
        except VerbundFehler as fehler:
            return antwort({"ok": False, "fehler": str(fehler)})
        return antwort(
            {
                "ok": True,
                "geraet": eintrag.get("name", ""),
                "bild": f"/api/verbund/{eintrag['id']}/bild?welcher={welcher}",
            }
        )
    try:
        stand = await asyncio.to_thread(
            dienst.starten, welcher, float(args.get("takt", 2.0) or 2.0)
        )
    except LiveFehler as fehler:
        return antwort({"ok": False, "fehler": str(fehler)})
    chat = str(args.get("telegram", "")).strip()
    if chat:
        from app.services.telegram_service import get_telegram_service

        await get_telegram_service().live_starten(chat, welcher)
    return antwort({"ok": True, **stand})


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


@werkzeug_async("beobachten")
async def _beobachten(box: Any, args: dict, name: str = "") -> str:
    from app.services.beobachten import get_beobachten

    dienst = get_beobachten()
    aktion = str(args.get("aktion", "liste")).strip().lower()
    try:
        if aktion == "anlegen":
            eintrag = dienst.anlegen(str(args.get("frage", "")), str(args.get("bedingung", "")), args.get("intervall_stunden") or 24)
            return antwort({"ok": True, "beobachtung": eintrag, "hinweis": f"Jon prüft das alle {eintrag['intervall_stunden']:g} Stunden, solange er auf dem PC oder Pi läuft, und meldet sich in der App und über Telegram."})
        if aktion == "stoppen":
            return antwort({"ok": True, "beobachtung": dienst.stoppen(str(args.get("id", "")))})
        return antwort({"ok": True, "beobachtungen": [{k: e.get(k) for k in ("id", "frage", "bedingung", "status", "letzter_check", "intervall_stunden", "treffer")} for e in dienst.liste()]})
    except (ValueError, KeyError) as fehler:
        return antwort({"error": str(fehler).strip("'\"")})


@werkzeug_async("team")
async def _team(box: Any, args: dict, name: str = "") -> str:
    from app.services.agenten_service import get_agenten_service
    from app.services.tools import _QUELLE

    from app.services.agenten_service import kuerzen

    lauf = await get_agenten_service().bearbeiten(
        str(args.get("aufgabe", "")), int(args.get("agenten", 3) or 3),
        source=_QUELLE.get() or box._source,
        slot=getattr(box, "_slot", "jon"),
        persist=getattr(box, "_persist", True),
        research=args.get("internet") is True,
        run_id=str(args.get("_lauf") or "") or None,
        material=str(getattr(box, "_material", "") or ""),
    )
    text = str(lauf.get("antwort") or "")
    ergebnis = {"status": lauf["status"], "vollstaendig": lauf.get("vollstaendig", False), "antwort": kuerzen(text, 6000), "antwort_zeichen": len(text), "gespeichert_in": lauf.get("datei", ""), "teile": [{"titel": p.get("titel", ""), "status": p.get("status", "")} for p in lauf.get("teile", [])], "pruefung": {"ok": (lauf.get("pruefung") or {}).get("ok"), "probleme": ((lauf.get("pruefung") or {}).get("probleme") or [])[:5]}, "fehler": lauf.get("fehler", ""), "hinweis": lauf.get("hinweis", "")}
    if len(text) > 6000:
        ergebnis["anweisung"] = f"Das vollständige Ergebnis ({len(text)} Zeichen) steht in der Fachteam-Karte im Chat und in der Datei {lauf.get('datei') or 'im Agenten-Ordner'}. Gib es nicht gekürzt erneut aus, sondern sag dem Nutzer, wo er es findet, und fasse höchstens kurz zusammen."
    return antwort(ergebnis)


@werkzeug_async("youtube_transkript")
async def _youtube_transkript(box: Any, args: dict, name: str = "") -> str:
    import asyncio
    from app.services.media_service import fetch_youtube, get_media_service

    data = await asyncio.to_thread(fetch_youtube, str(args.get("url", "")))
    text = data.pop("text")
    data["zusammenfassung"] = await get_media_service().summarize(text, data["title"], slot=getattr(box, "slot", "jon"))
    data["zeichen"] = len(text)
    data["hinweis"] = "Aus den Untertiteln, nicht aus einer Sichtung der Videobilder."
    return antwort(data)


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


@werkzeug("aufgabe")
def _aufgabe(box: Any, args: dict, name: str = "") -> str:
    from app.services.aufgaben_service import OFFEN, get_aufgaben_service

    dienst = get_aufgaben_service()
    aktion = str(args.get("aktion", "anlegen")).strip().lower()
    kennung = str(args.get("id", "")).strip()
    if aktion in ("liste", "zeigen", "stand"):
        return antwort(dienst.stand())
    if aktion == "pausieren":
        return antwort(dienst.pausieren(kennung) or {"error": "unbekannt"})
    if aktion in ("fortsetzen", "weiter"):
        return antwort(dienst.fortsetzen(kennung) or {"error": "unbekannt"})
    if aktion in ("abbrechen", "loeschen"):
        return antwort(dienst.abbrechen(kennung) or {"error": "unbekannt"})
    if aktion == "freigeben":
        return antwort(
            dienst.freigeben(kennung, args.get("erlaubt", True) is not False)
            or {"error": "unbekannt"}
        )
    if aktion in ("holen", "status") and kennung:
        return antwort(dienst.holen(kennung) or {"error": "unbekannt"})
    return antwort(
        dienst.anlegen(
            str(args.get("auftrag", "")),
            int(args.get("budget_minuten", 20) or 20),
            int(args.get("prioritaet", 5) or 5),
            str(args.get("titel", "")),
            quelle=getattr(box, "_source", "app"),
        )
    )


@werkzeug_async("aufgabe_starten")
async def _aufgabe_starten(box: Any, args: dict, name: str = "") -> str:
    from app.services.aufgaben_service import get_aufgaben_service

    return antwort(await get_aufgaben_service().lauf(str(args.get("id", ""))))


@werkzeug("durchspielen")
def _durchspielen(box: Any, args: dict, name: str = "") -> str:
    from app.services.vorwaerts_service import get_vorwaerts_service

    dienst = get_vorwaerts_service()
    schritte = args.get("schritte")
    if isinstance(schritte, list) and schritte:
        return antwort(dienst.durchspielen(schritte))
    return antwort(
        dienst.vorhersagen(str(args.get("werkzeug", "")), args.get("args") or {})
    )


@werkzeug_async("hypothese")
async def _hypothese(box: Any, args: dict, name: str = "") -> str:
    from app.services.hypothese_service import get_hypothese_service

    dienst = get_hypothese_service()
    aktion = str(args.get("aktion", "stand")).strip().lower()
    if aktion in ("vermuten", "anlegen"):
        beobachtung = str(args.get("beobachtung", "")).strip()
        if beobachtung:
            return antwort(await dienst.vermuten(beobachtung, str(args.get("bereich", ""))))
        return antwort(
            dienst.anlegen(
                str(args.get("vermutung", "")),
                str(args.get("test", "")),
                str(args.get("werkzeug", "keins")),
                args.get("args") or {},
                str(args.get("bereich", "")),
            )
        )
    if aktion in ("pruefen", "testen"):
        return antwort(await dienst.pruefen(str(args.get("id", ""))))
    if aktion == "lauf":
        return antwort(await dienst.lauf(int(args.get("anzahl", 2) or 2)))
    return antwort(dienst.stand())


@werkzeug("oberflaeche")
def _oberflaeche(box: Any, args: dict, name: str = "") -> str:
    from app.services.oberflaeche_service import liste, oeffnen

    ziel = str(args.get("werkzeug", "") or args.get("ziel", "")).strip()
    aktion = str(args.get("aktion", "")).strip().lower()
    datei = str(args.get("datei", "") or args.get("pfad", "")).strip()
    if (not ziel and not datei) or aktion in ("liste", "zeigen"):
        return antwort(liste())
    return antwort(oeffnen(ziel, aktion or "oeffnen", datei))


@werkzeug("ausloeser")
def _ausloeser(box: Any, args: dict, name: str = "") -> str:
    from app.services.ausloeser_service import AusloeserFehler, get_ausloeser_service

    dienst = get_ausloeser_service()
    aktion = str(args.get("aktion", "")).strip().lower()
    try:
        if aktion in ("", "liste", "zeigen"):
            return antwort(dienst.liste())
        if aktion in ("anlegen", "neu", "merken"):
            return antwort(
                dienst.anlegen(
                    str(args.get("art", "taeglich")),
                    str(args.get("auftrag", "")),
                    str(args.get("titel", "")),
                    str(args.get("zeit", "")),
                    args.get("tage"),
                    int(args.get("minuten", 0) or 0),
                    str(args.get("ordner", "")),
                    str(args.get("muster", "*")),
                    int(args.get("budget", 15) or 15),
                )
            )
        if aktion in ("aus", "pausieren", "stopp"):
            return antwort(dienst.schalten(str(args.get("id", "")), False))
        if aktion in ("an", "weiter", "einschalten"):
            return antwort(dienst.schalten(str(args.get("id", "")), True))
        if aktion in ("loeschen", "entfernen"):
            return antwort(dienst.loeschen(str(args.get("id", ""))))
        if aktion in ("pruefen", "jetzt"):
            return antwort(dienst.pruefen())
        return antwort({"error": f"Unbekannte Aktion: {aktion}"})
    except AusloeserFehler as fehler:
        return antwort({"error": str(fehler)})


@werkzeug("bericht")
def _bericht(box: Any, args: dict, name: str = "") -> str:
    from app.services.aufgaben_service import get_aufgaben_service
    from app.services.ausloeser_service import get_ausloeser_service
    from app.services.rueckgaengig_service import get_rueckgaengig_service

    grenze = max(1, min(30, int(args.get("anzahl", 8) or 8)))
    stand = get_aufgaben_service().stand()
    aenderungen = get_rueckgaengig_service().liste(grenze)
    ausloeser = [
        eintrag
        for eintrag in get_ausloeser_service().liste()["ausloeser"]
        if eintrag.get("aktiv")
    ]
    return antwort(
        {
            "aufgaben": {
                "laeuft": stand.get("laeuft"),
                "wartet": stand.get("wartet"),
                "fertig": stand.get("fertig"),
                "gescheitert": stand.get("gescheitert"),
                "braucht_freigabe": stand.get("braucht_freigabe", []),
                "offen": stand.get("offen", [])[:grenze],
            },
            "aenderungen": aenderungen,
            "ausloeser": ausloeser,
            "hinweis": (
                "Sag dem Nutzer in kurzen Saetzen, was seit seiner letzten Anwesenheit "
                "passiert ist. Nenne offene Freigaben zuerst. Jede Aenderung laesst "
                "sich mit rueckgaengig und der id zuruecknehmen."
            ),
        }
    )


def _datei_frei(pfad: str) -> str:
    from pathlib import Path

    from app.services.dateiraum_service import get_dateiraum_service

    erlaubt, grund = get_dateiraum_service().frei(Path(str(pfad or "")).expanduser())
    return "" if erlaubt else grund


def _mit_karte(box: Any, ergebnis: dict, beschreibung: str) -> dict:
    if ergebnis.get("ok") and ergebnis.get("path"):
        try:
            from pathlib import Path

            from app.services.dateiindex_service import get_dateiindex_service

            ergebnis["datei"] = get_dateiindex_service().karte_und_merken(ergebnis["path"], Path(ergebnis["path"]).stem, beschreibung, quelle=getattr(box, "_source", "app"))
        except Exception as fehler:
            from app.core.fehler import leise

            leise(fehler, "services/werkzeuge_kern")
    return ergebnis


def _aktionen(args: dict) -> list:
    import json

    roh = args.get("aktionen") or args.get("actions") or []
    if isinstance(roh, str):
        try:
            roh = json.loads(roh)
        except ValueError:
            return []
    if isinstance(roh, dict):
        roh = [roh]
    return [a for a in roh if isinstance(a, dict)]


@werkzeug_async("bild_suche")
async def _bild_suche(box: Any, args: dict, name: str = "") -> str:
    from app.services.bildquelle import herunterladen, suchen

    adresse = str(args.get("url", "") or "").strip()
    begriff = str(args.get("query", "") or args.get("suche", "") or args.get("bild_suche", "")).strip()
    if adresse:
        try:
            pfad = await herunterladen(adresse)
        except Exception as fehler:
            return antwort({"error": f"Bild konnte nicht geladen werden: {fehler}"})
    elif begriff:
        pfad = await suchen(begriff)
    else:
        return antwort({"error": "query (englischer Suchbegriff) oder url fehlt."})
    if not pfad:
        return antwort({"error": f"Kein passendes freies Foto zu '{begriff}' gefunden. Versuche einen anderen englischen Begriff oder bild_prompt."})
    return antwort({"ok": True, "pfad": pfad, "hinweis": "Diesen Pfad kannst du als image in create_pptx, edit_pptx oder edit_docx verwenden."})


@werkzeug_async("edit_pptx")
async def _edit_pptx(box: Any, args: dict, name: str = "") -> str:
    from app.services.pptx_bearbeiten import bearbeiten

    pfad = str(args.get("path", "") or args.get("pfad", ""))
    gesperrt = _datei_frei(pfad)
    if gesperrt:
        return antwort({"error": gesperrt})
    ergebnis = await bearbeiten(pfad, _aktionen(args), str(args.get("theme", "")))
    return antwort(_mit_karte(box, ergebnis, "Von Jon bearbeitete Praesentation"))


@werkzeug_async("edit_docx")
async def _edit_docx(box: Any, args: dict, name: str = "") -> str:
    from app.services.docx_bearbeiten import bearbeiten

    pfad = str(args.get("path", "") or args.get("pfad", ""))
    gesperrt = _datei_frei(pfad)
    if gesperrt:
        return antwort({"error": gesperrt})
    ergebnis = await bearbeiten(pfad, _aktionen(args))
    return antwort(_mit_karte(box, ergebnis, "Von Jon bearbeitetes Word-Dokument"))


@werkzeug("read_docx")
def _read_docx(box: Any, args: dict, name: str = "") -> str:
    from app.services.docx_bearbeiten import lesen

    pfad = str(args.get("path", "") or args.get("pfad", ""))
    gesperrt = _datei_frei(pfad)
    if gesperrt:
        return antwort({"error": gesperrt})
    return antwort(lesen(pfad))


@werkzeug("datei_kommentare")
def _datei_kommentare(box: Any, args: dict, name: str = "") -> str:
    from app.services.kommentar_service import beschreibung, get_kommentar_service

    dienst = get_kommentar_service()
    aktion = str(args.get("aktion", "lesen")).strip().lower()
    kennungen = args.get("ids") or ([args["id"]] if args.get("id") else [])
    if isinstance(kennungen, str):
        kennungen = [k.strip() for k in kennungen.split(",") if k.strip()]
    if aktion in ("erledigt", "fertig", "abhaken"):
        erledigt = [k for k in kennungen if dienst.aendern(str(k), True, antwort=str(args.get("antwort", "")) or None)]
        return antwort({"ok": bool(erledigt), "erledigt": erledigt, **({} if erledigt else {"error": "Keine passenden Kommentar-IDs."})})
    if aktion in ("antworten", "antwort"):
        geaendert = [k for k in kennungen if dienst.aendern(str(k), antwort=str(args.get("antwort", "")))]
        return antwort({"ok": bool(geaendert), "beantwortet": geaendert})
    pfad = str(args.get("path", "") or args.get("pfad", ""))
    gesperrt = _datei_frei(pfad)
    if gesperrt:
        return antwort({"error": gesperrt})
    if aktion in ("anlegen", "neu", "notieren"):
        eintrag = dienst.anlegen(pfad, str(args.get("text", "")), args.get("stelle") if isinstance(args.get("stelle"), dict) else {}, "jon")
        return antwort({"ok": True, "kommentar": eintrag})
    offen = str(args.get("alle", "")).lower() not in ("true", "1", "ja")
    return antwort({
        "path": pfad,
        "kommentare": [
            {"id": k["id"], "wo": beschreibung(k.get("stelle") or {}), "stelle": k.get("stelle"), "text": k["text"], "erledigt": k.get("erledigt", False)}
            for k in dienst.liste(pfad, offen=offen)
        ],
    })


@werkzeug_async("was_laeuft")
async def _was_laeuft(box: Any, args: dict, name: str = "") -> str:
    import asyncio

    from app.services.medien_jetzt import jetzt

    stand = await asyncio.to_thread(jetzt)
    if stand.get("lied") or stand.get("lied_aus_fenster"):
        return antwort({"ok": True, **stand})
    frage = str(args.get("frage", "") or "Welches Lied, Video oder welche Musik ist gerade zu sehen? Nenne Titel und Interpret, wenn sie sichtbar sind.")
    try:
        from app.services.mini_jon_agent import get_mini_jon_agent
        from app.services.mini_jon_screen import analyze

        gesehen = await analyze(get_mini_jon_agent(), frage)
        return antwort({"ok": True, "quelle": "bildschirm", **stand, "bildschirm": gesehen})
    except Exception as fehler:
        return antwort({
            "ok": False,
            **stand,
            "hinweis": (
                "Gerade meldet keine App ein laufendes Lied. Den Bildschirm konnte ich auch nicht ansehen: "
                f"{fehler}. Du kannst screenshot und danach look_at_image nutzen, wenn der Nutzer es möchte."
            ),
        })


@werkzeug_async("wechseln")
async def _wechseln(box: Any, args: dict, name: str = "") -> str:
    import asyncio

    from app.services.fenster_wechsel import fenster, wechseln

    ziel = str(args.get("ziel", "") or args.get("title", "") or args.get("name", "")).strip()
    if str(args.get("aktion", "")).strip().lower() in ("liste", "zeigen", "fenster"):
        liste = await asyncio.to_thread(fenster)
        return antwort({"fenster": [{"titel": f["titel"][:100], "programm": f["programm"]} for f in liste[:40]]})
    tabs = str(args.get("tabs", "true")).strip().lower() not in ("false", "0", "nein")
    return antwort(await asyncio.to_thread(wechseln, ziel, tabs))


@werkzeug_async("stundenplan")
async def _stundenplan(box: Any, args: dict, name: str = "") -> str:
    from app.services.stundenplan_service import TAGE, get_stundenplan_service

    dienst = get_stundenplan_service()
    aktion = str(args.get("aktion", "") or "zeigen").strip().lower()
    try:
        if aktion in ("setzen", "speichern", "eintragen", "neu"):
            if isinstance(args.get("tage"), dict) and args["tage"]:
                daten = dienst.setzen(args["tage"], "Jon")
            elif str(args.get("datei", "")).strip():
                daten = await dienst.aus_datei(str(args["datei"]))
            elif str(args.get("text", "")).strip():
                daten = await dienst.aus_text(str(args["text"]))
            else:
                return antwort({"error": "Gib den Stundenplan als tage, text oder datei mit."})
            return antwort({"ok": True, "gespeichert": {t: len(e) for t, e in daten["tage"].items() if e}})
        if aktion in ("tag", "tag_aendern", "aendern"):
            dienst.tag_aendern(str(args.get("tag", "")), list(args.get("eintraege") or []))
            name_tag, eintraege = dienst.fuer(str(args.get("tag", "")))
            return antwort({"ok": True, "tag": name_tag, "eintraege": eintraege})
        if aktion in ("loeschen", "löschen", "entfernen"):
            return antwort({"ok": dienst.loeschen()})
        if aktion in ("heute", "morgen", "tag_zeigen") or str(args.get("tag", "")).strip():
            from datetime import date, timedelta

            wunsch = str(args.get("tag", "")).strip()
            stichtag = wunsch or (date.today() + timedelta(days=1) if aktion == "morgen" else date.today())
            name_tag, eintraege = dienst.fuer(stichtag)
            return antwort({"tag": name_tag, "eintraege": eintraege, "text": dienst.text(stichtag) or f"Am {name_tag.capitalize()} steht nichts im Stundenplan."})
        daten = dienst.laden()
        return antwort({"tage": {t: daten["tage"].get(t, []) for t in TAGE if daten["tage"].get(t)}, "leer": not any(daten["tage"].values())})
    except ValueError as fehler:
        return antwort({"error": str(fehler)})


@werkzeug("morgen_nachricht")
def _morgen_nachricht(box: Any, args: dict, name: str = "") -> str:
    from app.services.settings_service import get_settings_service

    dienst = get_settings_service()
    daten = dienst.get()
    zusaetze = [str(z) for z in daten.get("telegram_morgen_zusaetze") or []]
    aenderung: dict = {}
    if "stundenplan" in args:
        aenderung["telegram_morgen_stundenplan"] = str(args["stundenplan"]).strip().lower() in ("true", "1", "ja", "an")
    neu = str(args.get("hinzufuegen", "") or "").strip()
    if neu and neu not in zusaetze:
        zusaetze.append(neu[:300])
        aenderung["telegram_morgen_zusaetze"] = zusaetze[-12:]
    weg = str(args.get("entfernen", "") or "").strip().lower()
    if weg:
        rest = [z for z in zusaetze if weg not in z.lower()]
        if len(rest) != len(zusaetze):
            aenderung["telegram_morgen_zusaetze"] = rest
            zusaetze = rest
    zeit = str(args.get("zeit", "") or "").strip().replace(".", ":")
    if zeit:
        teile = zeit.split(":")
        if len(teile) == 2 and teile[0].isdigit() and teile[1].isdigit() and int(teile[0]) < 24 and int(teile[1]) < 60:
            aenderung["telegram_morning_time"] = f"{int(teile[0]):02d}:{int(teile[1]):02d}"
        else:
            return antwort({"error": f"Unklare Uhrzeit: {zeit}. Nutze HH:MM."})
    if "an" in args:
        aenderung["telegram_morning"] = str(args["an"]).strip().lower() in ("true", "1", "ja", "an")
    elif aenderung and not daten.get("telegram_morning", False):
        aenderung["telegram_morning"] = True
    if aenderung:
        dienst.update(aenderung)
        daten = dienst.get()
    hinweis = ""
    if daten.get("telegram_morgen_stundenplan"):
        from app.services.stundenplan_service import get_stundenplan_service

        if not any(get_stundenplan_service().laden()["tage"].values()):
            hinweis = "Es ist noch kein Stundenplan gespeichert - frag den Nutzer danach und speichere ihn mit stundenplan (aktion setzen)."
    if not str(daten.get("telegram_token", "") or "").strip() and not str(daten.get("telegram_bot_token", "") or "").strip():
        hinweis = (hinweis + " " if hinweis else "") + "Telegram ist evtl. noch nicht eingerichtet (Einstellungen -> Verbindungen -> Telegram)."
    return antwort({
        "ok": True,
        "an": bool(daten.get("telegram_morning")),
        "uhrzeit": daten.get("telegram_morning_time", "07:30"),
        "stundenplan": bool(daten.get("telegram_morgen_stundenplan")),
        "zusaetze": daten.get("telegram_morgen_zusaetze") or [],
        **({"hinweis": hinweis} if hinweis else {}),
    })
