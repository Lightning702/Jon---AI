from __future__ import annotations

import os
import re
import shutil
import sys
import threading
import time

FARBE = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

RESET = "\x1b[0m"
FETT = "\x1b[1m"
MATT = "\x1b[2m"
KURSIV = "\x1b[3m"
GOLD = "\x1b[38;2;232;185;74m"
GOLD_HELL = "\x1b[38;2;250;214;124m"
BLAU = "\x1b[38;2;94;156;255m"
BLAU_TIEF = "\x1b[38;2;58;104;214m"
TUERKIS = "\x1b[38;2;92;214;214m"
GRUEN = "\x1b[38;2;104;211;145m"
ROT = "\x1b[38;2;255;110;110m"
GRAU = "\x1b[38;2;140;146;160m"
WEISS = "\x1b[38;2;232;236;244m"
LILA = "\x1b[38;2;186;140;255m"
HG_GRUEN = "\x1b[48;2;20;60;36m"
HG_ROT = "\x1b[48;2;70;24;28m"

LOGO = [
    "     ██╗ ██████╗ ███╗   ██╗",
    "     ██║██╔═══██╗████╗  ██║",
    "     ██║██║   ██║██╔██╗ ██║",
    "██   ██║██║   ██║██║╚██╗██║",
    "╚█████╔╝╚██████╔╝██║ ╚████║",
    " ╚════╝  ╚═════╝ ╚═╝  ╚═══╝",
]

_ausgabe_lock = threading.RLock()


def vorbereiten() -> None:
    global FARBE
    for strom in (sys.stdout, sys.stderr, sys.stdin):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if sys.platform == "win32":
        try:
            import ctypes

            kernel = ctypes.windll.kernel32
            griff = kernel.GetStdHandle(-11)
            modus = ctypes.c_uint32()
            if kernel.GetConsoleMode(griff, ctypes.byref(modus)):
                kernel.SetConsoleMode(griff, modus.value | 0x0004 | 0x0001)
            kernel.SetConsoleOutputCP(65001)
            kernel.SetConsoleCP(65001)
        except Exception:
            os.system("")
    FARBE = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def f(text: str, *stile: str) -> str:
    if not FARBE or not stile:
        return text
    return "".join(stile) + text + RESET


def breite() -> int:
    return max(40, min(shutil.get_terminal_size((100, 30)).columns, 160))


def sag(text: str = "", ende: str = "\n") -> None:
    with _ausgabe_lock:
        sys.stdout.write(text + ende)
        sys.stdout.flush()


def verlauf_farbe(text: str, start: tuple[int, int, int], ziel: tuple[int, int, int]) -> str:
    if not FARBE:
        return text
    teile = []
    laenge = max(1, len(text) - 1)
    for i, zeichen in enumerate(text):
        anteil = i / laenge
        r = int(start[0] + (ziel[0] - start[0]) * anteil)
        g = int(start[1] + (ziel[1] - start[1]) * anteil)
        b = int(start[2] + (ziel[2] - start[2]) * anteil)
        teile.append(f"\x1b[38;2;{r};{g};{b}m{zeichen}")
    return "".join(teile) + RESET


def kopf(version: str, zeilen: list[tuple[str, str]]) -> None:
    sag()
    if breite() >= 62:
        for zeile in LOGO:
            sag("  " + verlauf_farbe(zeile, (94, 156, 255), (232, 185, 74)) + "   " if zeile else "")
        sag(f("  H A R N E S S", GOLD, FETT) + f(f"   v{version}  ·  von FelWorks", GRAU))
    else:
        sag(f("  JON HARNESS", GOLD, FETT) + f(f"  v{version}", GRAU))
    sag()
    lang = max((len(name) for name, _ in zeilen), default=0)
    for name, wert in zeilen:
        sag("  " + f(name.ljust(lang), GRAU) + "  " + wert)
    sag()


def trenner() -> str:
    return f("─" * min(breite() - 2, 96), GRAU, MATT)


def kasten(titel: str, zeilen: list[str], farbe: str = BLAU) -> None:
    weit = min(breite() - 4, 100)
    sag(f("╭─ ", farbe) + f(titel, FETT, farbe) + f(" " + "─" * max(0, weit - len(titel) - 4) + "╮", farbe))
    for zeile in zeilen:
        sichtbar = len(re.sub(r"\x1b\[[0-9;]*m", "", zeile))
        sag(f("│ ", farbe) + zeile + " " * max(0, weit - sichtbar - 3) + f("│", farbe))
    sag(f("╰" + "─" * (weit - 1) + "╯", farbe))


