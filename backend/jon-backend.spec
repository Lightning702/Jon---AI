# -*- mode: python ; coding: utf-8 -*-
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

APP_VERSION = re.search(
    r'app_version: str = "([^"]+)"',
    (Path(SPECPATH) / "app" / "core" / "config.py").read_text(encoding="utf-8"),
).group(1)

_nums = tuple(int(p) for p in APP_VERSION.split("."))[:4]
_nums = _nums + (0,) * (4 - len(_nums))

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_nums, prodvers=_nums),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040704B0",
                    [
                        StringStruct("CompanyName", "Felix / Jon Projekt"),
                        StringStruct(
                            "FileDescription",
                            "Jon Backend - KI-Desktop-Assistent (laeuft nur lokal)",
                        ),
                        StringStruct("FileVersion", APP_VERSION),
                        StringStruct("InternalName", "jon-backend"),
                        StringStruct("LegalCopyright", "(c) 2026 Felix, MIT-Lizenz"),
                        StringStruct("OriginalFilename", "jon-backend.exe"),
                        StringStruct("ProductName", "Jon"),
                        StringStruct("ProductVersion", APP_VERSION),
                        StringStruct(
                            "Comments",
                            "Open Source: github.com/Lightning702/Jon---AI",
                        ),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1031, 1200])]),
    ],
)

datas = []
binaries = []
hiddenimports = []

for pkg in (
    "openwakeword",
    "edge_tts",
    "playwright",
    "cv2",
    "sounddevice",
    "onnxruntime",
    "speech_recognition",
    "anthropic",
    "openai",
    "google.generativeai",
    "paho",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += collect_submodules("app")
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "pydantic_settings",
    "sqlalchemy.dialects.sqlite",
]

datas += [("app/static", "app/static")]

a = Analysis(
    ["run_backend.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jon-backend",
    console=True,
    disable_windowed_traceback=False,
    icon="../frontend/electron/icon.ico",
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="jon-backend",
)
