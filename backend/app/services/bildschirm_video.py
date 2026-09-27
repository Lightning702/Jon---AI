from __future__ import annotations

import asyncio
import ctypes
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.logbook import logger as logbook_logger

_log = logbook_logger("video")

ORDNER = DATA_DIR / "bildschirmvideos"
FPS = 10
BREITE = 1280
MAX_SEKUNDEN = 180
BEHALTEN = 40
START_PRUEFUNG = 0.5
ANLAUF = 0.6

SICHTBARE_WERKZEUGE = {
    "start_program",
    "kill_program",
    "open_explorer",
    "open_in_vscode",
    "open_url",
    "focus_window",
    "mouse_move",
    "mouse_click",
    "mouse_scroll",
    "keyboard_type",
    "keyboard_press",
    "keyboard_hotkey",
    "media_control",
    "spotify_play",
    "amazon_play",
}
UNSICHTBARE_BROWSER = {
    "browser_status",
    "browser_read",
    "browser_screenshot",
    "browser_wahl",
}


class VideoFehler(Exception):
    pass


def sichtbar(name: str) -> bool:
    name = str(name or "")
    if name in SICHTBARE_WERKZEUGE:
        return True
    return name.startswith("browser_") and name not in UNSICHTBARE_BROWSER


def ffmpeg_pfad() -> str | None:
    return shutil.which("ffmpeg")


_encoder_cache: dict[str, str] = {}


def _encoder(ffmpeg: str) -> str:
    if ffmpeg in _encoder_cache:
        return _encoder_cache[ffmpeg]
    wahl = "mpeg4"
    try:
        lauf = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if "libx264" in lauf.stdout:
            wahl = "libx264"
    except Exception as fehler:
        leise(fehler, "services/bildschirm_video")
    _encoder_cache[ffmpeg] = wahl
    return wahl


def _dpi_bewusst():
    if os.name != "nt":
        return None
    try:
        return ctypes.windll.user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        return None


def _dpi_zurueck(alt) -> None:
    if os.name != "nt" or not alt:
        return
    try:
        ctypes.windll.user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(alt))
    except Exception as fehler:
        leise(fehler, "services/bildschirm_video")


def mauspunkt() -> tuple[int, int] | None:
    if os.name == "nt":
        class PUNKT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        punkt = PUNKT()
        try:
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(punkt)):
                return int(punkt.x), int(punkt.y)
        except Exception as fehler:
            leise(fehler, "services/bildschirm_video")
        return None
    try:
        import pyautogui

        x, y = pyautogui.position()
        return int(x), int(y)
    except Exception:
        return None


def _virtuell() -> dict | None:
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32
        feld = {
            "x": int(user32.GetSystemMetrics(76)),
            "y": int(user32.GetSystemMetrics(77)),
            "breite": int(user32.GetSystemMetrics(78)),
            "hoehe": int(user32.GetSystemMetrics(79)),
        }
    except Exception:
        return None
    return feld if feld["breite"] > 0 and feld["hoehe"] > 0 else None


def waehle_bereich(welcher: str, felder: list[dict], punkt: tuple[int, int] | None) -> dict | None:
    if not felder:
        return None
    wahl = str(welcher or "maus").strip().lower()
    treffer = None
    if wahl.isdigit():
        nummer = int(wahl)
        if 1 <= nummer <= len(felder):
            treffer = felder[nummer - 1]
    if treffer is None and punkt is not None:
        x, y = punkt
        treffer = next(
            (
                f
                for f in felder
                if f["links"] <= x < f["rechts"] and f["oben"] <= y < f["unten"]
            ),
            None,
        )
    if treffer is None:
        treffer = felder[0]
    return {
        "x": treffer["links"],
        "y": treffer["oben"],
        "breite": treffer["rechts"] - treffer["links"],
        "hoehe": treffer["unten"] - treffer["oben"],
    }


def bereich(welcher: str = "maus") -> dict | None:
    alt = _dpi_bewusst()
    try:
        if str(welcher or "").strip().lower() == "alle":
            return _virtuell()
        felder: list[dict] = []
        if os.name == "nt":
            from app.services.live_service import _monitore_windows

            try:
                felder = _monitore_windows()
            except Exception as fehler:
                leise(fehler, "services/bildschirm_video")
        return waehle_bereich(welcher, felder, mauspunkt())
    finally:
        _dpi_zurueck(alt)


def _filter(breite: int) -> str:
    return f"scale=w='trunc(min({breite},iw)/2)*2':h=-2,format=yuv420p"