class Kreisel:
    ZEICHEN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    nebenbei = None

    def __init__(self, text: str = "Jon denkt") -> None:
        self.text = text
        self._stopp = threading.Event()
        self._faden: threading.Thread | None = None
        self._start = 0.0
        self.zusatz = ""

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stopp()

    def start(self) -> None:
        if not sys.stdout.isatty():
            return
        self._start = time.time()
        self._stopp.clear()
        self._faden = threading.Thread(target=self._lauf, daemon=True)
        self._faden.start()

    def _lauf(self) -> None:
        i = 0
        while not self._stopp.wait(0.09):
            sekunden = int(time.time() - self._start)
            zeile = f("  " + self.ZEICHEN[i % len(self.ZEICHEN)] + " ", GOLD) + f(self.text, WEISS) + f(f" · {sekunden} s" + (f" · {self.zusatz}" if self.zusatz else "") + " · Strg+C bricht ab", GRAU)
            anzeige = Kreisel.nebenbei
            if anzeige is not None:
                try:
                    zeile += anzeige()
                except Exception:
                    pass
            with _ausgabe_lock:
                sys.stdout.write("\r\x1b[2K" + zeile)
                sys.stdout.flush()
            i += 1

    def stopp(self) -> None:
        if self._faden is None:
            return
        self._stopp.set()
        self._faden.join(timeout=1)
        self._faden = None
        with _ausgabe_lock:
            sys.stdout.write("\r\x1b[2K")
            sys.stdout.flush()


class Markdown:
    def __init__(self, einzug: str = "  ", vorsatz: str = "") -> None:
        self.puffer = ""
        self.im_code = False
        self.einzug = einzug
        self.vorsatz = vorsatz
        self.geschrieben = False
        self.leer = 0

    def zufuehren(self, stueck: str) -> None:
        self.puffer += stueck
        while "\n" in self.puffer:
            zeile, self.puffer = self.puffer.split("\n", 1)
            self._zeile(zeile)

    def ende(self) -> None:
        if self.puffer.strip():
            self._zeile(self.puffer)
        self.puffer = ""

    def _zeile(self, zeile: str) -> None:
        roh = zeile.rstrip()
        if not roh.strip() and not self.im_code:
            if self.geschrieben:
                self.leer += 1
            return
        if self.leer:
            sag()
            self.leer = 0
        if not self.geschrieben and self.vorsatz:
            with _ausgabe_lock:
                sys.stdout.write(self.vorsatz)
            einzug_alt = self.einzug
            self.einzug = ""
            self.geschrieben = True
            self._zeile_zeigen(roh)
            self.einzug = einzug_alt
            return
        self.geschrieben = True
        self._zeile_zeigen(roh)

    def _zeile_zeigen(self, roh: str) -> None:
        if roh.strip().startswith("```"):
            self.im_code = not self.im_code
            sprache = roh.strip()[3:].strip()
            if self.im_code:
                sag(self.einzug + f("┌─ " + (sprache or "code"), GRAU))
            else:
                sag(self.einzug + f("└─", GRAU))
            return
        if self.im_code:
            sag(self.einzug + f("│ ", GRAU) + f(roh, TUERKIS))
            return
        ueber = re.match(r"^(#{1,6})\s+(.*)$", roh)
        if ueber:
            stufe = len(ueber.group(1))
            text = self._inline(ueber.group(2))
            sag(self.einzug + (f(text, FETT, GOLD) if stufe <= 2 else f(text, FETT, WEISS)))
            return
        punkt = re.match(r"^(\s*)[-*+]\s+(.*)$", roh)
        if punkt:
            sag(self.einzug + punkt.group(1) + f("• ", BLAU) + self._inline(punkt.group(2)))
            return
        nummer = re.match(r"^(\s*)(\d+)[.)]\s+(.*)$", roh)
        if nummer:
            sag(self.einzug + nummer.group(1) + f(nummer.group(2) + ". ", BLAU) + self._inline(nummer.group(3)))
            return
        if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", roh):
            sag(self.einzug + trenner())
            return
        if roh.startswith(">"):
            sag(self.einzug + f("▌ ", GRAU) + f(self._inline(roh.lstrip("> ")), KURSIV))
            return
        sag(self.einzug + self._inline(roh))

    def _inline(self, text: str) -> str:
        if not FARBE:
            return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"`([^`]+)`", lambda m: f(m.group(1), TUERKIS), text)
        text = re.sub(r"\*\*(.+?)\*\*", lambda m: f(m.group(1), FETT), text)
        text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", lambda m: f(m.group(1), KURSIV), text)
        text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", lambda m: f(m.group(1), BLAU) + f(f" ({m.group(2)})", GRAU), text)
        return text


