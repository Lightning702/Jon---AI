from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

WOCHENTAGE = {
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonnabend": 5,
    "sonntag": 6,
}

MONATE = {
    "januar": 1,
    "februar": 2,
    "maerz": 3,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}

ZAHLWORT = {
    "einem": 1,
    "einer": 1,
    "eins": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fuenf": 5,
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwoelf": 12,
    "zwölf": 12,
}


@dataclass
class Spanne:
    von: datetime
    bis: datetime
    beschreibung: str
    zukunft: bool = False

    def als_dict(self) -> dict:
        return {
            "von": self.von.isoformat(timespec="seconds"),
            "bis": self.bis.isoformat(timespec="seconds"),
            "beschreibung": self.beschreibung,
            "zukunft": self.zukunft,
        }

    def enthaelt(self, moment: datetime) -> bool:
        return self.von <= moment <= self.bis


def _tagesspanne(tag: date, beschreibung: str, zukunft: bool = False) -> Spanne:
    return Spanne(
        datetime.combine(tag, time.min),
        datetime.combine(tag, time.max),
        beschreibung,
        zukunft,
    )


def verstehen(text: str, jetzt: datetime | None = None) -> Spanne:
    moment = jetzt or datetime.now()
    heute = moment.date()
    roh = str(text or "").strip().lower()

    if not roh or roh in ("heute", "today", "jetzt"):
        return _tagesspanne(heute, "heute")
    if roh in ("gestern", "yesterday"):
        return _tagesspanne(heute - timedelta(days=1), "gestern")
    if roh in ("vorgestern",):
        return _tagesspanne(heute - timedelta(days=2), "vorgestern")
    if roh in ("morgen", "tomorrow"):
        return _tagesspanne(heute + timedelta(days=1), "morgen", zukunft=True)
    if roh in ("uebermorgen", "übermorgen"):
        return _tagesspanne(heute + timedelta(days=2), "uebermorgen", zukunft=True)

    if "diese woche" in roh or roh in ("woche", "this week"):
        start = heute - timedelta(days=heute.weekday())
        return Spanne(
            datetime.combine(start, time.min),
            datetime.combine(start + timedelta(days=6), time.max),
            "diese Woche",
        )
    if "letzte woche" in roh or "vorige woche" in roh:
        start = heute - timedelta(days=heute.weekday() + 7)
        return Spanne(
            datetime.combine(start, time.min),
            datetime.combine(start + timedelta(days=6), time.max),
            "letzte Woche",
        )
    if "naechste woche" in roh or "nächste woche" in roh:
        start = heute + timedelta(days=7 - heute.weekday())
        return Spanne(
            datetime.combine(start, time.min),
            datetime.combine(start + timedelta(days=6), time.max),
            "naechste Woche",
            zukunft=True,
        )
    if "dieser monat" in roh or "diesen monat" in roh:
        start = heute.replace(day=1)
        naechster = (start + timedelta(days=32)).replace(day=1)
        return Spanne(
            datetime.combine(start, time.min),
            datetime.combine(naechster - timedelta(days=1), time.max),
            "dieser Monat",
        )
    if "letzter monat" in roh or "letzten monat" in roh:
        erster = heute.replace(day=1)
        ende = erster - timedelta(days=1)
        return Spanne(
            datetime.combine(ende.replace(day=1), time.min),
            datetime.combine(ende, time.max),
            "letzter Monat",
        )

    treffer = re.search(r"vor\s+(\d+|[a-zäöü]+)\s+(minute|stunde|tag|woche|monat)", roh)
    if treffer:
        rohzahl = treffer.group(1)
        anzahl = int(rohzahl) if rohzahl.isdigit() else ZAHLWORT.get(rohzahl, 1)
        einheit = treffer.group(2)
        if einheit == "minute":
            start = moment - timedelta(minutes=anzahl)
            return Spanne(start, moment, f"die letzten {anzahl} Minuten")
        if einheit == "stunde":
            start = moment - timedelta(hours=anzahl)
            return Spanne(start, moment, f"die letzten {anzahl} Stunden")
        if einheit == "tag":
            tag = heute - timedelta(days=anzahl)
            return _tagesspanne(tag, f"vor {anzahl} Tagen")
        if einheit == "woche":
            start = heute - timedelta(weeks=anzahl)
            return Spanne(
                datetime.combine(start, time.min),
                datetime.combine(start + timedelta(days=6), time.max),
                f"vor {anzahl} Wochen",
            )
        start = heute - timedelta(days=30 * anzahl)
        return Spanne(
            datetime.combine(start, time.min), moment, f"vor {anzahl} Monaten"
        )

    treffer = re.search(r"letzte[nr]?\s+(\d+)\s+(stunde|tag|woche)", roh)
    if treffer:
        anzahl = int(treffer.group(1))
        einheit = treffer.group(2)
        if einheit == "stunde":
            return Spanne(
                moment - timedelta(hours=anzahl), moment, f"die letzten {anzahl} Stunden"
            )
        if einheit == "tag":
            return Spanne(
                datetime.combine(heute - timedelta(days=anzahl - 1), time.min),
                datetime.combine(heute, time.max),
                f"die letzten {anzahl} Tage",
            )
        return Spanne(
            datetime.combine(heute - timedelta(weeks=anzahl), time.min),
            datetime.combine(heute, time.max),
            f"die letzten {anzahl} Wochen",
        )

    for name, nummer in WOCHENTAGE.items():
        if name in roh:
            rueckwaerts = "letzt" in roh or "vergangen" in roh or "war" in roh
            differenz = (heute.weekday() - nummer) % 7
            if rueckwaerts:
                tag = heute - timedelta(days=differenz or 7)
                return _tagesspanne(tag, f"letzter {name.capitalize()}")
            vor = (nummer - heute.weekday()) % 7
            tag = heute + timedelta(days=vor)
            return _tagesspanne(
                tag, f"{name.capitalize()}", zukunft=tag > heute
            )

    treffer = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})?", roh)
    if treffer:
        tag_nr = int(treffer.group(1))
        monat = int(treffer.group(2))
        jahr = int(treffer.group(3) or heute.year)
        if jahr < 100:
            jahr += 2000
        try:
            tag = date(jahr, monat, tag_nr)
            return _tagesspanne(
                tag, tag.strftime("%d.%m.%Y"), zukunft=tag > heute
            )
        except ValueError:
            pass

    treffer = re.search(r"(\d{1,2})\.?\s*(" + "|".join(MONATE) + ")", roh)
    if treffer:
        tag_nr = int(treffer.group(1))
        monat = MONATE[treffer.group(2)]
        try:
            tag = date(heute.year, monat, tag_nr)
            return _tagesspanne(
                tag, tag.strftime("%d.%m.%Y"), zukunft=tag > heute
            )
        except ValueError:
            pass

    return Spanne(
        datetime.combine(heute - timedelta(days=6), time.min),
        datetime.combine(heute, time.max),
        "die letzten sieben Tage",
    )
