from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path


def neustarten() -> None:
    vorher = int(subprocess.check_output(["systemctl", "show", "jon.service", "-p", "MainPID", "--value"], text=True).strip())
    restart = subprocess.run(["systemctl", "--no-ask-password", "restart", "jon.service"], capture_output=True)
    if restart.returncode:
        policy = subprocess.check_output(["systemctl", "show", "jon.service", "-p", "Restart", "--value"], text=True).strip()
        if policy != "always" or vorher <= 1 or Path(f"/proc/{vorher}").stat().st_uid != os.getuid():
            raise RuntimeError("Neustart benötigt die lokale Dienstverwaltung.")
        os.kill(vorher, signal.SIGTERM)
    for versuch in range(60):
        time.sleep(1)
        pid = int(subprocess.check_output(["systemctl", "show", "jon.service", "-p", "MainPID", "--value"], text=True).strip())
        if pid <= 1 or pid == vorher:
            continue
        try:
            with urllib.request.urlopen("http://127.0.0.1:8756/api/health", timeout=2) as antwort:
                if json.load(antwort).get("status") == "ok":
                    return
        except Exception:
            pass
    raise RuntimeError("Jon antwortet nach dem Neustart nicht.")


def ausfuehren() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paket", type=Path, required=True)
    parser.add_argument("--ziel", type=Path, required=True)
    parser.add_argument("--neustart", action="store_true")
    args = parser.parse_args()
    root = args.ziel.resolve(strict=True)
    if not (root / "backend/app/main.py").is_file():
        raise SystemExit("Der angegebene Ordner enthält keine Jon-Installation.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sicherung = root.parent / "jon-device-sicherungen" / stamp
    sicherung.mkdir(parents=True)
    stage = sicherung / "neu"
    stage.mkdir()
    with zipfile.ZipFile(args.paket) as paket:
        manifest = json.loads(paket.read("SHA256.json"))
        for name, sha in manifest.items():
            ziel = (stage / name).resolve()
            if not ziel.is_relative_to(stage.resolve()) or ".." in Path(name).parts:
                raise SystemExit("Ungültiger Paketpfad.")
            inhalt = paket.read(name)
            if hashlib.sha256(inhalt).hexdigest() != sha:
                raise SystemExit("Paket-Prüfsumme stimmt nicht.")
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_bytes(inhalt)
    for datei in (stage / "backend/app").rglob("*.py"):
        compile(datei.read_text(encoding="utf-8-sig"), str(datei), "exec")
    if not (stage / "webapp/index.html").is_file():
        raise SystemExit("Die neue Oberfläche fehlt im Paket.")
    teile = ["backend/app", "backend/requirements.txt", "backend/requirements-pi.txt", "webapp"]
    if (root / "frontend/dist").exists():
        shutil.copytree(stage / "webapp", stage / "frontend/dist")
        teile.append("frontend/dist")
    with tarfile.open(sicherung / "vorher.tar.gz", "w:gz") as archiv:
        for name in teile:
            if (root / name).exists():
                archiv.add(root / name, arcname=name)
    ersetzt = []
    try:
        for name in teile:
            ziel = root / name
            alt = sicherung / "alt" / name
            alt.parent.mkdir(parents=True, exist_ok=True)
            ziel.parent.mkdir(parents=True, exist_ok=True)
            if ziel.exists():
                ziel.rename(alt)
            ersetzt.append(name)
            (stage / name).rename(ziel)
        if args.neustart:
            neustarten()
        print(f"Jon aktualisiert. Sicherung: {sicherung / 'vorher.tar.gz'}")
    except Exception:
        for name in reversed(ersetzt):
            ziel = root / name
            alt = sicherung / "alt" / name
            fehlversuch = sicherung / "fehlversuch" / name
            fehlversuch.parent.mkdir(parents=True, exist_ok=True)
            if ziel.exists():
                ziel.rename(fehlversuch)
            if alt.exists():
                alt.rename(ziel)
        if args.neustart:
            neustarten()
        raise


if __name__ == "__main__":
    ausfuehren()
