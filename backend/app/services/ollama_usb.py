from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import socket
import string
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import DATA_DIR
from app.core.fehler import leise
from app.core.store import atomic_write_text

PRAEFIX = "usb:"
DATEI = DATA_DIR / "ollama_usb.json"
PROTOKOLL = DATA_DIR / "ollama_usb.log"
IMPORT_ORDNER = DATA_DIR / "ollama_usb_import"
PORTS = range(11435, 11445)
TIEFE = 5
MAX_EINTRAEGE = 60000
GGUF_MIN = 16 * 1024 * 1024
STARTZEIT = 40.0
LISTE_TTL = 20.0
REGISTRIES = {"registry.ollama.ai", "ollama.com"}
UEBERSPRINGEN = {
    "$recycle.bin", "system volume information", "windows", "program files", "program files (x86)",
    "programdata", "node_modules", ".git", "$windows.~bt", "$windows.~ws", "recovery", "msocache",
    ".trashes", ".spotlight-v100", ".fseventsd", "$sysreset", "perflogs",
}
ARTEN = {2: "usb", 3: "fest", 4: "netz", 5: "cd", 6: "ram"}
NAME_ERLAUBT = re.compile(r"[^a-z0-9._-]+")
OHNE_FENSTER = 0x08000000 if os.name == "nt" else 0


class UsbFehler(RuntimeError):
    pass


def _bezeichnung(kernel: Any, wurzel: str) -> str:
    import ctypes

    puffer = ctypes.create_unicode_buffer(261)
    try:
        if kernel.GetVolumeInformationW(wurzel, puffer, 261, None, None, None, None, 0):
            return puffer.value
    except Exception as fehler:
        leise(fehler, "services/ollama_usb")
    return ""


def laufwerke() -> list[dict]:
    if os.name != "nt":
        return _einhaengepunkte()
    import ctypes

    kernel = ctypes.windll.kernel32
    alt = kernel.SetErrorMode(0x0001)
    gefunden: list[dict] = []
    system = (os.environ.get("SystemDrive") or "C:").upper().rstrip("\\") + "\\"
    try:
        maske = int(kernel.GetLogicalDrives())
        for index, buchstabe in enumerate(string.ascii_uppercase):
            if not maske & (1 << index):
                continue
            wurzel = f"{buchstabe}:\\"
            art = ARTEN.get(int(kernel.GetDriveTypeW(wurzel)), "")
            if not art or art == "cd":
                continue
            try:
                nutzung = shutil.disk_usage(wurzel)
            except OSError:
                continue
            gefunden.append(
                {
                    "pfad": wurzel,
                    "name": _bezeichnung(kernel, wurzel),
                    "art": art,
                    "frei": int(nutzung.free),
                    "gesamt": int(nutzung.total),
                    "system": wurzel == system,
                }
            )
    finally:
        kernel.SetErrorMode(alt)
    gefunden.sort(key=lambda eintrag: (eintrag["system"], eintrag["art"] != "usb", eintrag["pfad"]))
    return gefunden


def _einhaengepunkte() -> list[dict]:
    nutzer = os.environ.get("USER", "")
    orte = [Path("/Volumes"), Path("/media") / nutzer, Path("/run/media") / nutzer, Path("/media"), Path("/mnt")]
    gefunden: list[dict] = []
    gesehen: set[str] = set()
    for ort in orte:
        try:
            kinder = sorted(p for p in ort.iterdir() if p.is_dir())
        except OSError:
            continue
        for kind in kinder:
            pfad = str(kind)
            if pfad in gesehen or (ort == Path("/media") and kind.name == nutzer):
                continue
            gesehen.add(pfad)
            try:
                nutzung = shutil.disk_usage(pfad)
            except OSError:
                continue
            gefunden.append({"pfad": pfad, "name": kind.name, "art": "usb", "frei": int(nutzung.free), "gesamt": int(nutzung.total), "system": False})
    return gefunden


def ist_speicher(ordner: Path) -> bool:
    try:
        return (ordner / "blobs").is_dir() and ((ordner / "manifests").is_dir() or (ordner / "manifests-v2").is_dir())
    except OSError:
        return False


