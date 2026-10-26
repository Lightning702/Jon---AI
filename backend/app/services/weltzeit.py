from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

STAEDTE = {
    "tokio": ("Tokio", "Asia/Tokyo"),
    "tokyo": ("Tokio", "Asia/Tokyo"),
    "japan": ("Japan", "Asia/Tokyo"),
    "osaka": ("Osaka", "Asia/Tokyo"),
    "seoul": ("Seoul", "Asia/Seoul"),
    "suedkorea": ("Südkorea", "Asia/Seoul"),
    "peking": ("Peking", "Asia/Shanghai"),
    "beijing": ("Peking", "Asia/Shanghai"),
    "shanghai": ("Shanghai", "Asia/Shanghai"),
    "china": ("China", "Asia/Shanghai"),
    "hongkong": ("Hongkong", "Asia/Hong_Kong"),
    "hong kong": ("Hongkong", "Asia/Hong_Kong"),
    "singapur": ("Singapur", "Asia/Singapore"),
    "singapore": ("Singapur", "Asia/Singapore"),
    "bangkok": ("Bangkok", "Asia/Bangkok"),
    "thailand": ("Thailand", "Asia/Bangkok"),
    "bali": ("Bali", "Asia/Makassar"),
    "neu delhi": ("Neu-Delhi", "Asia/Kolkata"),
    "delhi": ("Neu-Delhi", "Asia/Kolkata"),
    "mumbai": ("Mumbai", "Asia/Kolkata"),
    "indien": ("Indien", "Asia/Kolkata"),
    "dubai": ("Dubai", "Asia/Dubai"),
    "abu dhabi": ("Abu Dhabi", "Asia/Dubai"),
    "istanbul": ("Istanbul", "Europe/Istanbul"),
    "tuerkei": ("Türkei", "Europe/Istanbul"),
    "moskau": ("Moskau", "Europe/Moscow"),
    "moscow": ("Moskau", "Europe/Moscow"),
    "kiew": ("Kiew", "Europe/Kyiv"),
    "athen": ("Athen", "Europe/Athens"),
    "griechenland": ("Griechenland", "Europe/Athens"),
    "london": ("London", "Europe/London"),
    "england": ("England", "Europe/London"),
    "dublin": ("Dublin", "Europe/Dublin"),
    "lissabon": ("Lissabon", "Europe/Lisbon"),
    "portugal": ("Portugal", "Europe/Lisbon"),
    "madrid": ("Madrid", "Europe/Madrid"),
    "paris": ("Paris", "Europe/Paris"),
    "berlin": ("Berlin", "Europe/Berlin"),
    "wien": ("Wien", "Europe/Vienna"),
    "zuerich": ("Zürich", "Europe/Zurich"),
    "rom": ("Rom", "Europe/Rome"),
    "kairo": ("Kairo", "Africa/Cairo"),
    "aegypten": ("Ägypten", "Africa/Cairo"),
    "kapstadt": ("Kapstadt", "Africa/Johannesburg"),
    "johannesburg": ("Johannesburg", "Africa/Johannesburg"),
    "nairobi": ("Nairobi", "Africa/Nairobi"),
    "new york": ("New York", "America/New_York"),
    "washington": ("Washington", "America/New_York"),
    "miami": ("Miami", "America/New_York"),
    "toronto": ("Toronto", "America/Toronto"),
    "chicago": ("Chicago", "America/Chicago"),
    "texas": ("Texas", "America/Chicago"),
    "denver": ("Denver", "America/Denver"),
    "los angeles": ("Los Angeles", "America/Los_Angeles"),
    "san francisco": ("San Francisco", "America/Los_Angeles"),
    "kalifornien": ("Kalifornien", "America/Los_Angeles"),
    "seattle": ("Seattle", "America/Los_Angeles"),
    "vancouver": ("Vancouver", "America/Vancouver"),
    "las vegas": ("Las Vegas", "America/Los_Angeles"),
    "hawaii": ("Hawaii", "Pacific/Honolulu"),
    "mexiko": ("Mexiko-Stadt", "America/Mexico_City"),
    "mexico city": ("Mexiko-Stadt", "America/Mexico_City"),
    "rio": ("Rio de Janeiro", "America/Sao_Paulo"),
    "sao paulo": ("São Paulo", "America/Sao_Paulo"),
    "brasilien": ("Brasilien", "America/Sao_Paulo"),
    "buenos aires": ("Buenos Aires", "America/Argentina/Buenos_Aires"),
    "argentinien": ("Argentinien", "America/Argentina/Buenos_Aires"),
    "sydney": ("Sydney", "Australia/Sydney"),
    "melbourne": ("Melbourne", "Australia/Melbourne"),
    "australien": ("Australien (Sydney)", "Australia/Sydney"),
    "perth": ("Perth", "Australia/Perth"),
    "auckland": ("Auckland", "Pacific/Auckland"),
    "neuseeland": ("Neuseeland", "Pacific/Auckland"),
}
WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
FRAGE = re.compile(
    r"^(?:und\s+)?(?:wie\s*spaet|wieviel\s+uhr|wie\s+viel\s+uhr|welche\s+uhrzeit|was\s+fuer\s+eine\s+uhrzeit|uhrzeit)"
    r"(?:\s+ist\s+es|\s+haben\s+wir|\s+hat\s+man)?(?:\s+(?:gerade|jetzt|aktuell|eigentlich))*"
    r"(?:\s+(?P<praep>in|auf|im)\s+(?P<ort>[a-z][a-z .]{1,40}?))?"
    r"(?:\s+(?:gerade|jetzt|aktuell|eigentlich))*"
    r"(?:\s+(?:bitte|danke|kurz|antworte\s+kurz|sag\s+kurz|nur\s+kurz|ganz\s+kurz))*\s*$"
)
VERBOTEN = re.compile(r"\b(wenn|falls|als|bei|seit|bis|vor|nach|morgen|gestern|um\s+\d|\d)\b")


