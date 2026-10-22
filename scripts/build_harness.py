import os
import re
import shutil
import subprocess
import sys
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ROOT / "terminal"
ICON = ROOT / "frontend" / "electron" / "icon.ico"
VERSION_DATEI = TERMINAL / "jon_harness" / "__init__.py"

VERSIONSINFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({a}, {b}, {c}, 0), prodvers=({a}, {b}, {c}, 0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040704B0', [
      StringStruct('CompanyName', 'FelWorks'),
      StringStruct('FileDescription', 'Jon Harness - Jon im Terminal'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'jon-harness'),
      StringStruct('LegalCopyright', 'FelWorks'),
      StringStruct('OriginalFilename', 'jon-harness.exe'),
      StringStruct('ProductName', 'Jon Harness'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [0x0407, 1200])])
  ]
)
"""


def version() -> str:
    treffer = re.search(r'VERSION = "([^"]+)"', VERSION_DATEI.read_text(encoding="utf-8"))
    if not treffer:
        raise SystemExit("Keine Version in terminal/jon_harness/__init__.py")
    return treffer.group(1)


def exe_bauen(ziel: Path) -> Path:
    arbeit = ROOT / "build" / "harness"
    shutil.rmtree(arbeit, ignore_errors=True)
    arbeit.mkdir(parents=True, exist_ok=True)
    v = version()
    a, b, c = (v.split(".") + ["0", "0", "0"])[:3]
    info = arbeit / "version.txt"
    info.write_text(VERSIONSINFO.format(a=int(a), b=int(b), c=int(c), v=v), encoding="utf-8")
    einstieg = arbeit / "jon_harness_start.py"
    einstieg.write_text("from jon_harness.start import main\n\nmain()\n", encoding="utf-8")
    befehl = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
        "--name", "jon-harness", "--distpath", str(arbeit / "dist"), "--workpath", str(arbeit / "work"),
        "--specpath", str(arbeit), "--paths", str(TERMINAL), "--version-file", str(info),
        "--collect-submodules", "jon_harness",
        "--exclude-module", "tkinter", "--exclude-module", "unittest", "--exclude-module", "pydoc",
    ]
    if ICON.is_file():
        befehl += ["--icon", str(ICON)]
    befehl.append(str(einstieg))
    umgebung = {k: v for k, v in os.environ.items() if k not in ("ELECTRON_RUN_AS_NODE", "NODE_OPTIONS")}
    subprocess.run(befehl, cwd=str(ROOT), check=True, env=umgebung)
    fertig = arbeit / "dist" / "jon-harness.exe"
    if not fertig.is_file():
        raise SystemExit("jon-harness.exe wurde nicht gebaut.")
    ziel.mkdir(parents=True, exist_ok=True)
    ausgabe = ziel / "jon-harness.exe"
    shutil.copy2(fertig, ausgabe)
    return ausgabe


def pyz_bauen(ziel: Path) -> Path:
    arbeit = ROOT / "build" / "harness-pyz"
    shutil.rmtree(arbeit, ignore_errors=True)
    shutil.copytree(TERMINAL / "jon_harness", arbeit / "jon_harness", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    ziel.mkdir(parents=True, exist_ok=True)
    ausgabe = ziel / "jon-harness.pyz"
    zipapp.create_archive(arbeit, ausgabe, interpreter="/usr/bin/env python3", main="jon_harness.start:main", compressed=True)
    return ausgabe


def main() -> None:
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "terminal" / "dist"
    exe = exe_bauen(ziel)
    pyz = pyz_bauen(ziel)
    print(f"EXE: {exe} ({exe.stat().st_size // 1024} KB)")
    print(f"PYZ: {pyz} ({pyz.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