def _taste() -> str:
    if sys.platform == "win32":
        import msvcrt

        zeichen = msvcrt.getwch()
        if zeichen in ("\x00", "\xe0"):
            weiter = msvcrt.getwch()
            return {"H": "hoch", "P": "runter", "K": "links", "M": "rechts"}.get(weiter, "")
        if zeichen == "\r":
            return "enter"
        if zeichen == "\x1b":
            return "esc"
        if zeichen == "\x03":
            raise KeyboardInterrupt
        return zeichen
    import termios
    import tty

    griff = sys.stdin.fileno()
    alt = termios.tcgetattr(griff)
    try:
        tty.setraw(griff)
        zeichen = sys.stdin.read(1)
        if zeichen == "\x1b":
            folge = sys.stdin.read(2)
            return {"[A": "hoch", "[B": "runter", "[C": "rechts", "[D": "links"}.get(folge, "esc")
        if zeichen in ("\r", "\n"):
            return "enter"
        if zeichen == "\x03":
            raise KeyboardInterrupt
        return zeichen
    finally:
        termios.tcsetattr(griff, termios.TCSADRAIN, alt)


def waehlen(titel: str, eintraege: list[tuple[str, str]], start: int = 0) -> int | None:
    if not eintraege:
        return None
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        sag(f(titel, FETT, GOLD))
        for i, (name, hinweis) in enumerate(eintraege, 1):
            sag(f"  {i:>2}. {name}" + (f("  " + hinweis, GRAU) if hinweis else ""))
        try:
            eingabe = input("  Nummer: ").strip()
        except EOFError:
            return None
        return int(eingabe) - 1 if eingabe.isdigit() and 1 <= int(eingabe) <= len(eintraege) else None
    auswahl = max(0, min(start, len(eintraege) - 1))
    sag(f("  " + titel, FETT, GOLD) + f("   ↑↓ wählen · Enter bestätigen · Esc abbrechen", GRAU))
    gezeichnet = 0

    def zeichnen() -> None:
        nonlocal gezeichnet
        with _ausgabe_lock:
            if gezeichnet:
                sys.stdout.write(f"\x1b[{gezeichnet}F")
            for i, (name, hinweis) in enumerate(eintraege):
                aktiv = i == auswahl
                marke = f("❯ ", GOLD, FETT) if aktiv else "  "
                zeile = marke + (f(name, WEISS, FETT) if aktiv else f(name, WEISS)) + (f("  " + hinweis, GRAU) if hinweis else "")
                sys.stdout.write("\x1b[2K  " + zeile + "\n")
            sys.stdout.flush()
            gezeichnet = len(eintraege)

    zeichnen()
    puffer = ""
    while True:
        taste = _taste()
        if taste == "hoch":
            auswahl = (auswahl - 1) % len(eintraege)
            puffer = ""
        elif taste == "runter":
            auswahl = (auswahl + 1) % len(eintraege)
            puffer = ""
        elif taste == "enter":
            return auswahl
        elif taste in ("esc", "q"):
            return None
        elif taste.isdigit():
            puffer += taste
            if 1 <= int(puffer) <= len(eintraege):
                auswahl = int(puffer) - 1
            else:
                puffer = taste
                if 1 <= int(puffer) <= len(eintraege):
                    auswahl = int(puffer) - 1
        zeichnen()


def frage_ja(text: str, standard: bool = True) -> bool:
    hinweis = "[J/n]" if standard else "[j/N]"
    try:
        antwort = input(f("  " + text + " ", WEISS) + f(hinweis + " ", GRAU)).strip().lower()
    except EOFError:
        return standard
    if not antwort:
        return standard
    return antwort[0] in ("j", "y")


def diff_zeigen(alt: str, neu: str, pfad: str, max_zeilen: int = 60) -> tuple[int, int]:
    import difflib

    zeilen = list(difflib.unified_diff(alt.splitlines(), neu.splitlines(), lineterm="", n=2))
    plus = sum(1 for z in zeilen if z.startswith("+") and not z.startswith("+++"))
    minus = sum(1 for z in zeilen if z.startswith("-") and not z.startswith("---"))
    gezeigt = 0
    for zeile in zeilen[2:]:
        if gezeigt >= max_zeilen:
            sag("    " + f(f"… {len(zeilen) - 2 - gezeigt} weitere Zeilen", GRAU))
            break
        if zeile.startswith("@@"):
            sag("    " + f(zeile, BLAU, MATT))
        elif zeile.startswith("+"):
            sag("    " + f(zeile, GRUEN, HG_GRUEN))
        elif zeile.startswith("-"):
            sag("    " + f(zeile, ROT, HG_ROT))
        else:
            sag("    " + f(zeile, GRAU))
        gezeigt += 1
    return plus, minus
