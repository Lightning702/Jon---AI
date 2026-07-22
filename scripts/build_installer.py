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
    run(f'"{sys.executable}" -m pip install --disable-pip-version-check -r requirements.txt', BACKEND)
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


def build_portable_zip() -> Path:
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
    return target


def main() -> None:
    ensure_pyinstaller()
    build_backend()
    build_frontend()
    build_installer()
    portable = build_portable_zip()
    print("\nFertig!")
    print(f"Installer: {RELEASE / 'Jon-Setup.exe'}")
    print(f"Portabel:  {portable}")


if __name__ == "__main__":
    main()
