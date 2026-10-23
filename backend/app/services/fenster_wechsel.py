from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

from app.core.fehler import leise

BROWSER = {"chrome", "msedge", "firefox", "brave", "opera", "vivaldi", "arc"}
CHROMIUM = {"chrome", "msedge", "brave", "vivaldi", "opera", "arc"}
MAX_TABS = 40
STARK = r"(?:wechsle|wechsel|wechseln|spring|springe|switch|schalt(?:e)?\s+um|schalt(?:e)?)"
SCHWACH = r"(?:geh|gehe|zeig|zeige|hol|hole|bring|bringe|oeffne|öffne|mach|aktivier(?:e)?)"
NOMEN = r"(?:browser-?tab|tab|reiter|fenster|programm|app)"
FUELL = r"(?:bitte|mal|doch|schnell|jetzt|jon|den|das|die|dem|der|zum|zur|zu+h?|zuu+|in|ins|auf|aufs|nach|to|mir|mich|wieder|zurueck|zurück|nochmal|mit|von|vom|namens|titel|heisst|heißt|wo|the|lauft|läuft|laeuft|ist|offen|geoeffnet|geöffnet|spielt|gerade)"
NICHT = {"modell", "model", "anbieter", "provider", "sprache", "stimme", "thema", "theme", "design", "persona", "modus", "ordner", "projekt", "chat", "gespraech", "gespräch", "konto", "nutzer", "dunkelmodus", "hellmodus", "dark mode", "light mode", "ki"}
WUNSCH_STARK = re.compile(rf"^\s*(?:hey\s+)?(?:jon[,:]?\s+)?(?:kannst du\s+)?(?:bitte\s+)?{STARK}\b(?P<rest>.*)$", re.I)
WUNSCH_SCHWACH = re.compile(rf"^\s*(?:hey\s+)?(?:jon[,:]?\s+)?(?:kannst du\s+)?(?:bitte\s+)?{SCHWACH}\b(?P<rest>.*\b{NOMEN}\b.*)$", re.I)
WUNSCH_ENDE = re.compile(rf"^\s*(?:hey\s+)?(?:jon[,:]?\s+)?(?:kannst du\s+|kannst du mal\s+)?(?:bitte\s+)?(?P<rest>(?:zu|zum|zur|auf|in)\s+.+?)\s+(?:wechseln|springen|umschalten|switchen)\b.*$", re.I)


def wunsch(text: str) -> tuple[str, bool] | None:
    roh = " ".join(str(text or "").split())
    if not roh or len(roh) > 120:
        return None
    treffer = WUNSCH_STARK.match(roh) or WUNSCH_SCHWACH.match(roh) or WUNSCH_ENDE.match(roh)
    if not treffer:
        return None
    rest = treffer.group("rest")
    tab = bool(re.search(r"\b(?:browser-?tab|tab|reiter|browser)\b", rest, re.I))
    rest = re.sub(rf"\b{NOMEN}\b", " ", rest, flags=re.I)
    rest = re.sub(r"\b(?:um|kannst du|bitte|danke|wechseln|springen|aufmachen|anzeigen|zeigen|holen)\b", " ", rest, flags=re.I)
    rest = re.sub(r"[?!.,;:\"'„“”]+", " ", rest)
    woerter = rest.split()
    while woerter and re.fullmatch(FUELL, woerter[0], re.I):
        woerter.pop(0)
    while woerter and re.fullmatch(FUELL, woerter[-1], re.I):
        woerter.pop()
    ziel = " ".join(woerter).strip()
    if not ziel or len(woerter) > 5 or _sauber(ziel) in NICHT or _sauber(woerter[0]) in NICHT:
        return None
    return ziel, tab


