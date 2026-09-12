from __future__ import annotations

ZIELE: dict[str, dict[str, str]] = {
    "denken": {"name": "Jons Denken", "wozu": "Ziele, Verlauf, Gelerntes, Aufgaben"},
    "aufgaben": {"name": "Jons Denken", "wozu": "die laufenden Aufgaben"},
    "werkzeuge": {"name": "Alle Werkzeuge", "wozu": "die vollstaendige Werkzeugliste"},
    "suche": {"name": "Alles durchsuchen", "wozu": "Gespraeche, Wissen, Dateien"},
    "notizen": {"name": "Haftnotizen", "wozu": "kurze Notizen anlegen"},
    "tagebuch": {"name": "Sprach-Tagebuch", "wozu": "Eintraege sprechen und lesen"},
    "tresor": {"name": "Passwort-Tresor", "wozu": "Zugangsdaten verschluesselt ablegen"},
    "kalender": {"name": "Kalender", "wozu": "Termine und Erinnerungen"},
    "inbox": {"name": "Intelligente Inbox", "wozu": "Eingaenge sortiert"},
    "maps": {"name": "Jon Maps", "wozu": "Karten, Routen, Umgebung"},
    "studio": {"name": "Video und Foto", "wozu": "Bilder und Videos erzeugen"},
    "deep": {"name": "Deep Learning", "wozu": "eigenstaendige Tiefenrecherche"},
    "code": {"name": "Jon Code", "wozu": "Projekte bearbeiten"},
    "humanize": {"name": "Humanisierer", "wozu": "Texte natuerlicher machen"},
    "download": {"name": "Downloader", "wozu": "Videos und Musik laden"},
    "privat": {"name": "Privater Browser", "wozu": "spurloses Surfen"},
    "zwischenablage": {"name": "Clipboard-Historie", "wozu": "zuletzt Kopiertes"},
    "aufraeumen": {"name": "Ordner aufraeumen", "wozu": "Dateien sortieren"},
    "kochen": {"name": "Kochassistent", "wozu": "Rezepte finden"},
    "lernen": {"name": "Lern-Karteikarten", "wozu": "Karten lernen und abfragen"},
    "erklaer": {"name": "Bildschirm erklaeren", "wozu": "was gerade zu sehen ist"},
    "telefon": {"name": "Telefonanrufe", "wozu": "anrufen und Anrufe planen"},
    "handy": {"name": "Handy und Geraete", "wozu": "gekoppelte Geraete"},
    "spiele": {"name": "Spiele", "wozu": "die FelWorks-Sammlung"},
    "abendshow": {"name": "Abend-Show", "wozu": "Jon und Mini Jon im Dialog"},
    "freunde": {"name": "Freunde-Chat", "wozu": "mit anderen Jon-Nutzern"},
    "konten": {"name": "Konten und Nutzung", "wozu": "Schluessel und Verbrauch"},
    "nutzung": {"name": "Nutzung", "wozu": "Verbrauch und Kosten"},
    "skills": {"name": "Skills", "wozu": "Jons Anleitungen"},
    "einstellungen": {"name": "Einstellungen", "wozu": "alle Schalter"},
    "diagnose": {"name": "Diagnose", "wozu": "Geraete-Schluessel und Systemstand"},
}

WOERTER = {
    "ziele": "denken",
    "kopf": "denken",
    "gedanken": "denken",
    "aufgabenliste": "aufgaben",
    "tools": "werkzeuge",
    "search": "suche",
    "find": "suche",
    "notes": "notizen",
    "journal": "tagebuch",
    "vault": "tresor",
    "passwort": "tresor",
    "calendar": "kalender",
    "termine": "kalender",
    "karte": "maps",
    "karten": "maps",
    "navigation": "maps",
    "bild": "studio",
    "bilder": "studio",
    "foto": "studio",
    "video": "studio",
    "lerne": "deep",
    "research": "deep",
    "forschung": "deep",
    "recherche": "deep",
    "human": "humanize",
    "dl": "download",
    "downloader": "download",
    "private": "privat",
    "inkognito": "privat",
    "clipboard": "zwischenablage",
    "cleanup": "aufraeumen",
    "rezept": "kochen",
    "quiz": "lernen",
    "karteikarten": "lernen",
    "screen": "erklaer",
    "bildschirm": "erklaer",
    "anruf": "telefon",
    "anrufe": "telefon",
    "phone": "telefon",
    "android": "handy",
    "geraete": "handy",
    "games": "spiele",
    "show": "abendshow",
    "accounts": "konten",
    "login": "konten",
    "usage": "nutzung",
    "settings": "einstellungen",
    "zahnrad": "einstellungen",
}


def aufloesen(wunsch: str) -> str:
    roh = str(wunsch or "").strip().lower().lstrip("/")
    if not roh:
        return ""
    schlicht = "".join(z for z in roh if z.isalnum())
    if schlicht in ZIELE:
        return schlicht
    if schlicht in WOERTER:
        return WOERTER[schlicht]
    for name in ZIELE:
        if name in schlicht:
            return name
    for wort, ziel in WOERTER.items():
        if wort in schlicht and len(wort) >= 4:
            return ziel
    return ""


def oeffnen(wunsch: str) -> dict:
    ziel = aufloesen(wunsch)
    if not ziel:
        return {
            "error": f"Das Werkzeug '{wunsch}' kenne ich nicht.",
            "moeglich": sorted(ZIELE),
        }
    eintrag = ZIELE[ziel]
    return {
        "ok": True,
        "oeffne": ziel,
        "befehl": f"/{ziel}",
        "name": eintrag["name"],
        "hinweis": (
            f"{eintrag['name']} ist jetzt offen. Sag dem Nutzer in einem Satz, was er "
            "dort sieht - beschreibe nicht den Weg dorthin."
        ),
    }


def liste() -> dict:
    return {
        "werkzeuge": [
            {"ziel": name, "name": eintrag["name"], "wozu": eintrag["wozu"]}
            for name, eintrag in sorted(ZIELE.items())
        ]
    }
