from __future__ import annotations

import os
import re
import textwrap
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import Callable

from . import oberflaeche as ui
from .oberflaeche import GOLD, GRAU, GRUEN, ROT, WEISS, f

BTW = re.compile(r"^\s*/(?:btw|nebenbei)\b[\s:,-]*", re.IGNORECASE)
DANACH = re.compile(r"^\s*(?:danach|anschlie(?:ss|ß)end|nachher|als n(?:ae|ä)chstes|dann noch|after that|then)\b[\s,:-]*", re.IGNORECASE)


def ist_btw(text: str) -> bool:
    return bool(BTW.match(text or ""))


def frage_aus(text: str) -> str:
    return BTW.sub("", text or "", count=1).strip()


def auftrag_aus(text: str) -> str:
    roh = text.strip()
    return DANACH.sub("", roh, count=1).strip() or roh


class Nebenbei:
    def __init__(self, beantworten: Callable[[str], str]) -> None:
        self.beantworten = beantworten
        self.puffer = ""
        self.schlange: deque[str] = deque()
        self._stopp = threading.Event()
        self._halt = threading.Event()
        self._ruht = threading.Event()
        self._faden: threading.Thread | None = None
        self._tty_alt = None
        self._fragen: list[threading.Thread] = []

    @staticmethod
    def moeglich() -> bool:
        if os.environ.get("JON_HARNESS_OHNE_NEBENBEI"):
            return False
        try:
            return sys.stdin.isatty() and sys.stdout.isatty()
        except (AttributeError, ValueError):
            return False

    def anzeige(self) -> str:
        if self.puffer:
            return f(" › " + self.puffer[-40:], GOLD)
        return f(" · /btw fragt nebenbei", GRAU)

    @contextmanager
    def lauschen(self):
        if not self.moeglich():
            yield self
            return
        self._stopp.clear()
        self._halt.clear()
        self._ruht.clear()
        self._roh_an()
        ui.Kreisel.nebenbei = self.anzeige
        self._faden = threading.Thread(target=self._lauf, daemon=True)
        self._faden.start()
        try:
            yield self
        finally:
            self._stopp.set()
            if self._faden is not None:
                self._faden.join(timeout=1)
            self._faden = None
            ui.Kreisel.nebenbei = None
            self._roh_aus()
            if self.puffer.strip():
                self._zeile(self.puffer)
            self.puffer = ""
            for faden in self._fragen:
                faden.join(timeout=30)
            self._fragen = []

    @contextmanager
    def pause(self):
        if self._faden is None or self._halt.is_set():
            yield
            return
        self._halt.set()
        self._ruht.wait(0.6)
        self._roh_aus()
        try:
            yield
        finally:
            self._roh_an()
            self._ruht.clear()
            self._halt.clear()

    def naechste(self) -> str | None:
        return self.schlange.popleft() if self.schlange else None

    def _roh_an(self) -> None:
        if sys.platform == "win32":
            return
        try:
            import termios
            import tty

            griff = sys.stdin.fileno()
            self._tty_alt = termios.tcgetattr(griff)
            tty.setcbreak(griff)
        except Exception:
            self._tty_alt = None

    def _roh_aus(self) -> None:
        if sys.platform == "win32" or self._tty_alt is None:
            return
        try:
            import termios

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._tty_alt)
        except Exception:
            pass
        self._tty_alt = None

    def _zeichen(self) -> str | None:
        if sys.platform == "win32":
            import msvcrt

            if not msvcrt.kbhit():
                return None
            zeichen = msvcrt.getwch()
            if zeichen in ("\x00", "\xe0"):
                msvcrt.getwch()
                return ""
            return zeichen
        import select

        bereit, _, _ = select.select([sys.stdin], [], [], 0)
        if not bereit:
            return None
        daten = os.read(sys.stdin.fileno(), 4)
        if not daten:
            return None
        text = daten.decode("utf-8", "ignore")
        if text.startswith("\x1b"):
            return ""
        return text

    def _lauf(self) -> None:
        while not self._stopp.is_set():
            if self._halt.is_set():
                self._ruht.set()
                time.sleep(0.05)
                continue
            try:
                zeichen = self._zeichen()
            except Exception:
                return
            if zeichen is None:
                time.sleep(0.04)
                continue
            for taste in zeichen:
                if taste in ("\r", "\n"):
                    zeile, self.puffer = self.puffer, ""
                    if zeile.strip():
                        self._zeile(zeile)
                elif taste in ("\x08", "\x7f"):
                    self.puffer = self.puffer[:-1]
                elif taste == "\x1b":
                    self.puffer = ""
                elif taste == "\x15":
                    self.puffer = ""
                elif taste >= " ":
                    self.puffer += taste

    def _melden(self, text: str) -> None:
        with ui._ausgabe_lock:
            sys.stdout.write("\r\x1b[2K" + text + "\n")
            sys.stdout.flush()

    def _zeile(self, zeile: str) -> None:
        text = zeile.strip()
        if ist_btw(text):
            frage = frage_aus(text)
            if not frage:
                self._melden(f("  ✳ ", GOLD) + f("Schreib die Frage direkt dahinter, z. B. /btw wie weit bist du?", GRAU))
                return
            self._melden(f("  ✳ nebenbei: ", GOLD) + f(frage, WEISS))
            faden = threading.Thread(target=self._antworten, args=(frage,), daemon=True)
            self._fragen.append(faden)
            faden.start()
            return
        auftrag = text if text.startswith("/") else auftrag_aus(text)
        self.schlange.append(auftrag)
        self._melden(f("  ↳ ", GRUEN) + f("vorgemerkt für danach: ", GRAU) + f(auftrag[:160], WEISS))

    def _antworten(self, frage: str) -> None:
        try:
            antwort = self.beantworten(frage).strip() or "Dazu fällt mir gerade nichts ein."
        except Exception as fehler:
            self._melden(f("  ✳ ", GOLD) + f(f"Die Zwischenfrage ging nicht durch: {str(fehler)[:160]}", ROT))
            return
        zeilen = []
        for absatz in antwort.replace("**", "").splitlines():
            zeilen.extend(textwrap.wrap(absatz, max(30, min(ui.breite() - 8, 92))) if absatz.strip() else [""])
        with ui._ausgabe_lock:
            sys.stdout.write("\r\x1b[2K")
            sys.stdout.flush()
            ui.kasten("Nebenbei", [f(z, WEISS) for z in zeilen[:30]], GOLD)
