from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.services.browser.elemente import (
    BESCHREIBUNG_JS,
    ELEMENTE_JS,
    MAX_ELEMENTE,
    SEITE_JS,
    TEXT_LIMIT,
    ZUSTIMMUNG_JS,
)
from app.services.browser.protokoll import notieren
from app.core.fehler import leise

BROWSER_DIR = DATA_DIR / "browser"
PROFIL_DIR = BROWSER_DIR / "profil"
AKTION_TIMEOUT_MS = 20000
AUFRUF_TIMEOUT_S = 70
LADE_TIMEOUT_MS = 25000
KENNUNG = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_ID_RE = re.compile(r"^e\d+$")
_SELEKTOR_RE = re.compile(r"^([#.\[/]|xpath=|css=|text=|//)|[>:=\"']")


class BrowserFehler(RuntimeError):
    pass


class ElementVeraltet(BrowserFehler):
    pass


def freundlich(exc: Exception) -> str:
    text = str(exc)
    art = type(exc).__name__
    if "Timeout" in art or "Timeout" in text[:120]:
        return (
            "Zeitueberschreitung - die Seite oder das Element hat nicht reagiert. "
            "Lies die Seite neu und versuch einen anderen Weg."
        )
    if "net::ERR_NAME_NOT_RESOLVED" in text:
        return "Die Adresse wurde nicht gefunden - stimmt die URL?"
    if "net::ERR_INTERNET_DISCONNECTED" in text:
        return "Keine Internetverbindung."
    if "net::ERR_CONNECTION" in text:
        return "Die Seite ist nicht erreichbar."
    if "Executable doesn't exist" in text:
        return "Chromium ist noch nicht installiert."
    if "Target page, context or browser has been closed" in text:
        return "Der Tab wurde geschlossen. Oeffne die Seite noch einmal."
    if "intercepts pointer events" in text or "not visible" in text:
        return (
            "Das Element ist verdeckt (z.B. durch ein Popup oder einen "
            "Cookie-Hinweis). Lies die Seite neu und raeum den Dialog zuerst weg."
        )
    return (text.splitlines()[0] if text else "Unbekannter Fehler")[:300]