def ffmpeg_befehl(
    ffmpeg: str,
    feld: dict | None,
    ziel: Path,
    encoder: str = "libx264",
    fps: int = FPS,
    breite: int = BREITE,
    max_sekunden: int = MAX_SEKUNDEN,
    system: str | None = None,
    anzeige: str = "",
) -> list[str]:
    system = system or os.name
    befehl = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    if system == "nt":
        befehl += ["-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1"]
        if feld:
            befehl += [
                "-offset_x",
                str(feld["x"]),
                "-offset_y",
                str(feld["y"]),
                "-video_size",
                f"{feld['breite']}x{feld['hoehe']}",
            ]
        befehl += ["-i", "desktop"]
    else:
        befehl += ["-f", "x11grab", "-framerate", str(fps), "-draw_mouse", "1"]
        eingang = anzeige or ":0"
        if feld:
            befehl += ["-video_size", f"{feld['breite']}x{feld['hoehe']}"]
            eingang += f"+{feld['x']},{feld['y']}"
        befehl += ["-i", eingang]
    befehl += ["-t", str(max_sekunden), "-vf", _filter(breite)]
    if encoder == "libx264":
        befehl += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "28"]
    else:
        befehl += ["-c:v", "mpeg4", "-q:v", "6"]
    befehl += ["-an", "-movflags", "+faststart", str(ziel)]
    return befehl


def _anzeige() -> str:
    anzeige = os.environ.get("DISPLAY", "")
    if anzeige:
        return anzeige
    if Path("/tmp/.X11-unix/X0").exists():
        return ":0"
    return ""


