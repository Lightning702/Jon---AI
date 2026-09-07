from __future__ import annotations

import re

MUSTER: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(?i)winerror 5|permission denied|zugriff verweigert"),
        "Windows laesst das nicht zu (fehlende Rechte). Schliess die Datei oder das "
        "Programm, das sie benutzt, oder starte Jon als Administrator.",
    ),
    (
        re.compile(r"(?i)winerror 32|being used by another process"),
        "Die Datei ist gerade von einem anderen Programm geoeffnet. Schliess sie und "
        "versuch es noch einmal.",
    ),
    (
        re.compile(r"(?i)filenotfounderror|winerror 2|no such file"),
        "Diesen Pfad gibt es nicht. Pruef die Schreibweise oder lass dir den Ordner "
        "erst mit list_dir zeigen.",
    ),
    (
        re.compile(r"(?i)winerror 3|cannot find the path"),
        "Den Ordner gibt es nicht. Leg ihn vorher an oder nimm einen anderen Pfad.",
    ),
    (
        re.compile(r"(?i)notadirectoryerror"),
        "Das ist eine Datei, kein Ordner.",
    ),
    (
        re.compile(r"(?i)isadirectoryerror"),
        "Das ist ein Ordner, keine Datei.",
    ),
    (
        re.compile(r"(?i)disk|no space left|winerror 112"),
        "Die Festplatte ist voll. Raeum etwas auf und versuch es noch einmal.",
    ),
    (
        re.compile(r"(?i)err_name_not_resolved|getaddrinfo failed|name or service not known"),
        "Diese Adresse gibt es nicht oder der Name laesst sich nicht aufloesen. "
        "Stimmt die Schreibweise?",
    ),
    (
        re.compile(r"(?i)err_internet_disconnected|network is unreachable|connectionerror"),
        "Keine Internetverbindung. Sobald du wieder online bist, klappt es.",
    ),
    (
        re.compile(r"(?i)err_connection_refused|connection refused"),
        "Der Server nimmt gerade keine Verbindungen an.",
    ),
    (
        re.compile(r"(?i)timeout|timed out"),
        "Zeitueberschreitung - es hat zu lange gedauert. Versuch es gleich noch einmal "
        "oder nimm einen kleineren Schritt.",
    ),
    (
        re.compile(r"(?i)ssl|certificate verify"),
        "Das Sicherheitszertifikat der Seite passt nicht. Aus Vorsicht wurde "
        "abgebrochen.",
    ),
    (
        re.compile(r"(?i)401|unauthorized|invalid api key|incorrect api key"),
        "Der Zugangsschluessel wird abgelehnt. Pruef den Schluessel unter "
        "Einstellungen -> Konten.",
    ),
    (
        re.compile(r"(?i)429|rate limit|too many requests"),
        "Der Anbieter bremst gerade (zu viele Anfragen). Warte kurz und versuch es "
        "noch einmal.",
    ),
    (
        re.compile(r"(?i)402|quota|insufficient (funds|credit|balance)"),
        "Beim Anbieter ist kein Guthaben mehr uebrig.",
    ),
    (
        re.compile(r"(?i)5\d\d server error|internal server error|bad gateway"),
        "Beim Anbieter ist etwas schiefgegangen. Das liegt nicht an dir - gleich "
        "noch einmal versuchen.",
    ),
    (
        re.compile(r"(?i)json|expecting value|unmarshal"),
        "Die Antwort war unvollstaendig oder kein gueltiges Format.",
    ),
    (
        re.compile(r"(?i)playwright|executable doesn't exist"),
        "Der Browser ist noch nicht fertig installiert. Beim naechsten Versuch "
        "sollte es klappen.",
    ),
    (
        re.compile(r"(?i)modulenotfounderror|no module named"),
        "Ein benoetigtes Zusatzpaket fehlt in dieser Installation.",
    ),
    (
        re.compile(r"(?i)memoryerror|out of memory"),
        "Der Arbeitsspeicher hat nicht gereicht. Versuch es mit weniger Daten.",
    ),
]

TECHNISCH = re.compile(r"(?i)traceback|at 0x[0-9a-f]+|file \"|line \d+")


def verstaendlich(fehler: str | BaseException, was: str = "") -> str:
    roh = str(fehler).strip()
    if not roh:
        return "Unbekannter Fehler."
    for muster, text in MUSTER:
        if muster.search(roh):
            return f"{was}: {text}" if was else text
    erste = roh.splitlines()[0]
    if TECHNISCH.search(roh) or len(erste) > 200:
        kurz = erste[:160]
        return (
            f"{was}: {kurz}" if was else f"Das hat nicht geklappt: {kurz}"
        )
    return f"{was}: {erste}" if was else erste