def _normal(text: str) -> str:
    klein = (text or "").casefold()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        klein = klein.replace(alt, neu)
    klein = unicodedata.normalize("NFKD", klein)
    klein = "".join(z for z in klein if not unicodedata.combining(z))
    klein = re.sub(r"[?!.,;:\-]+", " ", klein)
    return re.sub(r"\s+", " ", klein).strip()


def ort_finden(ort: str) -> tuple[str, str] | None:
    sauber = re.sub(r"^(?:der|die|dem|den)\s+", "", ort.strip())
    return STAEDTE.get(sauber)


def antwort(text: str, utc: datetime | None = None) -> str | None:
    from zoneinfo import ZoneInfo

    normal = _normal(text)
    if not normal or len(normal) > 70:
        return None
    treffer = FRAGE.match(normal)
    if not treffer:
        return None
    ort = (treffer.group("ort") or "").strip()
    if VERBOTEN.search(ort):
        return None
    utc = utc or datetime.now(timezone.utc)
    lokal = utc.astimezone()
    if not ort:
        return f"Es ist {lokal.strftime('%H:%M')} Uhr ({WOCHENTAGE[lokal.weekday()]}, {lokal.strftime('%d.%m.%Y')})."
    gefunden = ort_finden(ort)
    if gefunden is None:
        return None
    name, zone = gefunden
    try:
        dort = utc.astimezone(ZoneInfo(zone))
    except Exception:
        return None
    hier_versatz, dort_versatz = lokal.utcoffset(), dort.utcoffset()
    unterschied = (dort_versatz - hier_versatz).total_seconds() / 3600 if hier_versatz is not None and dort_versatz is not None else 0.0
    if abs(unterschied) < 0.01:
        vergleich = "genauso spät wie hier"
    else:
        stunden = f"{abs(unterschied):g}".replace(".", ",")
        einheit = "Stunde" if abs(unterschied) == 1 else "Stunden"
        vergleich = f"{stunden} {einheit} {'später' if unterschied > 0 else 'früher'} als hier"
    tag = ""
    if dort.date() != lokal.date():
        wort = "schon" if dort.date() > lokal.date() else "noch"
        tag = f", {wort} {WOCHENTAGE[dort.weekday()]} der {dort.strftime('%d.%m.')}"
    praep = "Auf" if treffer.group("praep") == "auf" else "In"
    return f"{praep} {name} ist es jetzt {dort.strftime('%H:%M')} Uhr{tag} – {vergleich}."
