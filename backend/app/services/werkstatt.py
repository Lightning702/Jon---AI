from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

MAX_TEXT = 24000
MAX_FOLIEN = 40
MAX_AKTIONEN = 40
MAX_ZEILEN = 40
MAX_SPALTEN = 10

SPRACHEN = {
    ".py": "python", ".pyw": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript", ".cjs": "javascript",
    ".mjs": "javascript", ".jsx": "jsx", ".json": "json", ".html": "html", ".htm": "html", ".css": "css", ".scss": "css",
    ".md": "markdown", ".kt": "kotlin", ".kts": "kotlin", ".java": "java", ".cs": "csharp", ".cpp": "cpp", ".cc": "cpp",
    ".hpp": "cpp", ".c": "c", ".h": "c", ".rs": "rust", ".go": "go", ".sh": "bash", ".ps1": "powershell", ".bat": "batch",
    ".cmd": "batch", ".sql": "sql", ".yml": "yaml", ".yaml": "yaml", ".toml": "toml", ".ini": "ini", ".xml": "xml",
    ".svg": "xml", ".dart": "dart", ".swift": "swift", ".php": "php", ".rb": "ruby", ".lua": "lua", ".glsl": "glsl",
    ".vert": "glsl", ".frag": "glsl", ".txt": "text", ".log": "text", ".env": "ini", ".csv": "text",
}
DOKUMENTE = {"docx", "odt", "pdf", "md", "markdown", "txt", "text", "rtf"}
TABELLEN = {"xlsx", "ods", "csv"}
OFFICE = {".pptx", ".ppt", ".odp", ".docx", ".doc", ".odt", ".pdf", ".xlsx", ".ods"}

PPTX_TEXTE = {
    "text": "Text ersetzen",
    "ersetzen": "Suchen und ersetzen",
    "schrift": "Schrift ändern",
    "format": "Schrift ändern",
    "notizen": "Sprechernotizen schreiben",
    "bild": "Bild einsetzen",
    "bild_einfuegen": "Bild einsetzen",
    "bild_ersetzen": "Bild austauschen",
    "textfeld": "Textfeld hinzufügen",
    "element_loeschen": "Element entfernen",
    "element_verschieben": "Element verschieben",
    "verschieben": "Element verschieben",
    "groesse": "Größe ändern",
    "diagramm": "Diagramm aktualisieren",
    "hintergrund": "Hintergrund färben",
    "uebergang": "Übergang setzen",
    "folie_neu": "Neue Folie",
    "folie_loeschen": "Folie löschen",
    "folie_verschieben": "Folie verschieben",
    "folie_duplizieren": "Folie duplizieren",
}
DOCX_TEXTE = {
    "text": "Absatz umschreiben",
    "ersetzen": "Suchen und ersetzen",
    "einfuegen": "Text einfügen",
    "loeschen": "Absatz löschen",
    "format": "Formatieren",
    "bild": "Bild einsetzen",
    "tabelle": "Tabelle einfügen",
    "zelle": "Zelle ausfüllen",
    "duplizieren": "Absatz duplizieren",
}


