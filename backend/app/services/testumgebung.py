from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from app.core.fehler import leise

BILD = "alpine:3.20"
PAKETE = "python3 py3-pip nodejs npm php83 bash curl git"
META = ".jon-umgebung.json"
MAX_AUSGABE = 60_000
MAX_DATEI = 2_000_000
STANDARD = "standard"
ERLAUBT = re.compile(r"[^a-z0-9-]+")

SPRACHEN = {
    "python": ("main.py", "python3 main.py", ["python", "main.py"]),
    "py": ("main.py", "python3 main.py", ["python", "main.py"]),
    "javascript": ("main.js", "node main.js", ["node", "main.js"]),
    "js": ("main.js", "node main.js", ["node", "main.js"]),
    "node": ("main.js", "node main.js", ["node", "main.js"]),
    "php": ("index.php", "php83 index.php", ["php", "index.php"]),
    "bash": ("main.sh", "bash main.sh", ["bash", "main.sh"]),
    "sh": ("main.sh", "sh main.sh", ["bash", "main.sh"]),
    "shell": ("main.sh", "sh main.sh", ["bash", "main.sh"]),
    "powershell": ("main.ps1", "", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "main.ps1"]),
    "ps1": ("main.ps1", "", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "main.ps1"]),
    "html": ("index.html", "", None),
    "htm": ("index.html", "", None),
    "svg": ("bild.svg", "", None),
    "css": ("style.css", "", None),
}


class Fehler(ValueError):
    pass


def _jetzt() -> float:
    return time.time()


