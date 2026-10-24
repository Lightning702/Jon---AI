from __future__ import annotations

AKTION_FELDER = ("aktion", "action", "typ", "type", "was")
FOLIE_FELDER = (("slide", 0), ("slide_number", 0), ("seite", 0), ("nummer", 0), ("slide_index", 1), ("slide_idx", 1))
LISTEN_FELDER = ("aktionen", "actions", "schritte", "steps", "changes", "edits", "aenderungen", "slides", "folien")


def liste(args: dict) -> object:
    return next((args[f] for f in LISTEN_FELDER if args.get(f)), [])


def normalisieren(aktion: dict, namen: dict[str, str], bildfelder: tuple[str, ...], folien: bool = False) -> dict:
    name = next((str(aktion[f]).strip().lower() for f in AKTION_FELDER if str(aktion.get(f) or "").strip()), "")
    name = namen.get(name, name)
    if not name and any(str(aktion.get(f) or "").strip() for f in bildfelder if f != "pfad"):
        name = "bild"
    if name:
        aktion["aktion"] = name
    if folien and not aktion.get("folie"):
        for feld, verschiebung in FOLIE_FELDER:
            wert = aktion.get(feld)
            if isinstance(wert, bool):
                continue
            if isinstance(wert, int) or (isinstance(wert, str) and wert.strip().isdigit()):
                aktion["folie"] = int(wert) + verschiebung
                break
    return aktion
