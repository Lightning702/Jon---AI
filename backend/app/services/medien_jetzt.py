from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app.core.fehler import leise

SKRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$warten = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Erwarten($vorgang, [Type]$typ) { $aufgabe = $warten.MakeGenericMethod($typ).Invoke($null, @($vorgang)); $aufgabe.Wait(-1) | Out-Null; $aufgabe.Result }
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime] | Out-Null
$verwalter = Erwarten ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$liste = @()
foreach ($sitzung in $verwalter.GetSessions()) {
  try {
    $daten = Erwarten ($sitzung.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
    $info = $sitzung.GetPlaybackInfo()
    $liste += [pscustomobject]@{ app = $sitzung.SourceAppUserModelId; titel = $daten.Title; kuenstler = $daten.Artist; album = $daten.AlbumTitle; status = "$($info.PlaybackStatus)" }
  } catch {}
}
ConvertTo-Json -InputObject @($liste) -Compress
"""

BROWSER = re.compile(r"\s[-–—]\s(Google Chrome|Microsoft​? Edge|Mozilla Firefox|Brave|Opera|Vivaldi)$", re.I)
MEDIEN_FENSTER = re.compile(r"(youtube|spotify|soundcloud|deezer|apple music|tidal|amazon music|twitch)", re.I)


def _windows_sitzungen() -> list[dict]:
    with tempfile.TemporaryDirectory() as ordner:
        datei = Path(ordner) / "medien.ps1"
        datei.write_text(SKRIPT, encoding="utf-8-sig")
        ergebnis = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(datei)],
            capture_output=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    roh = ergebnis.stdout.decode("utf-8", errors="replace").strip()
    if not roh:
        return []
    daten = json.loads(roh)
    return [d for d in (daten if isinstance(daten, list) else [daten]) if isinstance(d, dict) and (d.get("titel") or d.get("kuenstler"))]


def _linux_sitzungen() -> list[dict]:
    if not shutil.which("playerctl"):
        return []
    ergebnis = subprocess.run(
        ["playerctl", "-a", "metadata", "--format", "{{playerName}}\t{{title}}\t{{artist}}\t{{album}}\t{{status}}"],
        capture_output=True, text=True, timeout=10,
    )
    liste = []
    for zeile in ergebnis.stdout.splitlines():
        teile = zeile.split("\t")
        if len(teile) == 5 and (teile[1] or teile[2]):
            liste.append({"app": teile[0], "titel": teile[1], "kuenstler": teile[2], "album": teile[3], "status": teile[4]})
    return liste


def sitzungen() -> list[dict]:
    try:
        if os.name == "nt":
            return _windows_sitzungen()
        if sys.platform.startswith("linux"):
            return _linux_sitzungen()
    except Exception as fehler:
        leise(fehler, "services/medien_jetzt")
    return []


def fenstertitel() -> list[str]:
    try:
        import pygetwindow

        titel = [t.strip() for t in pygetwindow.getAllTitles() if t and t.strip()]
    except Exception:
        return []
    return [t for t in titel if MEDIEN_FENSTER.search(t)][:8]


def _app_name(kennung: str) -> str:
    text = str(kennung or "")
    for muster, name in (("spotify", "Spotify"), ("chrome", "Google Chrome"), ("msedge", "Microsoft Edge"), ("firefox", "Firefox"), ("brave", "Brave"), ("zune", "Medienplayer"), ("applemusic", "Apple Music"), ("music", "Musik-App")):
        if muster in text.lower():
            return name
    return text.split("!")[0].split("\\")[-1] or "unbekannte App"


def jetzt() -> dict:
    liste = sitzungen()
    spielt = [s for s in liste if str(s.get("status", "")).lower() in ("playing", "4", "spielt")]
    beste = (spielt or liste or [None])[0]
    ergebnis: dict = {"sitzungen": [{**s, "app": _app_name(s.get("app", ""))} for s in liste], "fenster": fenstertitel()}
    if beste:
        ergebnis["lied"] = {"titel": beste.get("titel", ""), "kuenstler": beste.get("kuenstler", ""), "album": beste.get("album", ""), "app": _app_name(beste.get("app", "")), "spielt": beste in spielt}
    else:
        for titel in ergebnis["fenster"]:
            sauber = BROWSER.sub("", titel)
            sauber = re.sub(r"\s[-–—]\s(YouTube|Spotify)$", "", sauber, flags=re.I).strip()
            if sauber and sauber.lower() not in ("youtube", "spotify", "spotify premium", "spotify free"):
                ergebnis["lied_aus_fenster"] = sauber
                break
    return ergebnis
