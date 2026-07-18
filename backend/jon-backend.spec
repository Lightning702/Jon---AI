# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

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
    console=False,
    disable_windowed_traceback=False,
    icon="../frontend/electron/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="jon-backend",
)
