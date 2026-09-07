from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import threading
import time

_letzte_cpu: dict[str, float] = {}
_lock = threading.Lock()


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _speicher_windows() -> dict:
    stand = _MemoryStatusEx()
    stand.dwLength = ctypes.sizeof(_MemoryStatusEx)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stand))
    gesamt = int(stand.ullTotalPhys)
    frei = int(stand.ullAvailPhys)
    return {
        "gesamt": gesamt,
        "benutzt": gesamt - frei,
        "prozent": float(stand.dwMemoryLoad),
    }


def _speicher_linux() -> dict:
    werte: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as datei:
            for zeile in datei:
                teile = zeile.split(":")
                if len(teile) == 2:
                    werte[teile[0].strip()] = int(teile[1].strip().split()[0]) * 1024
    except OSError:
        return {"gesamt": 0, "benutzt": 0, "prozent": 0.0}
    gesamt = werte.get("MemTotal", 0)
    frei = werte.get("MemAvailable", werte.get("MemFree", 0))
    benutzt = max(0, gesamt - frei)
    prozent = round(benutzt / gesamt * 100, 1) if gesamt else 0.0
    return {"gesamt": gesamt, "benutzt": benutzt, "prozent": prozent}


def speicher() -> dict:
    if os.name == "nt":
        try:
            return _speicher_windows()
        except Exception:
            return {"gesamt": 0, "benutzt": 0, "prozent": 0.0}
    return _speicher_linux()


def _cpu_windows() -> tuple[float, float]:
    leerlauf = ctypes.c_ulonglong()
    kern = ctypes.c_ulonglong()
    nutzer = ctypes.c_ulonglong()
    ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(leerlauf), ctypes.byref(kern), ctypes.byref(nutzer)
    )
    gesamt = float(kern.value + nutzer.value)
    return float(leerlauf.value), gesamt


def _cpu_linux() -> tuple[float, float]:
    try:
        with open("/proc/stat", encoding="utf-8") as datei:
            teile = datei.readline().split()
    except OSError:
        return 0.0, 0.0
    zahlen = [float(wert) for wert in teile[1:] if wert.replace(".", "").isdigit()]
    if len(zahlen) < 4:
        return 0.0, 0.0
    return zahlen[3], sum(zahlen)


def cpu_last() -> float:
    messen = _cpu_windows if os.name == "nt" else _cpu_linux
    try:
        leerlauf, gesamt = messen()
    except Exception:
        return 0.0
    with _lock:
        vorher_leerlauf = _letzte_cpu.get("leerlauf", 0.0)
        vorher_gesamt = _letzte_cpu.get("gesamt", 0.0)
        _letzte_cpu["leerlauf"] = leerlauf
        _letzte_cpu["gesamt"] = gesamt
    if not vorher_gesamt:
        time.sleep(0.2)
        try:
            leerlauf2, gesamt2 = messen()
        except Exception:
            return 0.0
        with _lock:
            _letzte_cpu["leerlauf"] = leerlauf2
            _letzte_cpu["gesamt"] = gesamt2
        vorher_leerlauf, vorher_gesamt = leerlauf, gesamt
        leerlauf, gesamt = leerlauf2, gesamt2
    spanne = gesamt - vorher_gesamt
    if spanne <= 0:
        return 0.0
    frei = (leerlauf - vorher_leerlauf) / spanne
    return round(max(0.0, min(1.0, 1.0 - frei)) * 100, 1)


def grafik() -> dict | None:
    pfad = shutil.which("nvidia-smi")
    if not pfad:
        return None
    try:
        ergebnis = subprocess.run(
            [
                pfad,
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=6,
        )
    except Exception:
        return None
    zeile = (ergebnis.stdout or "").strip().splitlines()
    if not zeile:
        return None
    teile = [wert.strip() for wert in zeile[0].split(",")]
    if len(teile) < 4:
        return None
    try:
        return {
            "name": teile[0],
            "prozent": float(teile[1]),
            "benutzt": int(float(teile[2])) * 1024 * 1024,
            "gesamt": int(float(teile[3])) * 1024 * 1024,
        }
    except ValueError:
        return None


def uebersicht() -> dict:
    from app.core.config import get_settings
    from app.core.logbook import since_boot

    ram = speicher()
    gpu = grafik()
    platte = shutil.disk_usage(os.path.expanduser("~"))
    return {
        "name": platform.node(),
        "system": f"{platform.system()} {platform.release()}",
        "kerne": os.cpu_count() or 0,
        "cpu": cpu_last(),
        "ram": ram,
        "gpu": gpu,
        "platte": {
            "gesamt": platte.total,
            "benutzt": platte.used,
            "prozent": round(platte.used / platte.total * 100, 1) if platte.total else 0.0,
        },
        "laufzeit": round(since_boot(), 1),
        "version": get_settings().app_version,
    }
