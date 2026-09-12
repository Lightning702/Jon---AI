import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
RELEASE = FRONTEND / "release"


def run(cmd: str, cwd: Path) -> None:
    print(f"\n> {cmd}")
    env = dict(os.environ)
    env.pop("ELECTRON_RUN_AS_NODE", None)
    env.pop("NODE_OPTIONS", None)
    subprocess.run(cmd, cwd=str(cwd), check=True, env=env, shell=True)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        run(f'"{sys.executable}" -m pip install --disable-pip-version-check pyinstaller', ROOT)


def build_backend() -> None:
    shutil.rmtree(BACKEND / "build", ignore_errors=True)
    shutil.rmtree(BACKEND / "dist", ignore_errors=True)
    liste = "requirements.lock" if (BACKEND / "requirements.lock").exists() else "requirements.txt"
    run(f'"{sys.executable}" -m pip install --disable-pip-version-check -r {liste}', BACKEND)
    run(f'"{sys.executable}" -m PyInstaller --noconfirm --clean jon-backend.spec', BACKEND)
    exe = BACKEND / "dist" / "jon-backend" / "jon-backend.exe"
    if not exe.exists():
        raise SystemExit("jon-backend.exe wurde nicht erstellt.")


def build_frontend() -> None:
    if not (FRONTEND / "node_modules").exists():
        run("npm install", FRONTEND)
    run("npm run build", FRONTEND)


def build_installer() -> None:
    run("npx electron-builder --config installer.config.json", FRONTEND)
    setup = RELEASE / "Jon-Setup.exe"
    if not setup.exists():
        raise SystemExit("Jon-Setup.exe wurde nicht erstellt.")


ICON = FRONTEND / "electron" / "icon.ico"
EINRICHTER_NAME = "Jon einrichten.exe"

LIESMICH = r"""Jon - portable Fassung

So richtest du Jon ein:

1. Diesen Ordner an einen festen Platz entpacken, zum Beispiel nach
   C:\Users\<du>\Jon. Nicht aus dem ZIP heraus starten.
2. "Jon einrichten.exe" doppelklicken. Das legt ein Jon-Symbol auf dem
   Desktop und im Startmenue an und startet Jon gleich.
3. Ab dann startest du Jon ueber das Desktop-Symbol.

Du kannst Jon auch direkt per Doppelklick auf Jon.exe starten - beim
ersten Mal bietet er das Desktop-Symbol dann selbst an.

Jon braucht keine Installation. Alles - App, Oberflaeche und Backend -
liegt in diesem Ordner. Deine Daten und Einstellungen legt Jon unter
%LOCALAPPDATA%\Jon ab.

Willst du das Symbol spaeter neu anlegen oder entfernen, sag Jon einfach
"leg mir ein Desktop-Symbol an" oder "entfern das Desktop-Symbol".

Windows meldet beim ersten Start eventuell SmartScreen, weil die Dateien
nicht signiert sind: Weitere Informationen -> Trotzdem ausfuehren.
"""


def build_einrichter() -> Path | None:
    quelle = ROOT / "scripts" / "jon_einrichten.py"
    if not quelle.is_file():
        raise SystemExit("scripts/jon_einrichten.py fehlt.")
    arbeit = ROOT / "build" / "einrichter"
    shutil.rmtree(arbeit, ignore_errors=True)
    arbeit.mkdir(parents=True, exist_ok=True)
    befehl = (
        f'"{sys.executable}" -m PyInstaller --noconfirm --clean --onefile '
        f'--name "Jon einrichten" --distpath "{arbeit / "dist"}" '
        f'--workpath "{arbeit / "work"}" --specpath "{arbeit}" '
    )
    if ICON.is_file():
        befehl += f'--icon "{ICON}" '
    befehl += f'"{quelle}"'
    try:
        run(befehl, ROOT)
    except subprocess.CalledProcessError:
        print("  Einrichter-EXE liess sich nicht bauen - das ZIP kommt ohne sie.")
        return None
    fertig = arbeit / "dist" / EINRICHTER_NAME
    return fertig if fertig.is_file() else None


def build_portable_zip() -> Path:
    einrichter = build_einrichter()
    unpacked = RELEASE / "win-unpacked"
    if not unpacked.exists():
        raise SystemExit("win-unpacked fehlt - electron-builder zuerst laufen lassen.")
    target = RELEASE / "Jon-Windows.zip"
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(unpacked.rglob("*")):
            rel = "Jon/" + path.relative_to(unpacked).as_posix()
            if path.is_dir():
                continue
            z.write(path, rel)
        if einrichter is not None and einrichter.is_file():
            z.write(einrichter, "Jon/" + EINRICHTER_NAME)
        if ICON.is_file() and not (unpacked / "resources" / "icon.ico").is_file():
            z.write(ICON, "Jon/resources/icon.ico")
        z.writestr("Jon/LIESMICH.txt", LIESMICH)
    return target


def write_checksums(paths: list[Path]) -> Path:
    target = RELEASE / "SHA256SUMS.txt"
    zeilen = []
    for path in paths:
        sha = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1_048_576), b""):
                sha.update(block)
        zeilen.append(f"{sha.hexdigest()}  {path.name}")
    target.write_text(chr(10).join(zeilen) + chr(10), encoding="utf-8")
    return target


def main() -> None:
    ensure_pyinstaller()
    build_backend()
    build_frontend()
    build_installer()
    portable = build_portable_zip()
    print("\nFertig!")
    summen = write_checksums([RELEASE / "Jon-Setup.exe", portable])
    print(f"Installer: {RELEASE / 'Jon-Setup.exe'}")
    print(f"Portabel:  {portable}")
    print(f"Pruefsummen: {summen}")


if __name__ == "__main__":
    main()
