from __future__ import annotations

import re

WUNSCH = re.compile(r"ohne\s+(?:jeden\s+|jegliche\s+|alle\s+|irgendwelche\s+)?kommentar|keine\s+kommentare|kommentarlos|no\s+comments|without\s+comments", re.IGNORECASE)
REGEX_DAVOR = set("(,=:[!&|?{};+-*%<>~^")
REGEX_WOERTER = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw", "yield", "await", "instanceof"}
ENDUNGEN_JS = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx")
ENDUNGEN_CSS = (".css", ".scss", ".less")
ENDUNGEN_HTML = (".html", ".htm", ".svg", ".vue")
SKRIPT = re.compile(r"(<script\b[^>]*>)(.*?)(</script\s*>)", re.IGNORECASE | re.DOTALL)
STIL = re.compile(r"(<style\b[^>]*>)(.*?)(</style\s*>)", re.IGNORECASE | re.DOTALL)
HTML_KOMMENTAR = re.compile(r"<!--(?!\[if|<!\[endif)(?:(?!-->).)*-->", re.DOTALL)


def gewuenscht(*texte: str) -> bool:
    return any(WUNSCH.search(str(t or "")) for t in texte)


def _zeilenrest(aus: list[str]) -> bool:
    for teil in reversed(aus):
        stelle = teil.rfind("\n")
        rest = teil if stelle < 0 else teil[stelle + 1:]
        if rest.strip():
            return False
        if stelle >= 0:
            return True
    return True


def _zeile_leeren(aus: list[str]) -> None:
    while aus:
        teil = aus[-1]
        stelle = teil.rfind("\n")
        if stelle >= 0:
            aus[-1] = teil[: stelle + 1]
            return
        aus.pop()


def _entfernt(text: str, start: int, ende: int, aus: list[str]) -> int:
    ganze_zeile = _zeilenrest(aus)
    nach = ende
    while nach < len(text) and text[nach] in " \t":
        nach += 1
    if ganze_zeile and (nach >= len(text) or text[nach] in "\r\n"):
        _zeile_leeren(aus)
        if nach < len(text) and text[nach] == "\r":
            nach += 1
        if nach < len(text) and text[nach] == "\n":
            nach += 1
        return nach
    if nach >= len(text) or text[nach] in "\r\n":
        while aus and aus[-1] and aus[-1][-1] in " \t":
            aus[-1] = aus[-1][:-1]
            if not aus[-1]:
                aus.pop()
        return nach
    if "\n" in text[start:ende]:
        aus.append("\n")
    elif aus and not aus[-1][-1:].isspace() and ende < len(text) and not text[ende].isspace():
        aus.append(" ")
    return ende


def _string_ende(text: str, start: int) -> int:
    zeichen = text[start]
    stelle = start + 1
    while stelle < len(text):
        if text[stelle] == "\\":
            stelle += 2
            continue
        if text[stelle] == zeichen or text[stelle] == "\n":
            return stelle + 1
        stelle += 1
    return len(text)


def _vorlage_ende(text: str, start: int) -> int:
    stelle = start + 1
    while stelle < len(text):
        zeichen = text[stelle]
        if zeichen == "\\":
            stelle += 2
            continue
        if zeichen == "`":
            return stelle + 1
        if zeichen == "$" and text[stelle + 1:stelle + 2] == "{":
            tiefe = 1
            stelle += 2
            while stelle < len(text) and tiefe:
                innen = text[stelle]
                if innen in "\"'":
                    stelle = _string_ende(text, stelle)
                    continue
                if innen == "`":
                    stelle = _vorlage_ende(text, stelle)
                    continue
                if innen == "{":
                    tiefe += 1
                elif innen == "}":
                    tiefe -= 1
                stelle += 1
            continue
        stelle += 1
    return len(text)


