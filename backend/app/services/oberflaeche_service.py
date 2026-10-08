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
    "harness": {"name": "Jon Harness", "wozu": "Coding-Agent mit Projektvorschau", "premium": "1"},
    "medien": {"name": "Stimmen und Transkripte", "wozu": "Audio, YouTube, Vorlesen", "premium": "1"},
    "fachteam": {"name": "Jon Fachteam", "wozu": "Fachagenten mit Gegenpruefung", "premium": "1"},
    "beobachten": {"name": "Beobachten", "wozu": "Jon meldet sich bei Neuigkeiten", "premium": "1"},
    "support": {"name": "Support", "wozu": "Fehler und Ideen melden", "premium": "1"},
    "player": {"name": "Player", "wozu": "Musik und Videos abspielen", "premium": "1"},
    "premium": {"name": "Jon Premium", "wozu": "Lizenz und Stufe", "premium": "1"},
    "profil": {"name": "Profil", "wozu": "Name und Bild", "premium": "1"},
    "minijon": {"name": "MiniJon", "wozu": "Aussehen und Verhalten von MiniJon", "premium": "1"},
    "verlauf": {"name": "Gespraechsverlauf", "wozu": "Seitenleiste mit allen Chats", "premium": "1"},
    "neuer_chat": {"name": "Neuer Chat", "wozu": "ein frisches Gespraech beginnen", "premium": "1"},
    "datei": {"name": "Dateiansicht", "wozu": "eine Datei in Jon anzeigen, anklicken und kommentieren", "premium": "1"},
    "alles_schliessen": {"name": "Alles schliessen", "wozu": "alle offenen Fenster in Jon schliessen", "premium": "1"},
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
    "coding": "harness",
    "codingagent": "harness",
    "jonharness": "harness",
    "transkript": "medien",
    "transkripte": "medien",
    "stimmen": "medien",
    "vorlesen": "medien",
    "agenten": "fachteam",
    "team": "fachteam",
    "agents": "fachteam",
    "musik": "player",
    "lizenz": "premium",
    "profile": "profil",
    "mini": "minijon",
    "pet": "minijon",
    "sidebar": "verlauf",
    "seitenleiste": "verlauf",
    "chats": "verlauf",
    "neuerchat": "neuer_chat",
    "newchat": "neuer_chat",
    "dateiansicht": "datei",
    "praesentation": "datei",
    "powerpoint": "datei",
    "dokument": "datei",
    "schliessen": "alles_schliessen",
    "allesschliessen": "alles_schliessen",
}


def aufloesen(wunsch: str) -> str:
    roh = str(wunsch or "").strip().lower().lstrip("/")
    if not roh:
        return ""
    schlicht = "".join(z for z in roh.replace("ß", "ss").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue") if z.isalnum() or z == "_")
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


def _premium() -> bool:
    from app.services.premium import unbegrenzt

    return unbegrenzt()


def oeffnen(wunsch: str, aktion: str = "oeffnen", datei: str = "") -> dict:
    ziel = aufloesen(wunsch) or ("datei" if datei else "")
    schliessen = aktion.strip().lower() in ("schliessen", "schließen", "zu", "close")
    if not ziel:
        return {
            "error": f"Den Bereich '{wunsch}' kenne ich nicht.",
            "moeglich": sorted(ZIELE),
        }
    eintrag = ZIELE[ziel]
    if (eintrag.get("premium") or schliessen) and not _premium():
        from app.services.premium import PremiumNoetig

        return {"error": PremiumNoetig("steuerung").text, "premium_noetig": "steuerung"}
    steuerung: dict = {"ziel": ziel, "aktion": "schliessen" if schliessen else "oeffnen"}
    if ziel == "datei":
        from pathlib import Path

        from app.services.dateiindex_service import karte
        from app.services.dateiraum_service import get_dateiraum_service

        pfad = Path(str(datei or "")).expanduser()
        erlaubt, grund = get_dateiraum_service().frei(pfad)
        if not datei or not pfad.is_file() or not erlaubt:
            return {"error": grund or "Gib mit datei den vollstaendigen Pfad einer vorhandenen Datei an."}
        steuerung["datei"] = karte(pfad)
    ergebnis = {
        "ok": True,
        "steuerung": steuerung,
        "name": eintrag["name"],
        "hinweis": (
            f"{eintrag['name']} ist jetzt {'geschlossen' if schliessen else 'offen'}. Sag dem Nutzer in einem Satz, "
            "was passiert ist - beschreibe nicht den Weg dorthin."
        ),
    }
    if not eintrag.get("premium") and not schliessen:
        ergebnis["oeffne"] = ziel
        ergebnis["befehl"] = f"/{ziel}"
    return ergebnis


def liste() -> dict:
    return {
        "werkzeuge": [
            {"ziel": name, "name": eintrag["name"], "wozu": eintrag["wozu"], **({"premium": True} if eintrag.get("premium") else {})}
            for name, eintrag in sorted(ZIELE.items())
        ],
        "premium_aktiv": _premium(),
    }
