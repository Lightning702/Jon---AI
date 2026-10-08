from __future__ import annotations

import re

LAYOUT_NAMEN = {
    "content": "bullets", "inhalt": "bullets", "standard": "bullets", "liste": "bullets", "list": "bullets",
    "bullet": "bullets", "punkte": "bullets", "text_bullets": "bullets", "title_content": "bullets",
    "two_column": "two_columns", "twocolumn": "two_columns", "zwei_spalten": "two_columns", "spalten": "two_columns",
    "split": "two_columns", "column": "two_columns",
    "bild": "image", "foto": "image", "picture": "image", "photo": "image", "image_text": "image",
    "zitat": "quote", "abschluss": "closing", "ende": "closing", "schluss": "closing", "end": "closing", "danke": "closing",
    "titel": "title", "cover": "title", "titelfolie": "title",
    "process": "timeline", "prozess": "timeline", "ablauf": "timeline", "schema": "timeline", "steps": "timeline",
    "schritte": "timeline", "flow": "timeline", "diagram_flow": "timeline", "zeitleiste": "timeline",
    "karten": "cards", "grid": "cards", "kacheln": "cards",
    "statistik": "stat", "zahlen": "stat",
    "glossar": "table", "glossary": "table",
    "sources": "bullets", "quellen": "bullets", "references": "bullets",
    "title_and_content": "bullets", "content_slide": "bullets", "title_body": "bullets", "body": "bullets",
    "two_content": "two_columns", "comparison": "two_columns", "two_col": "two_columns",
    "section_header": "closing", "section": "closing", "abschnitt": "closing", "kapitel": "closing", "trenner": "closing",
    "picture_with_caption": "image", "bild_mit_text": "image", "image_left": "image", "image_right": "image",
    "title_slide": "title", "deckblatt": "title", "titelseite": "title", "intro": "title",
    "title_only": "title_only", "blank": "title_only", "leer": "title_only", "custom": "title_only",
}
BEKANNT = {"title", "bullets", "cards", "stat", "stats", "two_columns", "columns", "image", "quote", "timeline", "closing",
           "text", "prosa", "agenda", "chart", "diagramm", "table", "tabelle", "compare", "vergleich"}
LISTEN = ("bullets", "punkte", "stichpunkte", "points", "inhalt", "content", "liste", "zeilen_text")
BILD_FELDER = ("image", "image_url", "bild_url", "bild_suche", "image_search", "bild_prompt", "image_prompt")
MAX_PUNKTE = 7
MAX_ZEICHEN = 700
LISTENFOLIEN = ("quellen", "quelle", "sources", "literatur", "references", "glossar", "glossary", "bildnachweis", "abgleich", "checkliste", "inhalt", "agenda")
QUELLZEILE = ("quelle:", "quellen:", "source:", "sources:")


def _layout(eintrag: dict) -> str:
    roh = str(eintrag.get("layout") or eintrag.get("typ") or eintrag.get("type") or "bullets").strip().lower()
    roh = re.sub(r"[\s\-]+", "_", roh)
    if roh in BEKANNT:
        return roh
    return LAYOUT_NAMEN.get(roh, "bullets")


BILDZEICHEN = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2B06\u2B07\u2B05\uFE0F\u200D]")


def ohne_emoji(text: str) -> str:
    return re.sub(r"\s{2,}", " ", BILDZEICHEN.sub("", str(text))).strip()


def _tabelle(eintrag: dict) -> None:
    if eintrag.get("tabelle") or eintrag.get("table"):
        return
    kopf = next((eintrag.pop(f) for f in ("headers", "header", "kopfzeile", "spalten", "column_headers") if isinstance(eintrag.get(f), list)), None)
    zeilen = next((eintrag.pop(f) for f in ("rows", "zeilen", "data", "daten", "cells") if isinstance(eintrag.get(f), list)), None)
    if not zeilen:
        return
    zeilen = [z if isinstance(z, list) else [z] for z in zeilen]
    if kopf:
        breite = len(kopf)
        flach = [w for z in zeilen for w in z]
        if any(len(z) != breite for z in zeilen) and breite and len(flach) % breite == 0:
            zeilen = [flach[i:i + breite] for i in range(0, len(flach), breite)]
        zeilen = [kopf] + zeilen
    eintrag["tabelle"] = [[ohne_emoji(str(w)) for w in z] for z in zeilen]
    eintrag["layout"] = "table"