def _regex_ende(text: str, start: int) -> int:
    stelle = start + 1
    klasse = False
    while stelle < len(text):
        zeichen = text[stelle]
        if zeichen == "\n":
            return -1
        if zeichen == "\\":
            stelle += 2
            continue
        if zeichen == "[":
            klasse = True
        elif zeichen == "]":
            klasse = False
        elif zeichen == "/" and not klasse:
            stelle += 1
            while stelle < len(text) and text[stelle].isalpha():
                stelle += 1
            return stelle
        stelle += 1
    return -1


def js(text: str) -> str:
    aus: list[str] = []
    stelle = 0
    letztes = ""
    wort = ""
    while stelle < len(text):
        zeichen = text[stelle]
        if zeichen in "\"'":
            ende = _string_ende(text, stelle)
            aus.append(text[stelle:ende])
            stelle, letztes, wort = ende, zeichen, ""
            continue
        if zeichen == "`":
            ende = _vorlage_ende(text, stelle)
            aus.append(text[stelle:ende])
            stelle, letztes, wort = ende, zeichen, ""
            continue
        if zeichen == "/" and stelle + 1 < len(text):
            folgend = text[stelle + 1]
            if folgend == "/":
                ende = text.find("\n", stelle)
                stelle = _entfernt(text, stelle, len(text) if ende < 0 else ende, aus)
                continue
            if folgend == "*":
                ende = text.find("*/", stelle + 2)
                stelle = _entfernt(text, stelle, len(text) if ende < 0 else ende + 2, aus)
                continue
            if not letztes or letztes in REGEX_DAVOR or wort in REGEX_WOERTER:
                ende = _regex_ende(text, stelle)
                if ende > 0:
                    aus.append(text[stelle:ende])
                    stelle, letztes, wort = ende, "/", ""
                    continue
        aus.append(zeichen)
        if zeichen.isalnum() or zeichen in "_$":
            wort = wort + zeichen if letztes and (letztes.isalnum() or letztes in "_$") else zeichen
            letztes = zeichen
        elif not zeichen.isspace():
            letztes, wort = zeichen, ""
        stelle += 1
    return "".join(aus)


def css(text: str) -> str:
    aus: list[str] = []
    stelle = 0
    while stelle < len(text):
        zeichen = text[stelle]
        if zeichen in "\"'":
            ende = _string_ende(text, stelle)
            aus.append(text[stelle:ende])
            stelle = ende
            continue
        if zeichen == "/" and text[stelle + 1:stelle + 2] == "*":
            ende = text.find("*/", stelle + 2)
            stelle = _entfernt(text, stelle, len(text) if ende < 0 else ende + 2, aus)
            continue
        aus.append(zeichen)
        stelle += 1
    return "".join(aus)


def html(text: str) -> str:
    teile: list[str] = []
    stelle = 0
    for treffer in sorted(list(SKRIPT.finditer(text)) + list(STIL.finditer(text)), key=lambda t: t.start()):
        if treffer.start() < stelle:
            continue
        teile.append(_html_rein(text[stelle:treffer.start()]))
        kopf, innen, fuss = treffer.group(1), treffer.group(2), treffer.group(3)
        if kopf.lower().startswith("<style"):
            innen = css(innen)
        elif not re.search(r'type\s*=\s*["\']?(?:application/(?:ld\+)?json|text/template|importmap)', kopf, re.IGNORECASE):
            innen = js(innen)
        teile.append(kopf + innen + fuss)
        stelle = treffer.end()
    teile.append(_html_rein(text[stelle:]))
    return "".join(teile)


def _html_rein(text: str) -> str:
    aus: list[str] = []
    stelle = 0
    for treffer in HTML_KOMMENTAR.finditer(text):
        aus.append(text[stelle:treffer.start()])
        stelle = _entfernt(text, treffer.start(), treffer.end(), aus)
    aus.append(text[stelle:])
    return "".join(aus)


def entfernen(pfad: str, inhalt: str) -> str:
    name = str(pfad or "").lower()
    if name.endswith(ENDUNGEN_HTML):
        return html(inhalt)
    if name.endswith(ENDUNGEN_CSS):
        return css(inhalt)
    if name.endswith(ENDUNGEN_JS):
        return js(inhalt)
    return inhalt