def _modellname(host: str, raum: str, modell: str, tag: str) -> str:
    if host in REGISTRIES and raum == "library":
        return f"{modell}:{tag}"
    if host in REGISTRIES:
        return f"{raum}/{modell}:{tag}"
    return f"{host}/{raum}/{modell}:{tag}"


def _blob(speicher: Path, digest: str) -> Path:
    return speicher / "blobs" / str(digest).replace(":", "-")


def _konfiguration(speicher: Path, eintrag: Any) -> dict:
    if not isinstance(eintrag, dict) or not eintrag.get("digest"):
        return {}
    datei = _blob(speicher, str(eintrag["digest"]))
    try:
        if datei.stat().st_size > 256 * 1024:
            return {}
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def modelle_lesen(speicher: Path) -> list[dict]:
    gefunden: dict[str, dict] = {}
    for unterordner in ("manifests-v2", "manifests"):
        basis = speicher / unterordner
        if not basis.is_dir():
            continue
        for wurzel, _ordner, dateien in os.walk(basis):
            for name in dateien:
                datei = Path(wurzel) / name
                teile = datei.relative_to(basis).parts
                if len(teile) != 4:
                    continue
                modellname = _modellname(*teile)
                if modellname in gefunden:
                    continue
                try:
                    manifest = json.loads(datei.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(manifest, dict):
                    continue
                schichten = [s for s in manifest.get("layers") or [] if isinstance(s, dict)]
                groesse = sum(int(s.get("size") or 0) for s in schichten)
                fehlend = [s for s in schichten if s.get("digest") and not _blob(speicher, str(s["digest"])).is_file()]
                info = _konfiguration(speicher, manifest.get("config"))
                gefunden[modellname] = {
                    "name": modellname,
                    "id": PRAEFIX + modellname,
                    "groesse": groesse,
                    "familie": str(info.get("model_family") or ""),
                    "parameter": str(info.get("model_type") or ""),
                    "quantisierung": str(info.get("file_type") or ""),
                    "vollstaendig": not fehlend,
                }
    return sorted(gefunden.values(), key=lambda eintrag: eintrag["name"])


def durchsuchen(pfad: str) -> dict:
    roh = str(pfad or "").strip().strip('"').strip()
    if not roh:
        raise UsbFehler("Wähle zuerst ein Laufwerk oder einen Ordner aus.")
    if re.fullmatch(r"[A-Za-z]:?", roh):
        roh = roh[0] + ":\\"
    wurzel = Path(roh).expanduser()
    if not wurzel.exists():
        raise UsbFehler(f"{wurzel} gibt es nicht. Steckt der USB-Stick?")
    if wurzel.is_file():
        if wurzel.suffix.lower() != ".gguf":
            raise UsbFehler("Wähle ein Laufwerk, einen Ordner oder eine .gguf-Datei aus.")
        return {"pfad": str(wurzel), "speicher": [], "gguf": [_gguf_eintrag(wurzel)], "programme": [], "abgebrochen": False}
    speicher: list[Path] = []
    ggufs: list[dict] = []
    programme: list[str] = []
    gezaehlt = 0
    abgebrochen = False
    stapel: list[tuple[Path, int]] = [(wurzel, 0)]
    while stapel:
        ordner, tiefe = stapel.pop()
        if ist_speicher(ordner):
            speicher.append(ordner)
            continue
        try:
            eintraege = list(os.scandir(ordner))
        except OSError:
            continue
        for eintrag in eintraege:
            gezaehlt += 1
            if gezaehlt > MAX_EINTRAEGE:
                abgebrochen = True
                stapel.clear()
                break
            name = eintrag.name.lower()
            try:
                if eintrag.is_dir(follow_symlinks=False):
                    if tiefe < TIEFE and name not in UEBERSPRINGEN:
                        stapel.append((Path(eintrag.path), tiefe + 1))
                elif name.endswith(".gguf"):
                    groesse = eintrag.stat().st_size
                    if groesse >= GGUF_MIN and "mmproj" not in name:
                        ggufs.append(_gguf_eintrag(Path(eintrag.path), groesse))
                elif name in ("ollama.exe", "ollama") and eintrag.is_file():
                    programme.append(eintrag.path)
            except OSError:
                continue
    ergebnis = []
    for ordner in sorted(speicher, key=lambda p: str(p).lower()):
        modelle = modelle_lesen(ordner)
        ergebnis.append({"pfad": str(ordner), "modelle": modelle, "groesse": sum(m["groesse"] for m in modelle)})
    return {
        "pfad": str(wurzel),
        "speicher": ergebnis,
        "gguf": sorted(ggufs, key=lambda g: g["pfad"].lower()),
        "programme": programme,
        "abgebrochen": abgebrochen,
    }


def _gguf_eintrag(datei: Path, groesse: int | None = None) -> dict:
    if groesse is None:
        try:
            groesse = datei.stat().st_size
        except OSError:
            groesse = 0
    return {"pfad": str(datei), "datei": datei.name, "groesse": int(groesse), "vorschlag": modellname_aus_datei(datei.name)}


def modellname_aus_datei(dateiname: str) -> str:
    stamm = dateiname[:-5] if dateiname.lower().endswith(".gguf") else dateiname
    sauber = NAME_ERLAUBT.sub("-", stamm.lower()).strip("-._")
    return (sauber or "usb-modell")[:80]


def _prozess_laeuft(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            ausgabe = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=6, creationflags=OHNE_FENSTER,
            ).stdout.lower()
        except Exception:
            return False
        return "ollama" in ausgabe
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        return "ollama" in Path(f"/proc/{pid}/cmdline").read_text(errors="ignore").lower()
    except OSError:
        return True


def _prozess_beenden(pid: int) -> None:
    if not _prozess_laeuft(pid):
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=10, creationflags=OHNE_FENSTER)
        else:
            os.kill(pid, 15)
    except Exception as fehler:
        leise(fehler, "services/ollama_usb")