def _texte(wert) -> list[str]:
    if isinstance(wert, str):
        return [ohne_emoji(z) for z in wert.split("\n") if ohne_emoji(z)]
    if isinstance(wert, list):
        ergebnis = []
        for teil in wert:
            if isinstance(teil, dict):
                kopf = str(teil.get("titel") or teil.get("title") or "").strip()
                text = str(teil.get("text") or teil.get("beschreibung") or "").strip()
                ergebnis.append(f"{kopf}: {text}" if kopf and text else kopf or text)
            elif isinstance(teil, list):
                ergebnis.append(" | ".join(str(w) for w in teil))
            elif str(teil).strip():
                ergebnis.append(ohne_emoji(str(teil)))
        return [ohne_emoji(e) for e in ergebnis if ohne_emoji(e)]
    return []


def _bild(eintrag: dict) -> None:
    for feld in ("background", "hintergrund", "hintergrundbild", "background_image", "bild", "photo", "foto"):
        wert = eintrag.pop(feld, None)
        if not wert:
            continue
        if isinstance(wert, dict):
            for schluessel in BILD_FELDER:
                if wert.get(schluessel) and not eintrag.get(schluessel):
                    eintrag[schluessel] = wert[schluessel]
            if wert.get("url") and not eintrag.get("image_url"):
                eintrag["image_url"] = wert["url"]
            if wert.get("suche") and not eintrag.get("bild_suche"):
                eintrag["bild_suche"] = wert["suche"]
        elif isinstance(wert, str) and not eintrag.get("image"):
            eintrag["image"] = wert


def _spalten(eintrag: dict) -> None:
    if eintrag.get("items") or eintrag.get("columns"):
        return
    spalten = []
    for links, deutsch in (("left", "links"), ("right", "rechts")):
        kopf = eintrag.pop(f"{links}_title", None) or eintrag.pop(f"{deutsch}_titel", None) or ""
        punkte = eintrag.pop(f"{links}_bullets", None) or eintrag.pop(f"{deutsch}_punkte", None) or eintrag.pop(links, None) or eintrag.pop(deutsch, None) or []
        text = eintrag.pop(f"{links}_text", None) or eintrag.pop(f"{deutsch}_text", None) or ""
        if isinstance(punkte, dict):
            kopf = kopf or punkte.get("title") or punkte.get("titel") or ""
            text = text or punkte.get("text") or ""
            punkte = punkte.get("bullets") or punkte.get("punkte") or []
        if kopf or punkte or text:
            roh = [ohne_emoji(p) if not str(p)[:1].isspace() else "  " + ohne_emoji(p) for p in punkte] if isinstance(punkte, list) else _texte(punkte)
            spalten.append({"titel": str(kopf), "bullets": [p for p in roh if str(p).strip()], "text": str(text)})
    if spalten:
        eintrag["items"] = spalten


def _ablauf(eintrag: dict) -> None:
    if eintrag.get("items"):
        return
    for feld in ("steps", "schritte", "stages", "phasen", "ablauf"):
        werte = eintrag.pop(feld, None)
        if werte:
            eintrag["items"] = [{"titel": t.split(":", 1)[0], "text": t.split(":", 1)[1].strip() if ":" in t else ""} for t in _texte(werte)]
            return


UNTERPUNKT = ("–", "-", "•", "*", "·", "▪", "◦")


def _ist_unterpunkt(zeile: str) -> bool:
    return zeile[:1].isspace() or zeile.strip().startswith(UNTERPUNKT)


def _ohne_zeichen(zeile: str) -> str:
    text = zeile.strip()
    while text[:1] in UNTERPUNKT and text:
        text = text[1:].strip()
    return text


def _gruppen(punkte: list) -> tuple[list[tuple[str, list[str]]], list[str]]:
    gruppen: list[tuple[str, list[str]]] = []
    lose: list[str] = []
    for roh in punkte:
        zeile = str(roh)
        if not zeile.strip():
            continue
        if _ist_unterpunkt(zeile) and gruppen:
            gruppen[-1][1].append(_ohne_zeichen(zeile))
        elif _ist_unterpunkt(zeile):
            lose.append(_ohne_zeichen(zeile))
        else:
            gruppen.append((zeile.strip().rstrip(":").strip(), []))
    mit = [g for g in gruppen if g[1]]
    if len(mit) >= 2:
        lose = lose + [kopf for kopf, unter in gruppen if not unter]
        return mit, lose
    if len(mit) < 2:
        flach = []
        for kopf, unter in gruppen:
            flach.append(f"{kopf}:" if unter else kopf)
            flach.extend(f"– {u}" for u in unter)
        return [], lose + flach
    return gruppen, lose