def _sauber(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _programm(hwnd: int) -> str:
    try:
        import ctypes
        import win32process

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        griff = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not griff:
            return ""
        try:
            puffer = ctypes.create_unicode_buffer(1024)
            laenge = ctypes.c_ulong(1024)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(griff, 0, puffer, ctypes.byref(laenge)):
                return Path(puffer.value).stem.lower()
        finally:
            ctypes.windll.kernel32.CloseHandle(griff)
    except Exception as fehler:
        leise(fehler, "services/fenster_wechsel")
    return ""


def fenster() -> list[dict]:
    if os.name != "nt":
        return []
    import win32gui

    gefunden: list[dict] = []

    def sammeln(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        titel = win32gui.GetWindowText(hwnd).strip()
        if not titel or titel in ("Program Manager", "Default IME", "MSCTFIME UI"):
            return
        gefunden.append({"hwnd": hwnd, "titel": titel, "programm": _programm(hwnd)})

    win32gui.EnumWindows(sammeln, None)
    return gefunden


def _punkte(ziel: str, eintrag: dict) -> int:
    suche = _sauber(ziel)
    if not suche:
        return 0
    titel = _sauber(eintrag["titel"])
    programm = _sauber(eintrag.get("programm", ""))
    if suche == programm or titel == suche:
        return 100
    if re.search(rf"\b{re.escape(suche)}\b", titel):
        return 80 if titel.startswith(suche) else 70
    if suche in programm:
        return 60
    if suche in titel:
        return 50
    woerter = suche.split()
    if len(woerter) > 1 and all(w in titel for w in woerter):
        return 40
    return 0


def _gekoppelt_vorholen(hwnd: int) -> None:
    import ctypes

    import win32gui
    import win32process

    user32 = ctypes.windll.user32
    eigener = ctypes.windll.kernel32.GetCurrentThreadId()
    vorne = win32gui.GetForegroundWindow()
    fremde = {t for t in (win32process.GetWindowThreadProcessId(vorne)[0] if vorne else 0, win32process.GetWindowThreadProcessId(hwnd)[0]) if t and t != eigener}
    gekoppelt = [t for t in fremde if user32.AttachThreadInput(eigener, t, True)]
    try:
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        for t in gekoppelt:
            user32.AttachThreadInput(eigener, t, False)


def _vordergrund(hwnd: int) -> bool:
    import ctypes

    import win32con
    import win32gui

    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        try:
            import pyautogui

            pyautogui.press("alt")
        except Exception as fehler:
            leise(fehler, "services/fenster_wechsel")
        versuche = (
            lambda: win32gui.SetForegroundWindow(hwnd),
            lambda: _gekoppelt_vorholen(hwnd),
            lambda: ctypes.windll.user32.SwitchToThisWindow(hwnd, True),
        )
        for versuch in versuche:
            try:
                versuch()
            except Exception as fehler:
                leise(fehler, "services/fenster_wechsel")
            time.sleep(0.25)
            if win32gui.GetForegroundWindow() == hwnd:
                return True
        return False
    except Exception as fehler:
        leise(fehler, "services/fenster_wechsel")
        return False


def _aktiver_titel() -> str:
    import win32gui

    return win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()


def _tab_suche_chromium(ziel: str) -> str:
    import pyautogui

    begriff = _sauber(ziel)
    if not begriff:
        return ""
    import win32gui

    vorher = win32gui.GetForegroundWindow()
    pyautogui.hotkey("ctrl", "shift", "a")
    time.sleep(0.55)
    if win32gui.GetForegroundWindow() == vorher:
        return ""
    pyautogui.write(begriff, interval=0.015)
    time.sleep(0.6)
    pyautogui.press("enter")
    time.sleep(0.4)
    titel = _aktiver_titel()
    if _punkte(ziel, {"titel": titel}) >= 50:
        return titel
    pyautogui.press("escape")
    time.sleep(0.15)
    return ""


def _tab_suchen(ziel: str, eintrag: dict) -> str:
    import pyautogui

    if not _vordergrund(eintrag["hwnd"]):
        return ""
    start = _aktiver_titel()
    if _punkte(ziel, {"titel": start}) >= 50:
        return start
    if eintrag.get("programm") in CHROMIUM:
        try:
            titel = _tab_suche_chromium(ziel)
            if titel:
                return titel
        except Exception as fehler:
            leise(fehler, "services/fenster_wechsel")
        start = _aktiver_titel()
    for _ in range(MAX_TABS):
        pyautogui.hotkey("ctrl", "tab")
        time.sleep(0.22)
        titel = _aktiver_titel()
        if _punkte(ziel, {"titel": titel}) >= 50:
            return titel
        if titel == start:
            break
    return ""


def _eigenes(eintrag: dict) -> bool:
    titel = eintrag["titel"].strip()
    if eintrag["programm"] == "jon":
        return True
    return eintrag["programm"] == "electron" and (titel in ("Jon", "Mini Jon", "Funke") or titel.startswith("Jon "))


def _tabs_durchsuchen(ziel: str, alle: list[dict]) -> dict | None:
    gesehen: set[str] = set()
    for eintrag in alle:
        if eintrag["programm"] not in BROWSER:
            continue
        titel = _tab_suchen(ziel, eintrag)
        if titel:
            return {"ok": True, "tab": _ohne_browser(titel), "programm": eintrag["programm"]}
        if eintrag["programm"] in CHROMIUM:
            gesehen.add(eintrag["programm"])
    return None


def _ohne_browser(titel: str) -> str:
    return re.sub(r"\s+[-–—]\s+(?:Google Chrome|Microsoft\u200b? Edge|Microsoft Edge|Brave|Mozilla Firefox|Opera|Vivaldi)(?:\s+[-–—].*)?$", "", titel).strip() or titel


def wechseln(ziel: str, tabs: bool = True, tab_zuerst: bool = False) -> dict:
    ziel = str(ziel or "").strip()
    if not ziel:
        return {"error": "Sag, wohin ich wechseln soll, z. B. 'Claude' oder 'YouTube'."}
    if os.name != "nt":
        if shutil.which("wmctrl"):
            ergebnis = subprocess.run(["wmctrl", "-a", ziel], capture_output=True, timeout=10)
            return {"ok": ergebnis.returncode == 0, "fenster": ziel} if ergebnis.returncode == 0 else {"error": f"Kein Fenster '{ziel}' gefunden."}
        return {"error": "Fensterwechsel braucht hier wmctrl."}
    alle = [f for f in fenster() if not _eigenes(f)]
    if tab_zuerst and ziel.isdigit() and 1 <= int(ziel) <= 9:
        for eintrag in alle:
            if eintrag["programm"] in BROWSER and _vordergrund(eintrag["hwnd"]):
                import pyautogui

                pyautogui.hotkey("ctrl", ziel)
                time.sleep(0.3)
                return {"ok": True, "tab": _ohne_browser(_aktiver_titel()), "programm": eintrag["programm"]}
    if tab_zuerst and tabs:
        for eintrag in alle:
            if eintrag["programm"] in BROWSER and _punkte(ziel, {"titel": eintrag["titel"]}) >= 50 and _vordergrund(eintrag["hwnd"]):
                return {"ok": True, "tab": _ohne_browser(eintrag["titel"]), "programm": eintrag["programm"]}
        gefunden = _tabs_durchsuchen(ziel, alle)
        if gefunden:
            return gefunden
    bewertet = sorted(((_punkte(ziel, f), f) for f in alle), key=lambda p: -p[0])
    if bewertet and bewertet[0][0] >= 50:
        treffer = bewertet[0][1]
        if _vordergrund(treffer["hwnd"]):
            return {"ok": True, "fenster": treffer["titel"], "programm": treffer["programm"]}
    if tabs and not tab_zuerst:
        gefunden = _tabs_durchsuchen(ziel, alle)
        if gefunden:
            return gefunden
    if bewertet and bewertet[0][0] >= 40 and _vordergrund(bewertet[0][1]["hwnd"]):
        return {"ok": True, "fenster": bewertet[0][1]["titel"]}
    return {
        "error": f"Kein Fenster und kein Browser-Tab mit '{ziel}' gefunden.",
        "offen": [f["titel"][:80] for f in alle[:20]],
    }
