from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

from app.core.fehler import leise

BROWSER = {"chrome", "msedge", "firefox", "brave", "opera", "vivaldi", "arc", "jon"}
MAX_TABS = 40


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


def _vordergrund(hwnd: int) -> bool:
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
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.25)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception as fehler:
        leise(fehler, "services/fenster_wechsel")
        return False


def _aktiver_titel() -> str:
    import win32gui

    return win32gui.GetWindowText(win32gui.GetForegroundWindow()).strip()


def _tab_suchen(ziel: str, eintrag: dict) -> str:
    import pyautogui

    if not _vordergrund(eintrag["hwnd"]):
        return ""
    start = _aktiver_titel()
    if _punkte(ziel, {"titel": start}) >= 50:
        return start
    for _ in range(MAX_TABS):
        pyautogui.hotkey("ctrl", "tab")
        time.sleep(0.22)
        titel = _aktiver_titel()
        if _punkte(ziel, {"titel": titel}) >= 50:
            return titel
        if titel == start:
            break
    return ""


def wechseln(ziel: str, tabs: bool = True) -> dict:
    ziel = str(ziel or "").strip()
    if not ziel:
        return {"error": "Sag, wohin ich wechseln soll, z. B. 'Claude' oder 'YouTube'."}
    if os.name != "nt":
        if shutil.which("wmctrl"):
            ergebnis = subprocess.run(["wmctrl", "-a", ziel], capture_output=True, timeout=10)
            return {"ok": ergebnis.returncode == 0, "fenster": ziel} if ergebnis.returncode == 0 else {"error": f"Kein Fenster '{ziel}' gefunden."}
        return {"error": "Fensterwechsel braucht hier wmctrl."}
    alle = fenster()
    bewertet = sorted(((_punkte(ziel, f), f) for f in alle), key=lambda p: -p[0])
    if bewertet and bewertet[0][0] >= 50:
        treffer = bewertet[0][1]
        if _vordergrund(treffer["hwnd"]):
            return {"ok": True, "fenster": treffer["titel"], "programm": treffer["programm"]}
    if tabs:
        for eintrag in alle:
            if eintrag["programm"] in BROWSER:
                titel = _tab_suchen(ziel, eintrag)
                if titel:
                    return {"ok": True, "tab": titel, "programm": eintrag["programm"]}
    if bewertet and bewertet[0][0] >= 40 and _vordergrund(bewertet[0][1]["hwnd"]):
        return {"ok": True, "fenster": bewertet[0][1]["titel"]}
    return {
        "error": f"Kein Fenster und kein Browser-Tab mit '{ziel}' gefunden.",
        "offen": [f["titel"][:80] for f in alle[:20]],
    }