def _neue_datei() -> Path:
    ORDNER.mkdir(parents=True, exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return ORDNER / f"bildschirm-{stempel}.mp4"


def aufraeumen(behalten: int = BEHALTEN) -> None:
    try:
        dateien = sorted(ORDNER.glob("bildschirm-*.mp4"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return
    for alt in dateien[:-behalten] if behalten else dateien:
        try:
            alt.unlink()
        except OSError as fehler:
            leise(fehler, "services/bildschirm_video")


class _BilderSchleife:
    def __init__(self, feld: dict | None, ziel: Path, fps: int, breite: int, max_sekunden: int) -> None:
        self.feld = feld
        self.ziel = ziel
        self.fps = max(2, min(fps, 12))
        self.breite = breite
        self.max_sekunden = max_sekunden
        self._halt = threading.Event()
        self._faden: threading.Thread | None = None
        self.fehler = ""

    def _bild(self):
        from PIL import ImageDraw, ImageGrab

        if os.name == "nt":
            gesamt = ImageGrab.grab(all_screens=True)
            virtuell = _virtuell() or {"x": 0, "y": 0}
        else:
            gesamt = ImageGrab.grab()
            virtuell = {"x": 0, "y": 0}
        if self.feld:
            links = self.feld["x"] - virtuell["x"]
            oben = self.feld["y"] - virtuell["y"]
            bild = gesamt.crop(
                (links, oben, links + self.feld["breite"], oben + self.feld["hoehe"])
            )
            ursprung = (self.feld["x"], self.feld["y"])
        else:
            bild = gesamt
            ursprung = (virtuell["x"], virtuell["y"])
        punkt = mauspunkt()
        if punkt is not None:
            x, y = punkt[0] - ursprung[0], punkt[1] - ursprung[1]
            zeichner = ImageDraw.Draw(bild)
            zeichner.polygon(
                [(x, y), (x, y + 18), (x + 5, y + 14), (x + 9, y + 22), (x + 12, y + 21), (x + 8, y + 13), (x + 14, y + 13)],
                fill=(255, 255, 255),
                outline=(0, 0, 0),
            )
        return bild.convert("RGB")

    def starten(self) -> None:
        try:
            import cv2
            import numpy
        except Exception as fehler:
            raise VideoFehler(
                "Fuer Bildschirmvideos fehlt ffmpeg. Installiere es mit: "
                "winget install Gyan.FFmpeg"
            ) from fehler
        try:
            probe = self._bild()
        except Exception as fehler:
            raise VideoFehler("Hier gibt es keinen Bildschirm, den ich aufnehmen kann.") from fehler
        breite = min(self.breite, probe.width) // 2 * 2
        hoehe = max(2, int(probe.height * breite / probe.width) // 2 * 2)
        schreiber = cv2.VideoWriter(
            str(self.ziel), cv2.VideoWriter_fourcc(*"mp4v"), float(self.fps), (breite, hoehe)
        )
        if not schreiber.isOpened():
            raise VideoFehler("Die Videodatei liess sich nicht anlegen.")

        def schleife() -> None:
            takt = 1.0 / self.fps
            ende = time.monotonic() + self.max_sekunden
            naechster = time.monotonic()
            try:
                while not self._halt.is_set() and time.monotonic() < ende:
                    bild = self._bild().resize((breite, hoehe))
                    rahmen = cv2.cvtColor(numpy.asarray(bild), cv2.COLOR_RGB2BGR)
                    schreiber.write(rahmen)
                    naechster += takt
                    while naechster < time.monotonic():
                        schreiber.write(rahmen)
                        naechster += takt
                    self._halt.wait(max(0.0, naechster - time.monotonic()))
            except Exception as fehler:
                self.fehler = str(fehler)
                leise(fehler, "services/bildschirm_video")
            finally:
                schreiber.release()

        self._faden = threading.Thread(target=schleife, name="jon-bildschirmvideo", daemon=True)
        self._faden.start()

    def stoppen(self) -> None:
        self._halt.set()
        if self._faden is not None:
            self._faden.join(timeout=20)


class Aufnahme:
    def __init__(
        self,
        welcher: str = "maus",
        fps: int = FPS,
        breite: int = BREITE,
        max_sekunden: int = MAX_SEKUNDEN,
    ) -> None:
        self.welcher = welcher
        self.fps = fps
        self.breite = breite
        self.max_sekunden = max_sekunden
        self.ziel: Path | None = None
        self.gestartet = 0.0
        self._prozess: subprocess.Popen | None = None
        self._bilder: _BilderSchleife | None = None

    def starten(self) -> None:
        feld = bereich(self.welcher)
        self.ziel = _neue_datei()
        ffmpeg = ffmpeg_pfad()
        anzeige = ""
        if os.name != "nt":
            anzeige = _anzeige()
            if not anzeige:
                raise VideoFehler("Hier gibt es keinen Bildschirm, den ich aufnehmen kann.")
        if ffmpeg:
            befehl = ffmpeg_befehl(
                ffmpeg,
                feld,
                self.ziel,
                encoder=_encoder(ffmpeg),
                fps=self.fps,
                breite=self.breite,
                max_sekunden=self.max_sekunden,
                anzeige=anzeige,
            )
            try:
                self._prozess = subprocess.Popen(
                    befehl,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError as fehler:
                raise VideoFehler(f"ffmpeg liess sich nicht starten: {fehler}") from fehler
            time.sleep(START_PRUEFUNG)
            if self._prozess.poll() is not None:
                meldung = (self._prozess.stderr.read() or b"").decode("utf-8", "replace").strip()
                self._prozess = None
                raise VideoFehler(
                    "Die Bildschirmaufnahme ist sofort abgebrochen"
                    + (f": {meldung[-300:]}" if meldung else ".")
                )
        else:
            if os.name != "nt":
                raise VideoFehler(
                    "Fuer Bildschirmvideos fehlt ffmpeg (sudo apt install ffmpeg)."
                )
            self._bilder = _BilderSchleife(
                feld, self.ziel, self.fps, self.breite, self.max_sekunden
            )
            self._bilder.starten()
        self.gestartet = time.monotonic()
        _log.info("Bildschirmaufnahme gestartet: %s", self.ziel.name)

    def laeuft(self) -> bool:
        if self._prozess is not None:
            return self._prozess.poll() is None
        return self._bilder is not None

    def stoppen(self) -> Path | None:
        prozess, self._prozess = self._prozess, None
        if prozess is not None:
            try:
                if prozess.poll() is None and prozess.stdin:
                    prozess.stdin.write(b"q")
                    prozess.stdin.flush()
                    prozess.stdin.close()
                prozess.wait(timeout=20)
            except Exception as fehler:
                leise(fehler, "services/bildschirm_video")
                try:
                    prozess.kill()
                    prozess.wait(timeout=5)
                except Exception as fehler2:
                    leise(fehler2, "services/bildschirm_video")
        bilder, self._bilder = self._bilder, None
        if bilder is not None:
            bilder.stoppen()
        aufraeumen()
        if self.ziel and self.ziel.is_file() and self.ziel.stat().st_size > 1024:
            return self.ziel
        return None

    def verwerfen(self) -> None:
        pfad = self.stoppen()
        if pfad is not None:
            try:
                pfad.unlink()
            except OSError as fehler:
                leise(fehler, "services/bildschirm_video")


async def clip(welcher: str = "maus", sekunden: float = 10.0) -> Path:
    aufnahme = Aufnahme(welcher, max_sekunden=int(sekunden) + 30)
    await asyncio.to_thread(aufnahme.starten)
    pfad: Path | None = None
    try:
        await asyncio.sleep(max(1.0, sekunden))
    finally:
        pfad = await asyncio.to_thread(aufnahme.stoppen)
    if pfad is None:
        raise VideoFehler("Die Aufnahme ist leer geblieben.")
    return pfad


class Aktionsvideo:
    def __init__(self, welcher: str = "maus") -> None:
        self.welcher = welcher
        self.aufnahme: Aufnahme | None = None
        self.fehler = ""

    async def werkzeug(self, name: str) -> None:
        if self.aufnahme is not None or self.fehler or not sichtbar(name):
            return
        aufnahme = Aufnahme(self.welcher)
        try:
            await asyncio.to_thread(aufnahme.starten)
        except VideoFehler as fehler:
            self.fehler = str(fehler)
            return
        except Exception as fehler:
            leise(fehler, "services/bildschirm_video")
            self.fehler = str(fehler)
            return
        self.aufnahme = aufnahme
        await asyncio.sleep(ANLAUF)

    async def beenden(self, nachlauf: float = 2.5) -> Path | None:
        if self.aufnahme is None:
            return None
        await asyncio.sleep(max(0.0, nachlauf))
        aufnahme, self.aufnahme = self.aufnahme, None
        return await asyncio.to_thread(aufnahme.stoppen)

    async def verwerfen(self) -> None:
        aufnahme, self.aufnahme = self.aufnahme, None
        if aufnahme is not None:
            await asyncio.to_thread(aufnahme.verwerfen)