class BrowserManager:
    def __init__(self, sitzung: str = "standard") -> None:
        self.sitzung = sitzung
        self._queue: Queue = Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._installiert = False
        self._installiere = False
        self._install_fehler = ""
        self._offen = False
        self._nur_ram = False
        self._fluechtig: Path | None = None

    @property
    def offen(self) -> bool:
        return self._offen

    def _thread_sichern(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._schleife, daemon=True)
                self._thread.start()

    def _chromium_installieren(self) -> None:
        with self._lock:
            if self._installiere:
                return
            self._installiere = True
        try:
            ergebnis = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=1200,
            )
            with self._lock:
                self._installiert = ergebnis.returncode == 0
                self._install_fehler = (
                    "" if ergebnis.returncode == 0 else ergebnis.stderr[-400:]
                )
        except Exception as exc:
            with self._lock:
                self._install_fehler = str(exc)
        finally:
            with self._lock:
                self._installiere = False

    def _einstellungen(self) -> dict:
        try:
            from app.services.settings_service import get_settings_service

            werte = get_settings_service().get()
        except Exception:
            werte = {}
        speicher = str(werte.get("browser_speicher", "") or "").strip().lower()
        if speicher not in ("ram", "festplatte"):
            speicher = "festplatte" if werte.get("browser_persistent", True) else "ram"
        return {
            "sichtbar": bool(werte.get("browser_sichtbar", True)),
            "speicher": speicher,
            "persistent": speicher == "festplatte",
        }

    def _ablage(self, nur_ram: bool):
        if not nur_ram:
            BROWSER_DIR.mkdir(parents=True, exist_ok=True)
            return BROWSER_DIR
        if self._fluechtig is None:
            self._fluechtig = Path(
                tempfile.mkdtemp(prefix=f"jon-browser-{self.sitzung}-")
            )
        return self._fluechtig

    def _fluechtig_raeumen(self) -> None:
        if self._fluechtig is None:
            return
        try:
            shutil.rmtree(self._fluechtig, ignore_errors=True)
        except Exception as _fehler:
            leise(_fehler, "services/browser/manager")
        self._fluechtig = None

    def _schleife(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            while True:
                try:
                    _op, _args, aus = self._queue.get(timeout=60)
                except Empty:
                    return
                aus.put(
                    (
                        "err",
                        BrowserFehler(
                            "Playwright ist nicht installiert "
                            f"(pip install playwright): {exc}"
                        ),
                    )
                )

        pw = sync_playwright().start()
        sitzung: dict[str, Any] = {
            "browser": None,
            "context": None,
            "tabs": {},
            "aktiv": "",
            "zaehler": 0,
        }

        def tab_registrieren(seite) -> str:
            for kennung, vorhanden in sitzung["tabs"].items():
                if vorhanden is seite:
                    return kennung
            sitzung["zaehler"] += 1
            kennung = f"t{sitzung['zaehler']}"
            sitzung["tabs"][kennung] = seite
            try:
                seite.set_default_timeout(AKTION_TIMEOUT_MS)
            except Exception as _fehler:
                leise(_fehler, "services/browser/manager")
            return kennung

        def aufraeumen() -> None:
            for kennung in list(sitzung["tabs"]):
                seite = sitzung["tabs"][kennung]
                try:
                    if seite.is_closed():
                        sitzung["tabs"].pop(kennung, None)
                except Exception:
                    sitzung["tabs"].pop(kennung, None)
            if sitzung["aktiv"] not in sitzung["tabs"]:
                sitzung["aktiv"] = next(iter(sitzung["tabs"]), "")

        def context():
            if sitzung["context"] is not None:
                try:
                    sitzung["context"].pages
                    return sitzung["context"]
                except Exception:
                    sitzung["context"] = None
                    sitzung["browser"] = None
                    sitzung["tabs"] = {}
                    sitzung["aktiv"] = ""
            wahl = self._einstellungen()
            argumente = ["--disable-blink-features=AutomationControlled"]
            if wahl["persistent"]:
                profil = PROFIL_DIR if self.sitzung == "standard" else (
                    PROFIL_DIR.parent / f"profil-{self.sitzung}"
                )
                profil.mkdir(parents=True, exist_ok=True)
                ctx = pw.chromium.launch_persistent_context(
                    str(profil),
                    headless=not wahl["sichtbar"],
                    args=argumente,
                    locale="de-DE",
                    user_agent=KENNUNG,
                    viewport={"width": 1280, "height": 900},
                )
                sitzung["browser"] = None
            else:
                argumente += [
                    "--disk-cache-size=1",
                    "--media-cache-size=1",
                    "--disable-application-cache",
                ]
                browser = pw.chromium.launch(
                    headless=not wahl["sichtbar"], args=argumente
                )
                ctx = browser.new_context(
                    locale="de-DE",
                    user_agent=KENNUNG,
                    viewport={"width": 1280, "height": 900},
                )
                sitzung["browser"] = browser
            self._nur_ram = not wahl["persistent"]
            ctx.set_default_timeout(AKTION_TIMEOUT_MS)
            ctx.on("page", lambda seite: tab_registrieren(seite))
            sitzung["context"] = ctx
            for seite in list(ctx.pages):
                if seite not in sitzung["tabs"].values():
                    kennung = tab_registrieren(seite)
                    sitzung["aktiv"] = sitzung["aktiv"] or kennung
            self._offen = True
            notieren(
                "BROWSER START",
                f"sichtbar={wahl['sichtbar']} speicher={wahl['speicher']}",
            )
            return ctx

        def seite():
            ctx = context()
            aufraeumen()
            if not sitzung["tabs"]:
                neu = ctx.new_page()
                kennung = (
                    next(
                        (k for k, v in sitzung["tabs"].items() if v is neu),
                        "",
                    )
                    or tab_registrieren(neu)
                )
                sitzung["aktiv"] = kennung
            if sitzung["aktiv"] not in sitzung["tabs"]:
                sitzung["aktiv"] = next(iter(sitzung["tabs"]))
            return sitzung["tabs"][sitzung["aktiv"]]

        def tabliste() -> list[dict]:
            aufraeumen()
            liste = []
            for kennung, s in sitzung["tabs"].items():
                try:
                    liste.append(
                        {
                            "tab": kennung,
                            "titel": (s.title() or "")[:80],
                            "url": s.url,
                            "aktiv": kennung == sitzung["aktiv"],
                        }
                    )
                except Exception:
                    continue
            return liste

        def ziel(p, kennung: str):
            wert = str(kennung or "").strip()
            if not wert:
                raise BrowserFehler("Es wurde kein Element angegeben.")
            if _ID_RE.match(wert):
                loc = p.locator(f'[data-jon-el="{wert}"]').first
                try:
                    if loc.count() > 0:
                        return loc
                except Exception as _fehler:
                    leise(_fehler, "services/browser/manager")
                raise ElementVeraltet(
                    f"Die Element-ID {wert} gibt es auf dieser Seite nicht mehr. "
                    "Ruf browser_read auf und nimm eine aktuelle ID."
                )
            if _SELEKTOR_RE.search(wert):
                loc = p.locator(wert).first
                try:
                    if loc.count() > 0:
                        return loc
                except Exception as _fehler:
                    leise(_fehler, "services/browser/manager")
            for versuch in (
                lambda: p.get_by_role("button", name=wert).first,
                lambda: p.get_by_role("link", name=wert).first,
                lambda: p.get_by_label(wert).first,
                lambda: p.get_by_placeholder(wert).first,
                lambda: p.get_by_text(wert, exact=False).first,
            ):
                try:
                    loc = versuch()
                    if loc.count() > 0:
                        return loc
                except Exception:
                    continue
            raise ElementVeraltet(
                f"Kein Element gefunden fuer '{wert}'. Ruf browser_read auf und "
                "nimm eine Element-ID aus interaktive_elemente."
            )

        def schnappschuss(p, mit_text: bool = True, grenze: int = MAX_ELEMENTE) -> dict:
            daten: dict[str, Any] = {"url": p.url, "titel": "", "laden": "bereit"}
            try:
                daten["titel"] = p.title()
            except Exception as _fehler:
                leise(_fehler, "services/browser/manager")
            try:
                seiteninfo = p.evaluate(SEITE_JS, TEXT_LIMIT if mit_text else 400)
            except Exception:
                seiteninfo = {}
            if isinstance(seiteninfo, dict):
                daten["beschreibung"] = seiteninfo.get("beschreibung", "")
                daten["ueberschriften"] = seiteninfo.get("ueberschriften", [])
                if mit_text:
                    text = str(seiteninfo.get("text", ""))
                    daten["seitentext"] = re.sub(r"\n{3,}", "\n\n", text).strip()
                daten["dialoge"] = seiteninfo.get("dialoge", 0)
                daten["zustimmung_moeglich"] = seiteninfo.get(
                    "zustimmung_moeglich", False
                )
                if seiteninfo.get("titel") and not daten["titel"]:
                    daten["titel"] = seiteninfo["titel"]
            try:
                daten["interaktive_elemente"] = p.evaluate(ELEMENTE_JS, grenze)
            except Exception:
                daten["interaktive_elemente"] = []
            daten["tab"] = sitzung["aktiv"]
            daten["tabs"] = tabliste()
            return daten

        def geladen(p) -> None:
            try:
                p.wait_for_load_state("domcontentloaded", timeout=LADE_TIMEOUT_MS)
            except Exception as _fehler:
                leise(_fehler, "services/browser/manager")

        while True:
            op, args, aus = self._queue.get()
            if op == "__quit__":
                break
            try:
                if op == "goto":
                    p = seite()
                    url = str(args.get("url", "")).strip()
                    if url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
                        url = "https://" + url
                    p.goto(url, wait_until="domcontentloaded", timeout=LADE_TIMEOUT_MS)
                    aus.put(("ok", schnappschuss(p)))
                elif op == "read":
                    p = seite()
                    aus.put(("ok", schnappschuss(p)))
                elif op == "beschreiben":
                    p = seite()
                    try:
                        loc = ziel(p, str(args.get("element", "")))
                        info = loc.evaluate(BESCHREIBUNG_JS)
                        info["gefunden"] = True
                    except ElementVeraltet as exc:
                        info = {"gefunden": False, "fehler": str(exc)}
                    aus.put(("ok", info))
                elif op == "click":
                    p = seite()
                    loc = ziel(p, str(args.get("element", "")))
                    try:
                        loc.scroll_into_view_if_needed(timeout=4000)
                    except Exception as _fehler:
                        leise(_fehler, "services/browser/manager")
                    loc.click(timeout=AKTION_TIMEOUT_MS)
                    geladen(p)
                    p = seite()
                    daten = schnappschuss(p, mit_text=bool(args.get("mit_text", True)))
                    daten["geklickt"] = args.get("element")
                    aus.put(("ok", daten))
                elif op == "fill":
                    p = seite()
                    loc = ziel(p, str(args.get("element", "")))
                    loc.fill(str(args.get("text", "")))
                    if args.get("enter"):
                        loc.press("Enter")
                        geladen(p)
                    p = seite()
                    daten = schnappschuss(p, mit_text=bool(args.get("enter")))
                    daten["ausgefuellt"] = args.get("element")
                    aus.put(("ok", daten))
                elif op == "press":
                    p = seite()
                    taste = str(args.get("taste", "Enter")) or "Enter"
                    element = str(args.get("element", "")).strip()
                    if element:
                        ziel(p, element).press(taste)
                    else:
                        p.keyboard.press(taste)
                    geladen(p)
                    daten = schnappschuss(p, mit_text=False)
                    daten["taste"] = taste
                    aus.put(("ok", daten))
                elif op == "select":
                    p = seite()
                    loc = ziel(p, str(args.get("element", "")))
                    wert = str(args.get("option", ""))
                    try:
                        loc.select_option(label=wert)
                    except Exception:
                        loc.select_option(wert)
                    daten = schnappschuss(p, mit_text=False)
                    daten["gewaehlt"] = wert
                    aus.put(("ok", daten))
                elif op == "scroll":
                    p = seite()
                    richtung = str(args.get("richtung", "runter")).lower()
                    menge = int(args.get("menge", 600) or 600)
                    faktor = -1 if richtung in ("hoch", "up", "oben") else 1
                    if richtung in ("anfang", "top"):
                        p.evaluate("() => window.scrollTo(0, 0)")
                    elif richtung in ("ende", "bottom", "unten"):
                        p.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                    else:
                        p.mouse.wheel(0, faktor * menge)
                    p.wait_for_timeout(400)
                    daten = schnappschuss(p, mit_text=bool(args.get("mit_text", True)))
                    daten["gescrollt"] = richtung
                    aus.put(("ok", daten))
                elif op == "wait_element":
                    p = seite()
                    grenze = int(args.get("timeout", 10000) or 10000)
                    wert = str(args.get("element", "")).strip()
                    if _ID_RE.match(wert):
                        p.wait_for_selector(
                            f'[data-jon-el="{wert}"]', timeout=grenze
                        )
                    elif wert:
                        p.get_by_text(wert, exact=False).first.wait_for(timeout=grenze)
                    else:
                        p.wait_for_load_state("networkidle", timeout=grenze)
                    aus.put(("ok", schnappschuss(p)))
                elif op == "wait_navigation":
                    p = seite()
                    try:
                        p.wait_for_load_state(
                            "networkidle",
                            timeout=int(args.get("timeout", 12000) or 12000),
                        )
                    except Exception as _fehler:
                        leise(_fehler, "services/browser/manager")
                    aus.put(("ok", schnappschuss(p)))
                elif op == "back":
                    p = seite()
                    p.go_back(wait_until="domcontentloaded", timeout=LADE_TIMEOUT_MS)
                    aus.put(("ok", schnappschuss(p)))
                elif op == "forward":
                    p = seite()
                    p.go_forward(wait_until="domcontentloaded", timeout=LADE_TIMEOUT_MS)
                    aus.put(("ok", schnappschuss(p)))
                elif op == "reload":
                    p = seite()
                    p.reload(wait_until="domcontentloaded", timeout=LADE_TIMEOUT_MS)
                    aus.put(("ok", schnappschuss(p)))
                elif op == "tab_new":
                    ctx = context()
                    neu = ctx.new_page()
                    kennung = next(
                        (k for k, v in sitzung["tabs"].items() if v is neu), ""
                    ) or tab_registrieren(neu)
                    sitzung["aktiv"] = kennung
                    url = str(args.get("url", "")).strip()
                    if url:
                        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
                            url = "https://" + url
                        neu.goto(
                            url, wait_until="domcontentloaded", timeout=LADE_TIMEOUT_MS
                        )
                    aus.put(("ok", schnappschuss(neu)))
                elif op == "tab_switch":
                    aufraeumen()
                    kennung = str(args.get("tab", "")).strip()
                    if kennung not in sitzung["tabs"]:
                        offen = ", ".join(sitzung["tabs"]) or "keine"
                        raise BrowserFehler(
                            f"Tab {kennung} gibt es nicht. Offene Tabs: {offen}"
                        )
                    sitzung["aktiv"] = kennung
                    p = sitzung["tabs"][kennung]
                    try:
                        p.bring_to_front()
                    except Exception as _fehler:
                        leise(_fehler, "services/browser/manager")
                    aus.put(("ok", schnappschuss(p)))
                elif op == "tab_close":
                    aufraeumen()
                    kennung = str(args.get("tab", "")).strip() or sitzung["aktiv"]
                    p = sitzung["tabs"].pop(kennung, None)
                    if p is not None:
                        try:
                            p.close()
                        except Exception as _fehler:
                            leise(_fehler, "services/browser/manager")
                    sitzung["aktiv"] = next(iter(sitzung["tabs"]), "")
                    if sitzung["aktiv"]:
                        aus.put(("ok", schnappschuss(sitzung["tabs"][sitzung["aktiv"]])))
                    else:
                        aus.put(("ok", {"url": "", "titel": "", "tabs": [], "tab": ""}))
                elif op == "upload":
                    p = seite()
                    loc = ziel(p, str(args.get("element", "")))
                    pfade = args.get("pfade") or [args.get("pfad", "")]
                    loc.set_input_files([str(x) for x in pfade if str(x).strip()])
                    daten = schnappschuss(p, mit_text=False)
                    daten["hochgeladen"] = pfade
                    aus.put(("ok", daten))
                elif op == "screenshot":
                    p = seite()
                    ordner = self._ablage(self._nur_ram)
                    datei = (
                        ordner
                        / f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
                    )
                    p.screenshot(path=str(datei), full_page=bool(args.get("ganz")))
                    aus.put(
                        (
                            "ok",
                            {
                                "datei": str(datei),
                                "url": p.url,
                                "titel": p.title(),
                                "tab": sitzung["aktiv"],
                            },
                        )
                    )
                elif op == "zustimmung":
                    p = seite()
                    try:
                        info = p.evaluate(ZUSTIMMUNG_JS)
                    except Exception:
                        info = None
                    aus.put(("ok", {"dialog": info}))
                elif op == "status":
                    if sitzung["context"] is None:
                        aus.put(("ok", {"aktiv": False, "tabs": []}))
                    else:
                        p = seite()
                        daten = schnappschuss(p, mit_text=False, grenze=20)
                        daten["aktiv"] = True
                        aus.put(("ok", daten))
                elif op == "close":
                    for s in list(sitzung["tabs"].values()):
                        try:
                            s.close()
                        except Exception as _fehler:
                            leise(_fehler, "services/browser/manager")
                    if sitzung["context"] is not None:
                        try:
                            sitzung["context"].close()
                        except Exception as _fehler:
                            leise(_fehler, "services/browser/manager")
                    if sitzung["browser"] is not None:
                        try:
                            sitzung["browser"].close()
                        except Exception as _fehler:
                            leise(_fehler, "services/browser/manager")
                    sitzung["context"] = None
                    sitzung["browser"] = None
                    sitzung["tabs"] = {}
                    sitzung["aktiv"] = ""
                    self._offen = False
                    self._fluechtig_raeumen()
                    notieren("BROWSER ZU", "Sitzung beendet")
                    aus.put(("ok", {"geschlossen": True}))
                else:
                    aus.put(("err", BrowserFehler(f"Unbekannte Browser-Aktion: {op}")))
            except Exception as exc:
                aus.put(("err", exc))

    def aufrufen(self, op: str, args: dict | None = None) -> dict:
        self._thread_sichern()
        aus: Queue = Queue()
        self._queue.put((op, dict(args or {}), aus))
        try:
            status, ergebnis = aus.get(timeout=AUFRUF_TIMEOUT_S)
        except Empty:
            return {
                "ok": False,
                "fehler": "Zeitueberschreitung - der Browser reagiert nicht.",
            }
        if status == "ok":
            ergebnis = dict(ergebnis)
            ergebnis["ok"] = True
            return ergebnis
        meldung = freundlich(ergebnis)
        if "Chromium ist noch nicht installiert" in meldung:
            return {"ok": False, "fehler": self._chromium_hinweis()}
        return {
            "ok": False,
            "fehler": meldung,
            "veraltet": isinstance(ergebnis, ElementVeraltet),
        }

    def _chromium_hinweis(self) -> str:
        with self._lock:
            laeuft = self._installiere
            fehler = self._install_fehler
        if not laeuft:
            threading.Thread(target=self._chromium_installieren, daemon=True).start()
            return (
                "Chromium wird gerade zum ersten Mal installiert (einmalig, dauert "
                "ein paar Minuten). Sag dem Nutzer Bescheid und versuch es danach "
                "noch einmal."
            )
        if fehler:
            return f"Chromium-Installation fehlgeschlagen: {fehler}"
        return "Chromium wird noch installiert - bitte gleich noch einmal versuchen."

    def schliessen(self) -> dict:
        if self._thread is None or not self._thread.is_alive():
            return {"ok": True, "geschlossen": True}
        return self.aufrufen("close")


_manager: dict[str, BrowserManager] = {}
_manager_lock = threading.Lock()


def get_manager(sitzung: str = ""):
    from app.services.browser import privatbruecke
    from app.services.browser.sitzung import aktuell

    schluessel = sitzung or aktuell()
    if privatbruecke.aktiv():
        return privatbruecke.manager(schluessel)
    with _manager_lock:
        if schluessel not in _manager:
            _manager[schluessel] = BrowserManager(schluessel)
        return _manager[schluessel]


def alle_manager() -> dict[str, BrowserManager]:
    with _manager_lock:
        return dict(_manager)
