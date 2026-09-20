from __future__ import annotations

import os
import shutil
import sys

RESET = "\033[0m"
FETT = "\033[1m"
MATT = "\033[2m"
HELL = "\033[97m"
TUERKIS = "\033[38;5;45m"
BLAU = "\033[38;5;39m"
TIEF = "\033[38;5;24m"
GRUEN = "\033[38;5;78m"
GRAU = "\033[38;5;245m"
ROT = "\033[38;5;203m"

LOGO = [
    "       __            ",
    "      / /___   ____  ",
    " __  / / __ \\ / __ \\ ",
    "/ /_/ / /_/ // / / / ",
    "\\____/ \\____//_/ /_/ ",
]

FIGUR = [
    "        ╭───╮        ",
    "        │ ● │        ",
    "    ╭───┴───┴───╮    ",
    "   ╭╯           ╰╮   ",
    "   │  ███   ███  │   ",
    "   │             │   ",
    "   │   ╲_____╱   │   ",
    "   ╰╮           ╭╯   ",
    "    ╰───┬───┬───╯    ",
    "     ╭──┴╮ ╭┴──╮     ",
    "     ╰───╯ ╰───╯     ",
]

BLASE = [
    "╭" + "─" * 23 + "╮",
    "│  Einfach jon          │",
    "│  eingeben und         │",
    "│  los geht's!          │",
    "╰" + "─" * 15 + "╮╭" + "─" * 6 + "╯",
    " " * 16 + "╰╯" + " " * 7,
]

MENUE = [
    ("▭", "Chat", "Mit Jon sprechen"),
    ("</>", "Code", "Code schreiben, debuggen, refactoren"),
    ("▤", "Dateien", "Dateien analysieren und bearbeiten"),
    ("▣", "System", "Deinen Computer steuern"),
    ("◍", "Browser", "Im Web recherchieren und Aufgaben erledigen"),
    ("▥", "Projekte", "An deinen Projekten arbeiten (z.B. in VS Code)"),
    ("✱", "Tools", "Alle verfügbaren Tools"),
    ("◈", "Memory", "Auf dein Wissen und Erinnerungen zugreifen"),
    ("◆", "Agent", "Komplexe Aufgaben automatisch erledigen"),
    ("✦", "Einstellungen", "Jon konfigurieren"),
]

VERSPRECHEN = [
    "Läuft in jedem Terminal",
    "Vollständiger Jon Funktionsumfang",
    "Zugriff auf deine Projekte",
    "Code, Dateien, System, Browser und mehr",
    "Integriert in deine Tools (z.B. VS Code)",
]

BEISPIELE = [
    "erkläre mir dieses Projekt",
    "öffne vscode",
    "analysiere den code",
    "suche fehler",
    "erstelle eine neue feature-branch",
    "schreibe tests dafür",
    "starte den backend-server",
    "öffne youtube und suche nach ...",
    "zeige meine aufgaben",
    "was steht heute im kalender?",
    "steuere mein smart home",
    "erstelle eine präsentation über ...",
]

SPRACHE = [
    "Deutsch oder Englisch",
    "Kontext aus dem aktuellen Verzeichnis",
    "Versteht deine Projekte",
    "Führt komplexe Aufgaben selbstständig aus",
]

ORTE = [
    "Windows CMD",
    "PowerShell",
    "macOS Terminal (zsh, bash)",
    "Linux Terminal",
    "Integriert in VS Code, IntelliJ, etc.",
    "Als globaler Befehl: jon",
]

SPRUCH = [
    "„Mehr als ein Chatbot.",
    " Ein Assistent für dein ganzes System.\"",
]


def farbig() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("JON_CLI_EINFARBIG"):
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


class Stift:
    def __init__(self) -> None:
        self.an = farbig()

    def __call__(self, text: str, *farben: str) -> str:
        if not self.an or not farben:
            return text
        return "".join(farben) + text + RESET


def breite() -> int:
    try:
        return max(60, shutil.get_terminal_size((100, 30)).columns)
    except Exception:
        return 100


def sichtbar(text: str) -> int:
    laenge = 0
    i = 0
    while i < len(text):
        if text[i] == "\033":
            while i < len(text) and text[i] != "m":
                i += 1
            i += 1
            continue
        laenge += 2 if _breit(text[i]) else 1
        i += 1
    return laenge


def _breit(zeichen: str) -> bool:
    punkt = ord(zeichen)
    return (
        0x1100 <= punkt <= 0x115F
        or 0x2E80 <= punkt <= 0xA4CF
        or 0xAC00 <= punkt <= 0xD7A3
        or 0xF900 <= punkt <= 0xFAFF
        or 0xFE30 <= punkt <= 0xFE6F
        or 0xFF00 <= punkt <= 0xFF60
        or 0xFFE0 <= punkt <= 0xFFE6
        or 0x1F300 <= punkt <= 0x1FAFF
    )


def fuellen(zeile: str, weite: int) -> str:
    fehlt = weite - sichtbar(zeile)
    return zeile + " " * max(0, fehlt)


def nebeneinander(links: list[str], rechts: list[str], abstand: int = 4) -> list[str]:
    hoehe = max(len(links), len(rechts))
    weite = max((sichtbar(z) for z in links), default=0)
    zeilen = []
    for i in range(hoehe):
        a = links[i] if i < len(links) else ""
        b = rechts[i] if i < len(rechts) else ""
        zeilen.append(fuellen(a, weite) + " " * abstand + b)
    return zeilen


