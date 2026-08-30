from __future__ import annotations

import re

TRENNER = re.compile(r"^:?-{2,}:?$")


def _ist_zeile(zeile: str) -> bool:
    roh = zeile.strip()
    return roh.startswith("|") and roh.count("|") >= 2


def _zellen(zeile: str) -> list[str]:
    roh = zeile.strip()
    if roh.startswith("|"):
        roh = roh[1:]
    if roh.endswith("|"):
        roh = roh[:-1]
    return [teil.strip() for teil in roh.split("|")]


def _ist_trenner(zeile: str) -> bool:
    if not _ist_zeile(zeile):
        return False
    felder = _zellen(zeile)
    return bool(felder) and all(TRENNER.match(feld) for feld in felder)


def _schmucklos(text: str) -> str:
    return text.replace("*", "").strip("_ ").strip()


def _als_liste(kopf: list[str], werte: list[str]) -> list[str]:
    gefuellt = [wert.strip() for wert in werte]
    if not any(gefuellt):
        return []
    if len(gefuellt) <= 2:
        links = gefuellt[0]
        rechts = gefuellt[1] if len(gefuellt) > 1 else ""
        return [f"- {links}: {rechts}" if rechts else f"- {links}"]
    zeilen = [f"- {gefuellt[0]}"]
    for i in range(1, len(gefuellt)):
        if not gefuellt[i]:
            continue
        label = _schmucklos(kopf[i]) if i < len(kopf) else ""
        zeilen.append(f"   {label}: {gefuellt[i]}" if label else f"   {gefuellt[i]}")
    return zeilen


def _wandle(block: str) -> str:
    zeilen = block.split("\n")
    raus: list[str] = []
    i = 0
    while i < len(zeilen):
        if (
            _ist_zeile(zeilen[i])
            and i + 1 < len(zeilen)
            and _ist_trenner(zeilen[i + 1])
        ):
            kopf = _zellen(zeilen[i])
            i += 2
            while i < len(zeilen) and _ist_zeile(zeilen[i]) and not _ist_trenner(zeilen[i]):
                raus.extend(_als_liste(kopf, _zellen(zeilen[i])))
                i += 1
            continue
        raus.append(zeilen[i])
        i += 1
    return "\n".join(raus)


def ohne_tabellen(text: str) -> str:
    if "|" not in text:
        return text
    teile = text.split("```")
    for i in range(0, len(teile), 2):
        teile[i] = _wandle(teile[i])
    return "```".join(teile)
