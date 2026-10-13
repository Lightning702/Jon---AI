from __future__ import annotations

import asyncio
import json
from typing import Any

from app.services.werkzeug_register import antwort, werkzeug, werkzeug_async

ARTEN = {
    "handy": "handy", "smartphone": "handy", "telefon": "handy", "android": "handy", "iphone": "handy",
    "tablet": "tablet", "ipad": "tablet",
    "uhr": "uhr", "smartwatch": "uhr", "watch": "uhr", "armbanduhr": "uhr",
    "jon": "jon", "pi": "jon", "raspberry": "jon", "pc": "jon", "computer": "jon", "laptop": "jon", "server": "jon",
}


def _art(roh: Any) -> str:
    text = str(roh or "").strip().lower()
    if text in ARTEN:
        return ARTEN[text]
    for wort, art in ARTEN.items():
        if wort in text:
            return art
    return "handy"


def _handy_kopplung(art: str) -> dict:
    from app.services.handy_service import get_handy_service

    daten = get_handy_service().kopplung_starten(True)
    return {
        "ok": True,
        "art": art,
        "code": daten["code"],
        "code_gruppiert": daten["code_gruppiert"],
        "nutzlast": daten["nutzlast"],
        "ablauf": daten["ablauf"],
        "pc": daten["pc"].get("name", ""),
        "heimnetz": bool(daten.get("heimnetz")),
        "anleitung": (
            "Öffne auf dem Gerät die App „Jon Gerät“, tippe auf „Mit Jon verbinden“ und scanne "
            "den QR-Code. Danach bestätigst du die Anfrage hier im Chat."
        ),
    }


async def _uhr_kopplung() -> dict:
    from app.services.handy_service import HandyFehler, get_handy_service

    dienst = get_handy_service()
    handys = [g for g in dienst.geraete() if g.get("typ", "handy") in ("handy", "tablet") and g.get("online")]
    for handy in handys:
        try:
            ergebnis = await dienst.auftrag(handy["id"], "uhr-koppeln", {}, wartezeit=100.0)
        except HandyFehler:
            continue
        if ergebnis.get("ok"):
            daten = ergebnis.get("daten") or {}
            return {
                "ok": True,
                "art": "uhr",
                "fertig": True,
                "uhr": daten.get("uhr") or "Smartwatch",
                "handy": handy.get("name", ""),
                "anleitung": f"Die Uhr ist jetzt über {handy.get('name', 'das Handy')} mit Jon verbunden.",
            }
    daten = await asyncio.to_thread(dienst.kopplung_starten, False)
    return {
        "ok": True,
        "art": "uhr",
        "code": daten["code"],
        "code_gruppiert": daten["code_gruppiert"],
        "ablauf": daten["ablauf"],
        "pc": daten["pc"].get("name", ""),
        "anleitung": (
            "Installiere „Jon“ auf der Uhr. Am schnellsten geht es in der Handy-App unter "
            "Einstellungen → Uhr koppeln. Ohne Handy tippst du auf der Uhr „Code eingeben“ "
            "und gibst diesen Code ein."
        ),
    }


def _jon_kopplung(code: str) -> dict:
    from app.services.handy_service import get_handy_service

    if code.strip():
        from app.services.verbund_service import VerbundFehler, get_verbund_service

        try:
            eintrag = get_verbund_service().koppeln(code)
        except VerbundFehler as fehler:
            return {"ok": False, "error": str(fehler)}
        return {"ok": True, "art": "jon", "fertig": True, "jon": eintrag.get("name", ""), "anleitung": f"{eintrag.get('name', 'Der andere Jon')} ist jetzt im Verbund."}
    daten = get_handy_service().kopplung_starten(False)
    return {
        "ok": True,
        "art": "jon",
        "code": daten["code"],
        "code_gruppiert": daten["code_gruppiert"],
        "ablauf": daten["ablauf"],
        "pc": daten["pc"].get("name", ""),
        "anleitung": (
            "Gib diesen Code auf dem anderen Jon ein (zum Beispiel am Pi: „Verbinde dich mit "
            "Code …“ oder Einstellungen → Geräte-Verbund). Danach bestätigst du hier im Chat."
        ),
    }


@werkzeug_async("geraet_verbinden")
async def _geraet_verbinden(box: Any, args: dict, name: str = "") -> str:
    art = _art(args.get("art"))
    code = str(args.get("code") or "")
    if art == "uhr":
        return antwort(await _uhr_kopplung())
    if art == "jon" and not code.strip():
        from app.services.pc_kopplung import verbinden

        return antwort(await verbinden(str(args.get("name", "") or "")))
    if art == "jon":
        return antwort(await asyncio.to_thread(_jon_kopplung, code))
    return antwort(await asyncio.to_thread(_handy_kopplung, art))