def rahmen(titel: str, inhalt: list[str], stift: Stift, ton: str = TUERKIS) -> list[str]:
    weite = max([sichtbar(z) for z in inhalt] + [sichtbar(titel) + 4])
    oben = stift("╭─ ", ton) + stift(titel, ton, FETT) + stift(
        " " + "─" * max(0, weite - sichtbar(titel) - 1) + "╮", ton
    )
    zeilen = [oben]
    for z in inhalt:
        zeilen.append(stift("│ ", ton) + fuellen(z, weite) + stift(" │", ton))
    zeilen.append(stift("╰" + "─" * (weite + 2) + "╯", ton))
    return zeilen


def liste(eintraege: list[str], stift: Stift, zeichen: str = "✓") -> list[str]:
    return [stift(f" {zeichen} ", GRUEN) + stift(e, HELL) for e in eintraege]


def logo(stift: Stift, version: str) -> list[str]:
    zeilen = [stift(z, TUERKIS, FETT) for z in LOGO]
    zeilen[-1] = zeilen[-1] + stift(f"  v{version}", GRAU)
    return zeilen


def figur(stift: Stift) -> list[str]:
    zeilen = []
    for i, z in enumerate(FIGUR):
        if i == 4:
            kopf, augen, rest = z[:6], z[6:15], z[15:]
            zeilen.append(
                stift(kopf, BLAU) + stift(augen, TUERKIS, FETT) + stift(rest, BLAU)
            )
        elif i == 1:
            zeilen.append(stift(z, TUERKIS))
        else:
            zeilen.append(stift(z, BLAU))
    return zeilen


def blase(stift: Stift) -> list[str]:
    zeilen = []
    for z in BLASE:
        if "jon" in z:
            vorn, hinten = z.split("jon", 1)
            zeilen.append(
                stift(vorn, TIEF) + stift("jon", TUERKIS, FETT) + stift(hinten, TIEF)
            )
        else:
            zeilen.append(stift(z, TIEF))
    return zeilen


def menue(stift: Stift) -> list[str]:
    zeilen = []
    for symbol, name, text in MENUE:
        marke = stift(" " + symbol + " " * (4 - sichtbar(symbol)), GRAU)
        zeilen.append(marke + stift(f"{name:<15}", TUERKIS) + stift(text, HELL))
    return zeilen


def kopf(stift: Stift, version: str, name: str, schmal: bool) -> str:
    gruss = [
        "",
        stift(f"Hallo {name}!", HELL, FETT),
        stift("Ich bin Jon — dein persönlicher KI-Assistent, direkt im Terminal.", HELL),
        stift("Was kann ich für dich tun?", HELL),
        "",
    ]
    links = logo(stift, version) + gruss + menue(stift)
    links += [
        "",
        stift('Tipp: Schreib einfach, was du willst. (z.B. "hilfe")', MATT),
    ]
    if schmal:
        return "\n".join(links)
    rechts = blase(stift) + [" " * 6 + z for z in figur(stift)] + [""]
    rechts += [
        " " * 4 + stift("ÜBERALL.", TUERKIS, FETT),
        " " * 4 + stift("IMMER.", TUERKIS, FETT),
        " " * 4 + stift("DEIN JON.", TUERKIS, FETT),
        " " * 4 + stift("▔▔▔▔▔▔▔▔▔", BLAU),
        "",
    ]
    rechts += [" " * 2 + stift(z, GRAU) for z in SPRUCH] + [""]
    rechts += [" " * 2 + z for z in liste(VERSPRECHEN, stift)]
    return "\n".join(nebeneinander(links, rechts))


def hilfe(stift: Stift, schmal: bool) -> str:
    beispiele = [stift("Du> ", TIEF) + stift(b, HELL) for b in BEISPIELE]
    links = rahmen("Beispiele", beispiele, stift)
    mitte = rahmen("Natürliche Sprache", liste(SPRACHE, stift), stift)
    rechts = rahmen("Überall verfügbar", liste(ORTE, stift), stift)
    befehle = rahmen(
        "Befehle",
        [
            stift(f" {b:<17}", TUERKIS) + stift(t, HELL)
            for b, t in (
                ("chat", "in den normalen Chat wechseln"),
                ("code", "Code-Modus für dieses Projekt"),
                ("tools", "alle verfügbaren Tools zeigen"),
                ("memory", "Erinnerungen zeigen"),
                ("projekte", "Projektstruktur anzeigen"),
                ("einstellungen", "Provider, Modell, Verzeichnis"),
                ("modell <n>", "Modell waehlen — bleibt gemerkt"),
                ("anbieter <n>", "Anbieter waehlen — bleibt gemerkt"),
                ("neu", "Verlauf löschen"),
                ("hilfe", "diese Übersicht"),
                ("ende", "Jon beenden"),
            )
        ],
        stift,
    )
    if schmal:
        return "\n".join(links + [""] + mitte + [""] + rechts + [""] + befehle)
    return "\n".join(
        nebeneinander(links, nebeneinander(mitte + [""] + rechts, befehle, 3), 3)
    )


def fuss(stift: Stift) -> str:
    return stift(
        "Jon — In jedem Terminal. Auf jedem System. Für alles, was du vorhast.", MATT
    )