def _objekte(eintrag: dict) -> list[str]:
    texte: list[str] = []
    for feld in ("objects", "objekte", "elements", "elemente", "shapes", "formen"):
        objekte = eintrag.pop(feld, None)
        if not isinstance(objekte, list):
            continue
        for objekt in objekte:
            if not isinstance(objekt, dict):
                continue
            art = str(objekt.get("type") or objekt.get("typ") or objekt.get("art") or "").lower()
            hat_bild = any(objekt.get(f) for f in BILD_FELDER) or art in {"image", "picture", "bild", "foto", "photo"}
            if hat_bild:
                for schluessel in BILD_FELDER:
                    if objekt.get(schluessel) and not eintrag.get(schluessel):
                        eintrag[schluessel] = objekt[schluessel]
                quelle = objekt.get("path") or objekt.get("pfad") or objekt.get("src") or objekt.get("bild_pfad")
                if quelle and not eintrag.get("image"):
                    eintrag["image"] = quelle
                if objekt.get("url") and not eintrag.get("image_url"):
                    eintrag["image_url"] = objekt["url"]
                continue
            if art in {"table", "tabelle"}:
                zeilen = objekt.get("rows") or objekt.get("zeilen") or objekt.get("data")
                if zeilen and not eintrag.get("tabelle"):
                    eintrag["tabelle"] = zeilen
                continue
            if art in {"chart", "diagramm"}:
                if not eintrag.get("diagramm"):
                    eintrag["diagramm"] = {k: v for k, v in objekt.items() if k not in {"type", "typ", "art"}}
                continue
            text = objekt.get("text") or objekt.get("inhalt") or objekt.get("content")
            if isinstance(text, str):
                zeilen = [z.strip() for z in text.split("\n") if z.strip()]
                if zeilen:
                    texte.append(" ".join(zeilen) if len(zeilen) <= 3 and all(len(z) < 40 for z in zeilen) else zeilen[0])
                    if not (len(zeilen) <= 3 and all(len(z) < 40 for z in zeilen)):
                        texte.extend(zeilen[1:])
            else:
                texte.extend(_texte(text))
    return texte


def _inhalt_leer(eintrag: dict, layout: str) -> bool:
    if layout in ("title", "closing", "quote"):
        return False
    felder = ("bullets", "items", "text", "absaetze", "paragraphs", "tabelle", "table", "diagramm", "chart", "image", "stat", "stats", "left", "right")
    return not any(eintrag.get(f) for f in felder)


def _rest_als_punkte(eintrag: dict) -> list[str]:
    ausgelassen = {"layout", "title", "titel", "subtitle", "notes", "uebergang", "tempo", "animation", *BILD_FELDER}
    punkte = []
    for schluessel, wert in eintrag.items():
        if schluessel in ausgelassen:
            continue
        punkte.extend(_texte(wert))
    return punkte


def _spaltenfolien(eintrag: dict, gruppen: list[tuple[str, list[str]]], lose: list[str]) -> list[dict]:
    paare = [gruppen[i:i + 2] for i in range(0, len(gruppen), 2)]
    folien = []
    for nummer, paar in enumerate(paare):
        teil = {k: v for k, v in eintrag.items() if k not in {"bullets", "items", "layout"}}
        if nummer:
            teil.pop("text", None)
            teil.pop("notes", None)
            for feld in BILD_FELDER:
                teil.pop(feld, None)
        elif lose:
            teil["text"] = " ".join([str(eintrag.get("text") or "")] + lose).strip()
        teil["layout"] = "two_columns"
        teil["items"] = [{"titel": kopf, "bullets": unter[:6]} for kopf, unter in paar]
        if len(paare) > 1:
            teil["title"] = f"{eintrag.get('title', '')} ({nummer + 1}/{len(paare)})".strip()
        folien.append(teil)
    return folien