class Testumgebung:
    def __init__(self) -> None:
        self._sperre = threading.RLock()
        self._docker_stand: tuple[float, dict] = (0.0, {})
        self._einrichtung: dict[str, str] = {}

    def wurzel(self) -> Path:
        eigen = os.environ.get("JON_TESTUMGEBUNG_DIR")
        if eigen:
            ziel = Path(eigen)
        else:
            from app.services.dateiraum_service import get_dateiraum_service

            ziel = get_dateiraum_service().wurzel() / "Testumgebung"
        ziel.mkdir(parents=True, exist_ok=True)
        return ziel

    def docker(self, frisch: bool = False) -> dict:
        zeit, stand = self._docker_stand
        if stand and not frisch and _jetzt() - zeit < 30:
            return stand
        programm = shutil.which("docker")
        stand = {"installiert": bool(programm), "laeuft": False}
        if programm:
            try:
                ergebnis = subprocess.run([programm, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=6, creationflags=_ohne_fenster())
                stand["laeuft"] = ergebnis.returncode == 0 and bool(ergebnis.stdout.strip())
            except (OSError, subprocess.TimeoutExpired):
                stand["laeuft"] = False
        self._docker_stand = (_jetzt(), stand)
        return stand

    def docker_starten(self) -> dict:
        stand = self.docker(True)
        if stand["laeuft"]:
            return {"ok": True, "text": "Docker läuft schon."}
        if not stand["installiert"]:
            return {"ok": False, "text": "Docker ist nicht installiert. Ohne Docker läuft die Testumgebung als abgeschotteter Ordner."}
        kandidaten = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Docker" / "Docker" / "Docker Desktop.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "Docker Desktop.exe",
        ]
        cli = shutil.which("docker")
        if cli:
            kandidaten.append(Path(cli).resolve().parents[2] / "Docker Desktop.exe")
        for pfad in kandidaten:
            if pfad.is_file():
                try:
                    subprocess.Popen([str(pfad)], creationflags=_ohne_fenster())
                except OSError as fehler:
                    return {"ok": False, "text": f"Docker Desktop ließ sich nicht starten: {fehler}"}
                return {"ok": True, "text": "Docker Desktop startet. Das dauert etwa eine halbe Minute."}
        return {"ok": False, "text": "Docker Desktop wurde nicht gefunden. Starte Docker selbst."}

    def _ordner(self, kennung: str) -> Path:
        sauber = ERLAUBT.sub("-", str(kennung or "").lower()).strip("-")
        if not sauber:
            raise Fehler("Diese Testumgebung gibt es nicht.")
        return self.wurzel() / sauber

    def _meta(self, ordner: Path) -> dict:
        try:
            return json.loads((ordner / META).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _meta_schreiben(self, ordner: Path, daten: dict) -> None:
        (ordner / META).write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")

    def _container(self, kennung: str) -> str:
        return f"jon-test-{kennung}"

    def beschreiben(self, kennung: str) -> dict:
        ordner = self._ordner(kennung)
        if not ordner.is_dir():
            raise Fehler("Diese Testumgebung gibt es nicht.")
        meta = self._meta(ordner)
        dateien = 0
        groesse = 0
        for pfad in ordner.rglob("*"):
            if pfad.is_file() and pfad.name != META:
                dateien += 1
                try:
                    groesse += pfad.stat().st_size
                except OSError:
                    pass
        modus = meta.get("modus", "ordner")
        zustand = self._einrichtung.get(ordner.name, "bereit")
        if modus == "maschine" and not self.docker()["laeuft"]:
            zustand = "docker_aus"
        return {
            "id": ordner.name,
            "name": meta.get("name") or ordner.name,
            "modus": modus,
            "erstellt": meta.get("erstellt", 0),
            "dateien": dateien,
            "groesse": groesse,
            "zustand": zustand,
            "pfad": str(ordner),
        }

    def liste(self) -> dict:
        umgebungen = []
        for ordner in sorted(self.wurzel().iterdir()):
            if ordner.is_dir() and (ordner / META).is_file():
                try:
                    umgebungen.append(self.beschreiben(ordner.name))
                except Fehler:
                    continue
        umgebungen.sort(key=lambda u: u["erstellt"])
        return {"umgebungen": umgebungen, "docker": self.docker()}

    def erstellen(self, name: str = "", maschine: bool | None = None, kennung: str = "") -> dict:
        with self._sperre:
            titel = str(name or "").strip()[:60] or "Testumgebung"
            basis = ERLAUBT.sub("-", (kennung or titel).lower()).strip("-")[:40] or "test"
            ordner = self.wurzel() / basis
            if not kennung:
                nummer = 2
                while ordner.exists():
                    ordner = self.wurzel() / f"{basis}-{nummer}"
                    nummer += 1
            ordner.mkdir(parents=True, exist_ok=True)
            docker = self.docker(True)
            modus = "maschine" if (docker["laeuft"] if maschine is None else (maschine and docker["laeuft"])) else "ordner"
            self._meta_schreiben(ordner, {"name": titel, "modus": modus, "erstellt": _jetzt()})
            if modus == "maschine":
                self._maschine_anlegen(ordner)
            return self.beschreiben(ordner.name)

    def _maschine_anlegen(self, ordner: Path) -> None:
        name = self._container(ordner.name)
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30, creationflags=_ohne_fenster())
        ergebnis = subprocess.run(
            ["docker", "run", "-d", "--name", name, "--label", "jon-testumgebung=1", "--memory", "2g", "--cpus", "2",
             "-v", f"{ordner}:/arbeit", "-w", "/arbeit", BILD, "sleep", "infinity"],
            capture_output=True, text=True, timeout=300, creationflags=_ohne_fenster(),
        )
        if ergebnis.returncode != 0:
            meta = self._meta(ordner)
            meta["modus"] = "ordner"
            meta["hinweis"] = (ergebnis.stderr or ergebnis.stdout).strip()[:300]
            self._meta_schreiben(ordner, meta)
            return
        self._einrichtung[ordner.name] = "richtet_ein"
        threading.Thread(target=self._pakete, args=(ordner.name, name), daemon=True).start()

    def _pakete(self, kennung: str, container: str) -> None:
        try:
            subprocess.run(["docker", "exec", container, "sh", "-c", f"apk add --no-cache {PAKETE} && ln -sf /usr/bin/php83 /usr/bin/php"], capture_output=True, timeout=900, creationflags=_ohne_fenster())
        except (OSError, subprocess.TimeoutExpired) as fehler:
            leise(fehler, "services/testumgebung")
        finally:
            self._einrichtung.pop(kennung, None)

    def standard(self) -> str:
        ordner = self.wurzel() / STANDARD
        if not (ordner / META).is_file():
            self.erstellen("Standard", None, STANDARD)
        return STANDARD

    def loeschen(self, kennung: str) -> dict:
        with self._sperre:
            ordner = self._ordner(kennung)
            if not ordner.is_dir():
                raise Fehler("Diese Testumgebung gibt es nicht.")
            if ordner.resolve().parent != self.wurzel().resolve():
                raise Fehler("Dieser Ordner gehört nicht zur Testumgebung.")
            if self._meta(ordner).get("modus") == "maschine" and shutil.which("docker"):
                try:
                    subprocess.run(["docker", "rm", "-f", self._container(ordner.name)], capture_output=True, timeout=60, creationflags=_ohne_fenster())
                except (OSError, subprocess.TimeoutExpired) as fehler:
                    leise(fehler, "services/testumgebung")
            shutil.rmtree(ordner, ignore_errors=True)
            return {"ok": True, "geloescht": ordner.name}

    def zuruecksetzen(self, kennung: str) -> dict:
        ordner = self._ordner(kennung)
        meta = self._meta(ordner)
        self.loeschen(kennung)
        return self.erstellen(meta.get("name") or kennung, meta.get("modus") == "maschine", ordner.name)

    def _pfad(self, kennung: str, pfad: str) -> Path:
        ordner = self._ordner(kennung)
        if not ordner.is_dir():
            raise Fehler("Diese Testumgebung gibt es nicht.")
        ziel = (ordner / str(pfad or "").replace("\\", "/").lstrip("/")).resolve()
        if ziel != ordner.resolve() and ordner.resolve() not in ziel.parents:
            raise Fehler("Der Pfad liegt außerhalb der Testumgebung.")
        if ziel.name == META:
            raise Fehler("Diese Datei gehört zur Verwaltung der Testumgebung.")
        return ziel

    def dateien(self, kennung: str) -> dict:
        ordner = self._ordner(kennung)
        if not ordner.is_dir():
            raise Fehler("Diese Testumgebung gibt es nicht.")
        eintraege = []
        for pfad in sorted(ordner.rglob("*")):
            if pfad.name == META or any(teil.startswith(".") and teil != "." for teil in pfad.relative_to(ordner).parts[:-1]):
                continue
            if pfad.is_file():
                try:
                    groesse = pfad.stat().st_size
                except OSError:
                    groesse = 0
                eintraege.append({"pfad": pfad.relative_to(ordner).as_posix(), "groesse": groesse})
            if len(eintraege) >= 500:
                break
        return {"id": ordner.name, "dateien": eintraege}

    def lesen(self, kennung: str, pfad: str) -> dict:
        ziel = self._pfad(kennung, pfad)
        if not ziel.is_file():
            raise Fehler("Diese Datei gibt es nicht.")
        if ziel.stat().st_size > MAX_DATEI:
            raise Fehler("Die Datei ist zu groß zum Anzeigen.")
        return {"pfad": pfad, "inhalt": ziel.read_text(encoding="utf-8", errors="replace")}

    def schreiben(self, kennung: str, pfad: str, inhalt: str) -> dict:
        ziel = self._pfad(kennung, pfad)
        if ziel.is_dir():
            raise Fehler("Das ist ein Ordner.")
        daten = str(inhalt or "")
        if len(daten.encode("utf-8")) > MAX_DATEI:
            raise Fehler("Der Inhalt ist zu groß.")
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(daten, encoding="utf-8")
        return {"ok": True, "pfad": ziel.relative_to(self._ordner(kennung)).as_posix(), "groesse": len(daten)}

    def ausfuehren(self, kennung: str, befehl: str, zeit: float = 60) -> dict:
        ordner = self._ordner(kennung)
        if not ordner.is_dir():
            raise Fehler("Diese Testumgebung gibt es nicht.")
        befehl = str(befehl or "").strip()
        if not befehl:
            raise Fehler("Kein Befehl angegeben.")
        zeit = max(1.0, min(float(zeit or 60), 600.0))
        meta = self._meta(ordner)
        beginn = _jetzt()
        if meta.get("modus") == "maschine":
            if not self.docker()["laeuft"]:
                raise Fehler("Docker läuft gerade nicht. Starte Docker oder lege eine Testumgebung ohne Maschine an.")
            if self._einrichtung.get(ordner.name):
                befehl = "while [ ! -x /usr/bin/php ] && pgrep apk >/dev/null; do sleep 1; done; " + befehl
            aufruf = ["docker", "exec", "-w", "/arbeit", self._container(ordner.name), "sh", "-lc", befehl]
            umgebung = None
        else:
            temp = ordner / ".tmp"
            temp.mkdir(exist_ok=True)
            umgebung = {**os.environ, "TEMP": str(temp), "TMP": str(temp), "JON_TESTUMGEBUNG": ordner.name}
            if sys.platform == "win32":
                aufruf = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + befehl]
            else:
                aufruf = ["sh", "-lc", befehl]
        return self._laufen(aufruf, ordner, umgebung, zeit, beginn, befehl)

    def _laufen(self, aufruf: list[str], ordner: Path, umgebung: dict | None, zeit: float, beginn: float, befehl: str) -> dict:
        try:
            prozess = subprocess.Popen(aufruf, cwd=str(ordner), env=umgebung, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=_ohne_fenster())
        except OSError as fehler:
            raise Fehler(f"Der Befehl ließ sich nicht starten: {fehler}") from fehler
        abgebrochen = False
        try:
            roh, _ = prozess.communicate(timeout=zeit)
        except subprocess.TimeoutExpired:
            abgebrochen = True
            _beenden(prozess)
            roh, _ = prozess.communicate()
        text = (roh or b"").decode("utf-8", errors="replace")
        if len(text) > MAX_AUSGABE:
            text = text[:MAX_AUSGABE // 2] + "\n…\n" + text[-MAX_AUSGABE // 2:]
        return {"befehl": befehl, "exit": prozess.returncode, "ausgabe": text, "dauer": round(_jetzt() - beginn, 2), "abgebrochen": abgebrochen}

    def code(self, kennung: str, sprache: str, code: str, dateiname: str = "") -> dict:
        art = str(sprache or "").strip().lower()
        if art not in SPRACHEN:
            raise Fehler(f"Die Sprache '{sprache}' kann die Testumgebung noch nicht ausführen.")
        standard_name, befehl_maschine, befehl_ordner = SPRACHEN[art]
        name = Path(str(dateiname or standard_name).replace("\\", "/")).name or standard_name
        geschrieben = self.schreiben(kennung, name, code)
        ergebnis = {"datei": geschrieben["pfad"], "umgebung": self._ordner(kennung).name}
        if befehl_ordner is None:
            ergebnis["vorschau"] = f"/testumgebung-vorschau/{self._ordner(kennung).name}/{geschrieben['pfad']}"
            return ergebnis
        ordner = self._ordner(kennung)
        if self._meta(ordner).get("modus") == "maschine":
            if not befehl_maschine:
                raise Fehler("PowerShell gibt es in der Linux-Maschine nicht. Nimm eine Testumgebung ohne Maschine.")
            lauf = self.ausfuehren(kennung, befehl_maschine.replace(standard_name, name), 120)
        else:
            programm = _programm(befehl_ordner[0])
            if not programm:
                hilfe = "Starte Docker und lege eine Testumgebung als Maschine an – dort ist es dabei." if self.docker()["installiert"] else "Installiere es oder nutze Docker für eine Maschine mit allem dabei."
                raise Fehler(f"{befehl_ordner[0]} ist auf diesem PC nicht installiert. {hilfe}")
            temp = ordner / ".tmp"
            temp.mkdir(exist_ok=True)
            umgebung = {**os.environ, "TEMP": str(temp), "TMP": str(temp), "PYTHONIOENCODING": "utf-8", "JON_TESTUMGEBUNG": ordner.name}
            aufruf = [programm, *[name if teil == standard_name else teil for teil in befehl_ordner[1:]]]
            lauf = self._laufen(aufruf, ordner, umgebung, 120, _jetzt(), " ".join(aufruf[1:]))
        ergebnis.update(lauf)
        if art == "php" and "<" in lauf.get("ausgabe", "") and "</" in lauf.get("ausgabe", ""):
            ausgabe_datei = self.schreiben(kennung, "ausgabe.html", lauf["ausgabe"])
            ergebnis["vorschau"] = f"/testumgebung-vorschau/{ordner.name}/{ausgabe_datei['pfad']}"
        return ergebnis

    def datei_fuer_vorschau(self, kennung: str, pfad: str) -> Path:
        ziel = self._pfad(kennung, pfad or "index.html")
        if ziel.is_dir():
            ziel = ziel / "index.html"
        if not ziel.is_file():
            raise Fehler("Diese Datei gibt es nicht.")
        return ziel


def _programm(name: str) -> str | None:
    if name == "python":
        if not getattr(sys, "frozen", False):
            return sys.executable
        for kandidat in ("python", "py", "python3"):
            gefunden = shutil.which(kandidat)
            if gefunden and "WindowsApps" not in gefunden:
                return gefunden
        return None
    return shutil.which(name)


def _ohne_fenster() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _beenden(prozess: subprocess.Popen) -> None:
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(prozess.pid)], capture_output=True, timeout=15, creationflags=_ohne_fenster())
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        prozess.kill()
    except OSError:
        pass


_dienst: Testumgebung | None = None


def get_testumgebung() -> Testumgebung:
    global _dienst
    if _dienst is None:
        _dienst = Testumgebung()
    return _dienst