@werkzeug_async("karteikarten")
async def _karteikarten(box: Any, args: dict, name: str = "") -> str:
    from app.services.flashcards_service import get_flashcards_service

    dienst = get_flashcards_service()
    aktion = str(args.get("aktion") or "neu").strip().lower()
    decks = dienst.decks()
    if aktion in ("liste", "zeigen", "alle"):
        return antwort({"ok": True, "aktion": "liste", "decks": decks})
    wunsch = str(args.get("deck") or args.get("thema") or "").strip().lower()
    passend = next((d for d in decks if d["id"] == wunsch), None) or next((d for d in decks if wunsch and wunsch in d["titel"].lower()), None)
    if aktion in ("loeschen", "löschen"):
        if passend is None:
            return antwort({"ok": False, "error": "Diesen Kartenstapel finde ich nicht."})
        dienst.delete(passend["id"])
        return antwort({"ok": True, "aktion": "geloescht", "titel": passend["titel"]})
    if aktion in ("lernen", "abfragen", "ueben", "üben") and passend is not None:
        return antwort({"ok": True, "aktion": "lernen", "deck": passend["id"], "titel": passend["titel"], "anzahl": passend["anzahl"], "faellig": passend["faellig"]})
    thema = str(args.get("thema") or args.get("text") or "").strip()
    if not thema:
        return antwort({"ok": False, "error": "Zu welchem Thema soll ich Karteikarten machen?"})
    karten = args.get("karten")
    if isinstance(karten, list) and karten:
        ergebnis = dienst.aus_karten(thema, karten)
    else:
        ergebnis = await dienst.generate(thema)
    if ergebnis.get("error"):
        return antwort({"ok": False, "error": ergebnis["error"]})
    return antwort({"ok": True, "aktion": "lernen", "deck": ergebnis["id"], "titel": ergebnis["titel"], "anzahl": ergebnis["anzahl"], "faellig": ergebnis["anzahl"]})


@werkzeug("haftnotiz")
def _haftnotiz(box: Any, args: dict, name: str = "") -> str:
    from app.services.notes_service import get_notes_service

    dienst = get_notes_service()
    aktion = str(args.get("aktion") or "neu").strip().lower()
    if aktion in ("liste", "zeigen", "alle"):
        return antwort({"ok": True, "notizen": [n for n in dienst.list() if not n.get("done")][:40]})
    if aktion in ("erledigt", "fertig", "abhaken", "loeschen", "löschen"):
        suche = str(args.get("id") or args.get("text") or "").strip().lower()
        treffer = next((n for n in dienst.list() if n["id"] == suche or (suche and suche in n["text"].lower())), None)
        if treffer is None:
            return antwort({"ok": False, "error": "Diese Notiz finde ich nicht."})
        if aktion.startswith("l"):
            dienst.delete(treffer["id"])
            return antwort({"ok": True, "geloescht": treffer["text"]})
        return antwort({"ok": True, "erledigt": dienst.update(treffer["id"], done=True)})
    text = str(args.get("text") or "").strip()
    if not text:
        return antwort({"ok": False, "error": "Was soll auf die Notiz?"})
    notiz = dienst.add(text[:600], str(args.get("farbe") or "gold"))
    if args.get("anheften"):
        notiz = dienst.update(notiz["id"], pinned=True)
    return antwort({"ok": True, "notiz": notiz, "hinweis": "Die Notiz klebt jetzt in Jons Haftnotizen."})


@werkzeug_async("text_vermenschlichen")
async def _text_vermenschlichen(box: Any, args: dict, name: str = "") -> str:
    from app.services.humanize_service import humanize, score

    text = str(args.get("text") or "").strip()
    if len(text) < 20:
        return antwort({"ok": False, "error": "Gib mir einen längeren Text."})
    try:
        staerke = max(1, min(3, int(args.get("staerke") or 2)))
    except (TypeError, ValueError):
        staerke = 2
    ergebnis = await humanize(text[:12000], str(args.get("stil") or "neutral"), staerke)
    if ergebnis.get("error"):
        return antwort({"ok": False, "error": ergebnis["error"]})
    neu = str(ergebnis.get("text") or ergebnis.get("result") or "")
    return antwort({"ok": True, "text": neu, "vorher": score(text), "nachher": score(neu) if neu else {}})