def _port_frei(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        return probe.connect_ex(("127.0.0.1", port)) != 0


class UsbOllama:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._start_lock = threading.Lock()
        self._prozess: subprocess.Popen | None = None
        self._daten = self._laden()
        self._liste: list[str] = []
        self._liste_zeit = 0.0
        self._aufgabe: dict[str, Any] = {}
        self._letzter_fehler = ""
        atexit.register(self.beenden)

    def _laden(self) -> dict[str, Any]:
        daten: dict[str, Any] = {"speicher": "", "programm": "", "port": 0, "pid": 0, "aktiv": False}
        try:
            gespeichert = json.loads(DATEI.read_text(encoding="utf-8"))
            if isinstance(gespeichert, dict):
                daten.update({k: gespeichert[k] for k in daten if k in gespeichert})
        except (OSError, ValueError):
            pass
        return daten

    def _speichern(self) -> None:
        try:
            DATEI.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(DATEI, json.dumps(self._daten, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as fehler:
            leise(fehler, "services/ollama_usb")

    def speicher(self) -> str:
        with self._lock:
            return str(self._daten.get("speicher") or "")

    def aktiv(self) -> bool:
        with self._lock:
            return bool(self._daten.get("aktiv")) and bool(self._daten.get("speicher"))

    def basis(self) -> str:
        with self._lock:
            port = int(self._daten.get("port") or 0)
        return f"http://127.0.0.1:{port}" if port else ""

    def _erreichbar(self, port: int, zeit: float = 1.5) -> bool:
        if not port:
            return False
        try:
            return httpx.get(f"http://127.0.0.1:{port}/api/version", timeout=zeit).status_code == 200
        except Exception:
            return False

    def laeuft(self) -> bool:
        with self._lock:
            prozess = self._prozess
            port = int(self._daten.get("port") or 0)
            pid = int(self._daten.get("pid") or 0)
        if prozess is not None and prozess.poll() is None:
            return self._erreichbar(port)
        if prozess is None and pid and _prozess_laeuft(pid):
            return self._erreichbar(port)
        return False

    def _programm(self, speicher: Path, gefunden: list[str] | None = None) -> str:
        kandidaten: list[str] = list(gefunden or [])
        kandidaten.append(str(self._daten.get("programm") or ""))
        stick = Path(speicher.anchor) if speicher.anchor else speicher
        for ort in (speicher.parent, speicher.parent.parent, stick / "ollama", stick / "Ollama", stick):
            kandidaten.append(str(ort / ("ollama.exe" if os.name == "nt" else "ollama")))
        kandidaten.append(shutil.which("ollama") or "")
        lokal = os.environ.get("LOCALAPPDATA", "")
        if lokal:
            kandidaten.append(str(Path(lokal) / "Programs" / "Ollama" / "ollama.exe"))
        for basis in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramW6432", "")):
            if basis:
                kandidaten.append(str(Path(basis) / "Ollama" / "ollama.exe"))
        kandidaten += ["/usr/local/bin/ollama", "/usr/bin/ollama", "/opt/homebrew/bin/ollama", "/Applications/Ollama.app/Contents/Resources/ollama"]
        for kandidat in kandidaten:
            if kandidat and Path(kandidat).name.lower() in ("ollama.exe", "ollama") and Path(kandidat).is_file():
                return kandidat
        raise UsbFehler(
            "Ollama ist auf diesem PC nicht installiert und liegt auch nicht auf dem Stick. "
            "Installiere Ollama von ollama.com oder leg die portable ollama.exe mit auf den Stick."
        )

    def _protokoll_ende(self) -> str:
        try:
            zeilen = PROTOKOLL.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        except OSError:
            return ""
        return " | ".join(z.strip() for z in zeilen[-3:])[:400]

    def _starten(self, speicher: Path, programm: str) -> int:
        self._stoppen()
        port = next((p for p in PORTS if _port_frei(p)), 0)
        if not port:
            raise UsbFehler("Für den USB-Server ist kein Port zwischen 11435 und 11444 frei.")
        umgebung = dict(os.environ)
        umgebung.update({"OLLAMA_MODELS": str(speicher), "OLLAMA_HOST": f"127.0.0.1:{port}", "OLLAMA_NOPRUNE": "1"})
        umgebung.pop("OLLAMA_ORIGINS", None)
        PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
        with open(PROTOKOLL, "wb") as ausgabe:
            prozess = subprocess.Popen(
                [programm, "serve"],
                env=umgebung,
                stdin=subprocess.DEVNULL,
                stdout=ausgabe,
                stderr=ausgabe,
                cwd=str(Path(programm).parent),
                creationflags=OHNE_FENSTER,
            )
        with self._lock:
            self._prozess = prozess
            self._daten.update({"port": port, "pid": prozess.pid})
        ende = time.monotonic() + STARTZEIT
        while time.monotonic() < ende:
            if prozess.poll() is not None:
                raise UsbFehler("Ollama vom Stick hat sich sofort beendet. " + self._protokoll_ende())
            if self._erreichbar(port, 1.0):
                return port
            time.sleep(0.4)
        self._stoppen()
        raise UsbFehler("Ollama vom Stick ist nicht rechtzeitig hochgefahren. " + self._protokoll_ende())

    def _stoppen(self) -> None:
        with self._lock:
            prozess = self._prozess
            pid = int(self._daten.get("pid") or 0)
            self._prozess = None
            self._daten["pid"] = 0
            self._liste = []
            self._liste_zeit = 0.0
        if prozess is not None and prozess.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(prozess.pid), "/T", "/F"], capture_output=True, timeout=10, creationflags=OHNE_FENSTER)
                else:
                    prozess.terminate()
                prozess.wait(timeout=8)
            except Exception as fehler:
                leise(fehler, "services/ollama_usb")
        elif pid:
            _prozess_beenden(pid)

    def verbinden(self, pfad: str, programme: list[str] | None = None) -> dict:
        speicher = Path(str(pfad or "").strip().strip('"')).expanduser()
        if not ist_speicher(speicher):
            raise UsbFehler(f"In {speicher} liegen keine Ollama-Modelle (es fehlen die Ordner blobs und manifests).")
        with self._start_lock:
            programm = self._programm(speicher, programme)
            port = self._starten(speicher, programm)
            with self._lock:
                self._daten.update({"speicher": str(speicher), "programm": programm, "port": port, "aktiv": True})
                self._speichern()
        self._letzter_fehler = ""
        self.modelle(frisch=True)
        return self.stand()

    def trennen(self) -> dict:
        with self._start_lock:
            self._stoppen()
            with self._lock:
                self._daten.update({"aktiv": False, "port": 0})
                self._speichern()
        return self.stand()

    def beenden(self) -> None:
        try:
            self._stoppen()
            with self._lock:
                self._speichern()
        except Exception as fehler:
            leise(fehler, "services/ollama_usb")

    def sicherstellen(self) -> str:
        if not self.aktiv():
            raise UsbFehler("Es ist kein USB-Stick mit Ollama-Modellen verbunden. Verbinde ihn in den Einstellungen unter Ollama.")
        speicher = Path(self.speicher())
        if not ist_speicher(speicher):
            self._stoppen()
            raise UsbFehler(f"Der USB-Stick mit den Modellen ({speicher}) ist nicht eingesteckt.")
        if self.laeuft():
            return self.basis()
        with self._start_lock:
            if self.laeuft():
                return self.basis()
            port = self._starten(speicher, self._programm(speicher))
            with self._lock:
                self._daten["port"] = port
                self._speichern()
        return self.basis()

    def _im_hintergrund_starten(self) -> None:
        def los() -> None:
            try:
                self.sicherstellen()
                self.modelle(frisch=True)
            except Exception as fehler:
                self._letzter_fehler = str(fehler)

        threading.Thread(target=los, name="usb-ollama-start", daemon=True).start()

    def modelle(self, frisch: bool = False) -> list[str]:
        if not self.aktiv():
            return []
        if not ist_speicher(Path(self.speicher())):
            if self._prozess is not None:
                self._stoppen()
            return []
        jetzt = time.monotonic()
        with self._lock:
            if not frisch and self._liste and jetzt - self._liste_zeit < LISTE_TTL:
                return list(self._liste)
        if not self.laeuft():
            if not self._start_lock.locked():
                self._im_hintergrund_starten()
            return [PRAEFIX + m["name"] for m in modelle_lesen(Path(self.speicher())) if m["vollstaendig"]]
        try:
            antwort = httpx.get(self.basis() + "/api/tags", timeout=4.0)
            antwort.raise_for_status()
            namen = sorted(
                str(m.get("name") or m.get("model") or "").strip()
                for m in antwort.json().get("models", [])
                if isinstance(m, dict)
            )
        except Exception as fehler:
            self._letzter_fehler = str(fehler)
            return list(self._liste)
        liste = [PRAEFIX + n for n in namen if n]
        with self._lock:
            self._liste = liste
            self._liste_zeit = time.monotonic()
        return list(liste)

    @staticmethod
    def zerlegen(modell: str) -> tuple[bool, str]:
        text = str(modell or "")
        if text.startswith(PRAEFIX):
            return True, text[len(PRAEFIX):]
        return False, text

    def stand(self) -> dict:
        speicher = self.speicher()
        vorhanden = bool(speicher) and ist_speicher(Path(speicher))
        laeuft = self.laeuft() if self.aktiv() else False
        modelle = modelle_lesen(Path(speicher)) if vorhanden else []
        with self._lock:
            aufgabe = dict(self._aufgabe)
            port = int(self._daten.get("port") or 0)
            programm = str(self._daten.get("programm") or "")
        return {
            "aktiv": self.aktiv(),
            "speicher": speicher,
            "eingesteckt": vorhanden,
            "laeuft": laeuft,
            "port": port if laeuft else 0,
            "programm": programm,
            "modelle": modelle,
            "fehler": self._letzter_fehler,
            "aufgabe": aufgabe,
        }

    def einbinden(self, datei: str, name: str = "") -> dict:
        gguf = Path(str(datei or "").strip().strip('"'))
        if gguf.suffix.lower() != ".gguf" or not gguf.is_file():
            raise UsbFehler("Diese .gguf-Datei gibt es nicht (mehr).")
        with self._lock:
            if self._aufgabe.get("laeuft"):
                raise UsbFehler("Es wird gerade schon ein Modell eingebunden. Warte, bis es fertig ist.")
        modellname = modellname_aus_datei(name or gguf.name)
        if ":" not in modellname:
            modellname += ":latest"
        speicher = Path(self.speicher()) if self.aktiv() else Path()
        if not self.aktiv() or Path(speicher.anchor).resolve() != Path(gguf.anchor).resolve():
            speicher = Path(gguf.anchor) / "ollama" / "models"
        groesse = gguf.stat().st_size
        try:
            frei = shutil.disk_usage(speicher.anchor or str(speicher)).free
        except OSError:
            frei = 0
        if frei and frei < groesse + 200 * 1024 * 1024:
            raise UsbFehler(
                f"Auf {speicher.anchor} ist zu wenig Platz: Ollama legt eine eigene Kopie der Datei an "
                f"({groesse / 1e9:.1f} GB), frei sind nur {frei / 1e9:.1f} GB."
            )
        with self._lock:
            self._aufgabe = {"laeuft": True, "name": modellname, "datei": str(gguf), "text": "Starte Ollama auf dem Stick …", "fehler": "", "fertig": False, "start": time.time()}
        threading.Thread(target=self._einbinden_lauf, args=(gguf, modellname, speicher), name="usb-ollama-import", daemon=True).start()
        return self.stand()

    def _aufgabe_setzen(self, **werte: Any) -> None:
        with self._lock:
            self._aufgabe.update(werte)

    def _einbinden_lauf(self, gguf: Path, modellname: str, speicher: Path) -> None:
        try:
            for unterordner in ("blobs", "manifests"):
                (speicher / unterordner).mkdir(parents=True, exist_ok=True)
            if self.speicher() != str(speicher) or not self.laeuft():
                self.verbinden(str(speicher))
            programm = str(self._daten.get("programm") or "") or self._programm(speicher)
            IMPORT_ORDNER.mkdir(parents=True, exist_ok=True)
            modelfile = IMPORT_ORDNER / (re.sub(r"[^A-Za-z0-9._-]", "_", modellname) + ".Modelfile")
            modelfile.write_text(f'FROM "{gguf}"\n', encoding="utf-8")
            self._aufgabe_setzen(text=f"Ollama übernimmt {gguf.name} auf den Stick. Das kann bei großen Modellen einige Minuten dauern …")
            umgebung = dict(os.environ)
            umgebung["OLLAMA_HOST"] = self.basis().replace("http://", "")
            ergebnis = subprocess.run(
                [programm, "create", modellname, "-f", str(modelfile)],
                env=umgebung,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3 * 3600,
                creationflags=OHNE_FENSTER,
            )
            modelfile.unlink(missing_ok=True)
            if ergebnis.returncode != 0:
                meldung = (ergebnis.stderr or ergebnis.stdout or "").strip().splitlines()
                raise UsbFehler("Ollama konnte die Datei nicht einbinden: " + (meldung[-1] if meldung else f"Fehler {ergebnis.returncode}"))
            self.modelle(frisch=True)
            self._aufgabe_setzen(laeuft=False, fertig=True, text=f"{modellname} liegt jetzt auf dem Stick und ist in Jon wählbar.")
        except Exception as fehler:
            self._aufgabe_setzen(laeuft=False, fertig=False, fehler=str(fehler)[:500], text="")


_dienst: UsbOllama | None = None
_dienst_lock = threading.Lock()


def get_usb_ollama() -> UsbOllama:
    global _dienst
    with _dienst_lock:
        if _dienst is None:
            _dienst = UsbOllama()
        return _dienst


def ist_usb_modell(modell: str) -> bool:
    return str(modell or "").startswith(PRAEFIX)