def _kurz(wert: Any, laenge: int = 240) -> str:
    text = " ".join(str(wert if wert is not None else "").split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def _lang(wert: Any, laenge: int = MAX_TEXT) -> str:
    text = str(wert if wert is not None else "").replace("\r\n", "\n")
    return text if len(text) <= laenge else text[:laenge] + "\n…"


def sprache(pfad: str) -> str:
    return SPRACHEN.get(Path(str(pfad or "")).suffix.lower(), "text")


def _liste(wert: Any) -> list:
    if isinstance(wert, str):
        try:
            wert = json.loads(wert)
        except ValueError:
            return []
    if isinstance(wert, dict):
        wert = wert.get("aktionen") or wert.get("actions") or [wert]
    return wert if isinstance(wert, list) else []


def _farben(theme: str) -> dict:
    from app.services.pptx_service import DEFAULT_THEME, THEMES

    name = str(theme or "").strip().lower()
    werte = THEMES.get(name) or THEMES[DEFAULT_THEME]
    return {k: "#" + v for k, v in werte.items()}


def _punkte(wert: Any, anzahl: int = 8) -> list[str]:
    if not isinstance(wert, list):
        return []
    ergebnis = []
    for punkt in wert:
        if isinstance(punkt, dict):
            kopf = _kurz(punkt.get("titel") or punkt.get("title") or "", 80)
            text = _kurz(punkt.get("text") or punkt.get("beschreibung") or "", 200)
            punkt = f"{kopf}: {text}" if kopf and text else kopf or text
        text = str(punkt or "")
        unter = text[:1].isspace() or text.strip().startswith(("–", "- "))
        sauber = _kurz(text.strip().lstrip("–-•* ").strip(), 220)
        if sauber:
            ergebnis.append(("  " if unter else "") + sauber)
        if len(ergebnis) >= anzahl:
            break
    return ergebnis


def _tabelle(wert: Any) -> list[list[str]]:
    if not isinstance(wert, list):
        return []
    zeilen = []
    for zeile in wert[:8]:
        zellen = zeile if isinstance(zeile, list) else [zeile]
        zeilen.append([_kurz(z, 60) for z in zellen[:6]])
    return zeilen


def _bildhinweis(folie: dict) -> str:
    for feld in ("bild_suche", "image_search", "bild_prompt", "image_prompt"):
        if folie.get(feld):
            return _kurz(folie[feld], 80)
    for feld in ("image", "image_url", "bild_url"):
        if folie.get(feld):
            return Path(str(folie[feld])).name[:80] or "Bild"
    return ""


def _folie_kompakt(folie: dict) -> dict:
    items = []
    for item in (folie.get("items") or folie.get("columns") or [])[:6]:
        if isinstance(item, dict):
            items.append({
                "titel": _kurz(item.get("titel") or item.get("title") or "", 80),
                "text": _kurz(item.get("text") or item.get("beschreibung") or "", 200),
                "punkte": _punkte(item.get("bullets") or item.get("punkte") or [], 5),
            })
        elif str(item).strip():
            items.append({"titel": _kurz(item, 80), "text": "", "punkte": []})
    diagramm = folie.get("diagramm") or folie.get("chart")
    kompakt = {
        "layout": str(folie.get("layout") or "bullets"),
        "titel": _kurz(folie.get("title") or folie.get("titel") or "", 140),
        "untertitel": _kurz(folie.get("subtitle") or "", 200),
        "text": _kurz(folie.get("text") or "", 320),
        "punkte": _punkte(folie.get("bullets") or folie.get("absaetze") or []),
        "items": items,
        "tabelle": _tabelle(folie.get("tabelle") or folie.get("table")),
        "bild": _bildhinweis(folie),
        "notizen": _kurz(folie.get("notes") or "", 240),
        "quelle": _kurz(folie.get("quelle") or "", 120),
    }
    if isinstance(diagramm, dict):
        reihen = diagramm.get("reihen") or diagramm.get("series") or []
        werte = []
        if isinstance(reihen, list) and reihen and isinstance(reihen[0], dict):
            for wert in (reihen[0].get("werte") or reihen[0].get("values") or [])[:12]:
                try:
                    werte.append(float(wert))
                except (TypeError, ValueError):
                    werte.append(0.0)
        kompakt["diagramm"] = {
            "art": _kurz(diagramm.get("art") or diagramm.get("type") or "balken", 20),
            "kategorien": [_kurz(k, 24) for k in (diagramm.get("kategorien") or diagramm.get("categories") or [])[:12]],
            "werte": werte,
        }
    return {k: v for k, v in kompakt.items() if v not in ("", [], None)}


def _folien(args: dict) -> dict:
    from app.services.pptx_normalisieren import folien as normalisieren

    roh = args.get("slides")
    if isinstance(roh, str):
        try:
            roh = json.loads(roh)
        except ValueError:
            roh = []
    titel = str(args.get("title", "") or "")
    try:
        liste = normalisieren([f for f in copy.deepcopy(roh or []) if isinstance(f, (dict, str))], titel)
    except Exception:
        liste = [f for f in (roh or []) if isinstance(f, dict)]
    theme = str(args.get("theme", "") or "midnight")
    return {
        "art": "folien",
        "titel": _kurz(titel, 160),
        "untertitel": _kurz(args.get("subtitle", ""), 200),
        "theme": theme,
        "farben": _farben(theme),
        "folien": [_folie_kompakt(f) for f in liste[:MAX_FOLIEN] if isinstance(f, dict)],
        "anzahl": len(liste),
        "pfad": str(args.get("path", "") or ""),
    }


def _pptx_aktion(aktion: dict) -> dict:
    art = str(aktion.get("aktion") or aktion.get("art") or aktion.get("action") or "").strip().lower()
    eintrag: dict = {"art": art, "titel": PPTX_TEXTE.get(art, art or "Änderung")}
    for feld in ("folie", "element", "nach"):
        wert = aktion.get(feld)
        if isinstance(wert, (int, float)) and not isinstance(wert, bool):
            eintrag[feld] = int(wert)
        elif isinstance(wert, str) and wert.strip().isdigit():
            eintrag[feld] = int(wert.strip())
    if art == "ersetzen":
        eintrag["alt"] = _kurz(aktion.get("suchen", ""), 160)
        eintrag["neu"] = _kurz(aktion.get("ersetzen", ""), 160)
    elif art in ("text", "notizen", "textfeld"):
        eintrag["text"] = _kurz(aktion.get("text", ""), 600)
    elif art in ("bild", "bild_einfuegen", "bild_ersetzen"):
        eintrag["text"] = _bildhinweis(aktion)
        if aktion.get("position") and isinstance(aktion.get("position"), str):
            eintrag["position"] = _kurz(aktion["position"], 30)
    elif art == "hintergrund":
        eintrag["farbe"] = _kurz(aktion.get("farbe", ""), 20)
    elif art == "uebergang":
        eintrag["text"] = _kurz(aktion.get("art_uebergang") or aktion.get("uebergang") or aktion.get("typ") or "", 30)
    elif art in ("schrift", "format"):
        teile = []
        if aktion.get("groesse"):
            teile.append(f"{aktion['groesse']} pt")
        if aktion.get("fett"):
            teile.append("fett")
        if aktion.get("kursiv"):
            teile.append("kursiv")
        if aktion.get("farbe"):
            teile.append(str(aktion["farbe"]))
        eintrag["text"] = ", ".join(teile)
    elif art == "folie_neu":
        eintrag["folie_inhalt"] = _folie_kompakt(dict(aktion))
    elif art == "diagramm":
        eintrag["text"] = ", ".join(_kurz(k, 20) for k in (aktion.get("kategorien") or [])[:8])
    return eintrag


def _docx_aktion(aktion: dict) -> dict:
    art = str(aktion.get("aktion") or aktion.get("art") or aktion.get("action") or "").strip().lower()
    eintrag: dict = {"art": art, "titel": DOCX_TEXTE.get(art, art or "Änderung")}
    for feld in ("nr", "nach", "zeile", "spalte"):
        wert = aktion.get(feld)
        if isinstance(wert, (int, float)) and not isinstance(wert, bool):
            eintrag[feld] = int(wert)
    if aktion.get("stil"):
        eintrag["stil"] = _kurz(aktion["stil"], 20)
    if art == "ersetzen":
        eintrag["alt"] = _kurz(aktion.get("suchen", ""), 160)
        eintrag["neu"] = _kurz(aktion.get("ersetzen", ""), 160)
    elif art in ("text", "einfuegen", "zelle"):
        eintrag["text"] = _lang(aktion.get("text", ""), 1500)
    elif art == "bild":
        eintrag["text"] = _bildhinweis(aktion) or _kurz(aktion.get("unterschrift", ""), 80)
    elif art == "tabelle":
        eintrag["tabelle"] = _tabelle(aktion.get("zeilen") or aktion.get("rows"))
    return eintrag


def _bloecke(text: Any, titel: str) -> list[dict]:
    from app.services.dokument_service import _bloecke as zerlegen

    try:
        roh = zerlegen(_lang(text), titel)
    except Exception:
        roh = [("absatz", z) for z in str(text or "").split("\n")]
    bloecke = []
    for typ, inhalt in roh[:400]:
        if typ == "leer" and (not bloecke or bloecke[-1]["typ"] == "leer"):
            continue
        bloecke.append({"typ": typ, "text": _lang(inhalt, 2000)})
    return bloecke


def _zeilen(inhalt: Any) -> list[list[str]]:
    from app.services.dokument_service import _zeilen_aus

    try:
        zeilen = _zeilen_aus(inhalt)
    except Exception:
        zeilen = []
    return [[_kurz(z, 60) for z in zeile[:MAX_SPALTEN]] for zeile in zeilen[:MAX_ZEILEN]]


def _datei_erstellen(args: dict) -> dict:
    art = str(args.get("art", "txt") or "txt").lower().lstrip(".")
    titel = str(args.get("titel", "") or "")
    name = str(args.get("dateiname", "") or "") or (titel or "Dokument") + "." + ("md" if art == "markdown" else art)
    if art in TABELLEN:
        return {"art": "tabelle", "titel": _kurz(titel, 160), "format": art, "pfad": name, "zeilen": _zeilen(args.get("inhalt", ""))}
    inhalt = args.get("inhalt", "")
    if isinstance(inhalt, (list, dict)):
        inhalt = json.dumps(inhalt, ensure_ascii=False, indent=2)
    if art in DOKUMENTE:
        return {"art": "dokument", "titel": _kurz(titel, 160), "format": art, "pfad": name, "bloecke": _bloecke(inhalt, titel)}
    return {"art": "code", "pfad": name, "sprache": sprache(name), "inhalt": _lang(inhalt)}


def vorschau(name: str, args: dict | None) -> dict | None:
    args = args if isinstance(args, dict) else {}
    try:
        if name == "create_pptx":
            return _folien(args)
        if name == "edit_pptx":
            aktionen = [_pptx_aktion(a) for a in _liste(args.get("aktionen") or args.get("actions"))[:MAX_AKTIONEN] if isinstance(a, dict)]
            return {"art": "folien_aenderung", "pfad": str(args.get("path") or args.get("pfad") or ""), "aktionen": aktionen, "farben": _farben(str(args.get("theme") or ""))}
        if name == "edit_docx":
            aktionen = [_docx_aktion(a) for a in _liste(args.get("aktionen") or args.get("actions"))[:MAX_AKTIONEN] if isinstance(a, dict)]
            return {"art": "dokument_aenderung", "pfad": str(args.get("path") or args.get("pfad") or ""), "aktionen": aktionen}
        if name == "datei_erstellen":
            return _datei_erstellen(args)
        if name in ("write_file", "append_file", "create"):
            pfad = str(args.get("path", "") or "")
            return {"art": "code", "pfad": pfad, "sprache": sprache(pfad), "inhalt": _lang(args.get("content", "")), "anhaengen": name == "append_file"}
        if name in ("edit_file", "edit"):
            pfad = str(args.get("path", "") or "")
            return {"art": "diff", "pfad": pfad, "sprache": sprache(pfad), "alt": _lang(args.get("old", ""), 12000), "neu": _lang(args.get("new", ""), 12000)}
        if name in ("run_powershell", "run_cmd", "command", "verify"):
            befehl = str(args.get("command", "") or "")
            if not befehl.strip():
                return None
            shell = {"run_powershell": "PowerShell", "run_cmd": "cmd"}.get(name, "Shell")
            return {"art": "terminal", "befehl": _lang(befehl, 4000), "shell": shell, "pruefung": name == "verify"}
    except Exception:
        return None
    return None


def _daten(ergebnis: Any) -> dict:
    if isinstance(ergebnis, dict):
        return ergebnis
    try:
        daten = json.loads(ergebnis or "{}")
    except (TypeError, ValueError):
        return {"text": str(ergebnis or "")}
    return daten if isinstance(daten, dict) else {"text": str(daten)}


def datei_von(daten: dict) -> str:
    for schluessel in ("path", "pfad"):
        if isinstance(daten.get(schluessel), str) and daten[schluessel]:
            return daten[schluessel]
    datei = daten.get("datei")
    if isinstance(datei, dict) and isinstance(datei.get("path"), str):
        return datei["path"]
    return ""


def ergebnis(name: str, roh: Any) -> dict | None:
    if name not in WERKSTATT_WERKZEUGE:
        return None
    daten = _daten(roh)
    if daten.get("error"):
        return {"ok": False, "fehler": _kurz(daten["error"], 400)}
    if name in ("run_powershell", "run_cmd", "command", "verify"):
        ausgabe = str(daten.get("stdout") or daten.get("output") or "")
        code = daten.get("exit_code")
        ok = bool(daten.get("ok")) if "ok" in daten else code in (0, None)
        return {"ok": ok, "exit_code": code, "ausgabe": ausgabe[-4000:], "fehler": str(daten.get("stderr") or "")[-1500:]}
    pfad = datei_von(daten)
    antwort: dict = {"ok": True}
    if pfad:
        antwort["pfad"] = pfad
        antwort["office"] = Path(pfad).suffix.lower() in OFFICE
    if isinstance(daten.get("slides"), int):
        antwort["folien"] = daten["slides"]
    if isinstance(daten.get("fehler"), list) and daten["fehler"]:
        antwort["hinweise"] = [_kurz(f, 200) for f in daten["fehler"][:6]]
    if name in ("edit", "create") and daten.get("diff"):
        antwort["diff"] = _lang(daten["diff"], 16000)
    return antwort


WERKSTATT_WERKZEUGE = {
    "create_pptx", "edit_pptx", "edit_docx", "datei_erstellen", "write_file", "append_file", "edit_file",
    "run_powershell", "run_cmd", "create", "edit", "command", "verify",
}