@werkzeug_async("rezept")
async def _rezept(box: Any, args: dict, name: str = "") -> str:
    from app.services.recipe_service import recipe, suggest

    gericht = str(args.get("gericht") or "").strip()
    zutaten = str(args.get("zutaten") or "").strip()
    if gericht:
        ergebnis = await recipe(gericht)
    elif zutaten:
        ergebnis = await suggest(zutaten)
    else:
        return antwort({"ok": False, "error": "Sag mir ein Gericht oder was du im Kühlschrank hast."})
    if ergebnis.get("error"):
        return antwort({"ok": False, "error": ergebnis["error"]})
    return antwort({"ok": True, **ergebnis})


@werkzeug_async("bild_zeigen")
async def _bild_zeigen(box: Any, args: dict, name: str = "") -> str:
    from app.services.bildquelle import finden

    suche = str(args.get("query") or args.get("suche") or "").strip()
    if not suche:
        return antwort({"ok": False, "error": "query fehlt: ein englischer Suchbegriff, zum Beispiel 'TON 618 quasar'."})
    try:
        anzahl = max(1, min(3, int(args.get("anzahl") or 1)))
    except (TypeError, ValueError):
        anzahl = 1
    bilder = await finden(suche, anzahl)
    if not bilder:
        return antwort({"ok": False, "error": f"Zu '{suche}' habe ich kein freies Bild gefunden. Versuch einen anderen englischen Begriff oder antworte ohne Bild."})
    return antwort({
        "ok": True,
        "titel": str(args.get("titel") or "").strip()[:80],
        "bilder": bilder,
        "hinweis": "Die Bilder erscheinen unter deiner Antwort. Beschreib sie nicht Pixel fuer Pixel, sondern nutze sie zum Erklaeren.",
    })


def karte_webbild(daten: dict) -> dict | None:
    if not daten.get("ok") or not daten.get("bilder"):
        return None
    felder = ("pfad", "titel", "quelle", "seite", "lizenz", "autor", "beschreibung")
    return {"kind": "webbild", "data": {"titel": daten.get("titel", ""), "bilder": [{k: b.get(k, "") for k in felder} for b in daten["bilder"]]}}


def karte_kopplung(daten: dict) -> dict | None:
    if not daten.get("ok"):
        return None
    return {"kind": "kopplung", "data": {schluessel: daten.get(schluessel) for schluessel in ("art", "code", "code_gruppiert", "nutzlast", "ablauf", "pc", "anleitung", "fertig", "uhr", "handy", "jon", "heimnetz")}}


def karte_karteikarten(daten: dict) -> dict | None:
    if not daten.get("ok") or daten.get("aktion") not in ("lernen", "liste"):
        return None
    return {"kind": "karteikarten", "data": json.loads(json.dumps(daten))}


@werkzeug_async("telegram_senden")
async def _telegram_senden(box: Any, args: dict, name: str = "") -> str:
    from app.services import telegram_plan
    from app.services.reminder_service import get_reminder_service

    aktion = str(args.get("aktion", "") or "").strip().lower()
    if aktion in ("liste", "zeigen", "geplant"):
        return antwort({"geplant": telegram_plan.geplante()})
    if aktion in ("loeschen", "löschen", "entfernen", "absagen"):
        kennung = str(args.get("id", "") or "").strip()
        suche = str(args.get("text", "") or "").strip().lower()
        treffer = [g for g in telegram_plan.geplante() if (kennung and g["id"] == kennung) or (suche and suche in g["text"].lower())]
        for g in treffer:
            get_reminder_service().delete(g["id"])
        return antwort({"ok": bool(treffer), "geloescht": len(treffer)} if treffer else {"error": "Keine passende geplante Telegram-Nachricht gefunden."})
    text = str(args.get("text", "") or args.get("nachricht", "") or "").strip()
    if not text:
        return antwort({"error": "text fehlt: Was soll in der Telegram-Nachricht stehen?"})
    zeit = str(args.get("zeit", "") or args.get("time", "") or "").strip()
    taeglich = str(args.get("taeglich", "")).strip().lower() in ("true", "1", "ja") or str(args.get("wiederholen", "")).strip().lower() in ("daily", "taeglich", "täglich", "true")
    if zeit or str(args.get("datum", "") or "").strip():
        return antwort(telegram_plan.planen(text, zeit, str(args.get("datum", "") or ""), taeglich))
    return antwort(await telegram_plan.senden(text))