def _quellzeilen(eintrag: dict) -> None:
    punkte = [str(p) for p in eintrag.get("bullets") or []]
    quellen = [p for p in punkte if p.strip().lower().startswith(QUELLZEILE)]
    if not quellen or len(quellen) == len(punkte):
        return
    eintrag["bullets"] = [p for p in punkte if p not in quellen]
    zusatz = "; ".join(q.split(":", 1)[1].strip() for q in quellen)
    vorhanden = str(eintrag.get("quelle") or "").strip()
    eintrag["quelle"] = f"{vorhanden}; {zusatz}" if vorhanden else zusatz


def _gleichmaessig(punkte: list[str]) -> list[list[str]]:
    zeichen = sum(len(p) for p in punkte)
    anzahl = max(-(-len(punkte) // MAX_PUNKTE), -(-zeichen // MAX_ZEICHEN), 1)
    groesse = -(-len(punkte) // anzahl)
    gruppen = [punkte[i:i + groesse] for i in range(0, len(punkte), groesse)]
    while len(gruppen) > 1 and len(gruppen[-1]) == 1 and len(gruppen[-2]) < MAX_PUNKTE + 1:
        gruppen[-2].extend(gruppen.pop())
    return gruppen


NUMMERIERT = re.compile(r"\(\s*\d+\s*/\s*\d+\s*\)\s*$")


def _teilen(eintrag: dict) -> list[dict]:
    _quellzeilen(eintrag)
    if NUMMERIERT.search(str(eintrag.get("title", ""))):
        gruppen, lose = _gruppen(eintrag.get("bullets") or [])
        if not gruppen:
            eintrag["bullets"] = [p if p.startswith("– ") else _ohne_zeichen(p) for p in lose]
            return [eintrag]
    liste = any(w in str(eintrag.get("title", "")).lower() for w in LISTENFOLIEN)
    gruppen, lose = _gruppen(eintrag.get("bullets") or [])
    if gruppen and not liste:
        return _spaltenfolien(eintrag, gruppen, lose)
    if gruppen:
        flach = list(lose)
        for kopf, unter in gruppen:
            flach.append(f"{kopf}:" if unter else kopf)
            flach.extend(f"– {u}" for u in unter)
        lose = flach
    eintrag["bullets"] = [p if p.startswith("– ") else _ohne_zeichen(p) for p in lose]
    punkte = [str(p) for p in eintrag.get("bullets") or []]
    if len(punkte) <= MAX_PUNKTE and sum(len(p) for p in punkte) <= MAX_ZEICHEN:
        return [eintrag]
    gruppen = _gleichmaessig(punkte)
    folien = []
    for nummer, gruppe in enumerate(gruppen):
        teil = dict(eintrag) if nummer == 0 else {k: v for k, v in eintrag.items() if k in ("layout", "title", "uebergang", "tempo", "quelle", "footer")}
        teil["bullets"] = gruppe
        if nummer:
            teil["title"] = f"{eintrag.get('title', '')} ({nummer + 1}/{len(gruppen)})".strip()
            teil.pop("text", None)
        elif len(gruppen) > 1:
            teil["title"] = f"{eintrag.get('title', '')} (1/{len(gruppen)})".strip()
        folien.append(teil)
    return folien


def folie(eintrag) -> dict:
    if not isinstance(eintrag, dict):
        return {"layout": "bullets", "title": str(eintrag)}
    neu = dict(eintrag)
    if not neu.get("title") and neu.get("titel"):
        neu["title"] = neu.pop("titel")
    if not neu.get("subtitle") and neu.get("untertitel"):
        neu["subtitle"] = neu.pop("untertitel")
    if not neu.get("notes"):
        for feld in ("notizen", "speaker_notes", "sprechernotizen"):
            if neu.get(feld):
                neu["notes"] = neu.pop(feld)
                break
    _bild(neu)
    objekt_texte = _objekte(neu)
    layout = _layout(neu)
    if layout in ("table", "tabelle") or any(isinstance(neu.get(f), list) for f in ("headers", "rows")):
        _tabelle(neu)
        if neu.get("tabelle"):
            layout = "table"
    for feld in ("title", "subtitle", "text"):
        if isinstance(neu.get(feld), str):
            neu[feld] = ohne_emoji(neu[feld])
    if layout == "title_only":
        layout = "bullets"
    neu["layout"] = layout
    if objekt_texte and layout in ("title", "closing") and not str(neu.get("title") or "").strip():
        neu["title"] = objekt_texte.pop(0)
    if objekt_texte:
        if layout in ("title", "closing") and not neu.get("subtitle"):
            neu["subtitle"] = " · ".join(objekt_texte[:3]) if len(objekt_texte) > 1 else objekt_texte[0]
        elif layout not in ("title", "closing"):
            neu["bullets"] = _texte(neu.get("bullets") or []) + objekt_texte
    if not neu.get("bullets"):
        for feld in LISTEN[1:]:
            if isinstance(neu.get(feld), list):
                neu["bullets"] = _texte(neu.pop(feld))
                break
    if layout in ("two_columns", "columns", "compare", "vergleich"):
        _spalten(neu)
    if layout == "timeline":
        _ablauf(neu)
    if layout == "closing" and (neu.get("bullets") or neu.get("items")):
        neu["layout"] = layout = "bullets"
    if _inhalt_leer(neu, layout):
        punkte = _rest_als_punkte(neu)
        if punkte:
            neu["bullets"] = punkte
            if layout not in ("bullets", "image"):
                neu["layout"] = "bullets"
    if isinstance(neu.get("bullets"), list):
        neu["bullets"] = [ohne_emoji(b) if not str(b).startswith("  ") else "  " + ohne_emoji(b) for b in neu["bullets"] if ohne_emoji(b)]
    return neu


def _wie_titel(roh, normal: dict) -> bool:
    if not isinstance(roh, dict):
        return False
    art = str(roh.get("layout") or roh.get("type") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if art in {"title_only", "blank", "leer", "custom", "title_slide", "titel", "deckblatt", "titelseite", "cover", "intro"}:
        return True
    punkte = normal.get("bullets") or []
    return not art and normal["layout"] == "bullets" and len(punkte) <= 2 and sum(len(str(p)) for p in punkte) < 160 and not normal.get("items")


def _spalten_aufraeumen(eintrag: dict) -> list[dict]:
    spalten = eintrag.get("items") or eintrag.get("columns") or []
    if not isinstance(spalten, list):
        return [eintrag]
    zeilen: list[str] = []
    for spalte in spalten:
        if not isinstance(spalte, dict):
            continue
        saubere = []
        kopf_offen = False
        for punkt in [str(p) for p in spalte.get("bullets") or []]:
            roh = punkt.strip()
            unter = punkt[:1].isspace()
            zeichen = roh[:1] in ("•", "▪", "*", "·", "◦")
            while roh[:1] in ("•", "▪", "*", "·", "◦") and roh:
                roh = roh[1:].strip()
            if zeichen and kopf_offen:
                unter = True
            if roh.startswith(("–", "- ")):
                unter = True
                roh = roh.lstrip("–- ").strip()
            if roh:
                saubere.append(("– " + roh) if unter else roh)
                zeilen.append(("  " + roh) if unter else roh)
                if not unter:
                    kopf_offen = roh.endswith(":")
        spalte["bullets"] = saubere
    gruppen, lose = _gruppen(zeilen)
    if len(gruppen) >= 3 or (gruppen and len(zeilen) > 14):
        basis = {k: v for k, v in eintrag.items() if k not in {"items", "columns"}}
        return _spaltenfolien(basis, gruppen, lose)
    return [eintrag]


def folien(liste, titel: str = "") -> list[dict]:
    ergebnis: list[dict] = []
    for nummer, eintrag in enumerate(liste or []):
        normal = folie(eintrag)
        if nummer == 0 and normal["layout"] != "title" and _wie_titel(eintrag, normal):
            unter = [_ohne_zeichen(str(u)) for u in normal.pop("bullets", None) or []]
            normal["layout"] = "title"
            if not str(normal.get("title") or "").strip():
                normal["title"] = titel or (unter.pop(0) if unter else "")
                if titel and unter and unter[0].replace(" ", "").lower() in titel.replace(" ", "").replace("–", "").replace("-", "").lower():
                    unter.pop(0)
            if unter and not normal.get("subtitle"):
                normal["subtitle"] = " · ".join(unter)
        if nummer == 0 and normal["layout"] == "title" and not str(normal.get("title") or "").strip() and titel:
            normal["title"] = titel
        if normal["layout"] == "bullets":
            ergebnis.extend(_teilen(normal))
        elif normal["layout"] in ("two_columns", "columns"):
            ergebnis.extend(_spalten_aufraeumen(normal))
        else:
            ergebnis.append(normal)
    return ergebnis
