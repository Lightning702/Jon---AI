from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api import mobile_routes as mobile


class Raum:
    def __init__(self, wurzel: Path):
        self.wurzel = wurzel

    def sicherstellen(self) -> Path:
        self.wurzel.mkdir(parents=True, exist_ok=True)
        return self.wurzel

    def ordner(self, name: str) -> Path:
        ziel = self.sicherstellen() / name
        ziel.mkdir(parents=True, exist_ok=True)
        return ziel

    def frei(self, pfad: Path):
        ziel = Path(pfad).resolve()
        wurzel = self.wurzel.resolve()
        return (ziel == wurzel or wurzel in ziel.parents), "Außerhalb"


@pytest.fixture
def raum(monkeypatch, tmp_path):
    raum = Raum(tmp_path / "Jon")
    raum.sicherstellen()
    monkeypatch.setattr(mobile, "get_dateiraum_service", lambda: raum)
    return raum


def test_rohdatei_mit_webtyp(raum):
    seite = raum.ordner("Projects") / "Websites" / "demo"
    seite.mkdir(parents=True)
    (seite / "app.mjs").write_text("export const x = 1;", encoding="utf-8")
    antwort = mobile.raw_file(str(seite / "app.mjs"))
    assert antwort.media_type == "text/javascript"
    assert antwort.body == b"export const x = 1;"
    with pytest.raises(HTTPException):
        mobile.raw_file(str(raum.wurzel.parent / "fremd.txt"))


def test_zip_packt_den_ordner_ohne_muell(raum):
    seite = raum.ordner("Projects") / "Websites" / "demo"
    (seite / "node_modules").mkdir(parents=True)
    (seite / "index.html").write_text("<h1>Hallo</h1>", encoding="utf-8")
    (seite / "style.css").write_text("h1{color:red}", encoding="utf-8")
    (seite / "node_modules" / "gross.js").write_text("x", encoding="utf-8")
    ergebnis = mobile.zip_folder({"path": str(seite / "index.html")})
    assert ergebnis["dateien"] == 2
    with zipfile.ZipFile(ergebnis["pfad"]) as archiv:
        assert sorted(archiv.namelist()) == ["demo/index.html", "demo/style.css"]
    with pytest.raises(HTTPException):
        mobile.zip_folder({"path": str(raum.wurzel)})


def test_python_datei_ausfuehren(raum):
    skript = raum.ordner("Code") / "hallo.py"
    skript.write_text("import sys\nprint('Hallo Jon', sys.argv[1:])\n", encoding="utf-8")
    ergebnis = asyncio.run(mobile.run_file({"path": str(skript), "args": ["a"]}))
    assert ergebnis["exit_code"] == 0
    assert "Hallo Jon ['a']" in ergebnis["stdout"]
    fremd = raum.ordner("Code") / "bild.png"
    fremd.write_bytes(b"x")
    with pytest.raises(HTTPException):
        asyncio.run(mobile.run_file({"path": str(fremd)}))


def test_befehle_hilfe_und_unbekannt():
    hilfe = asyncio.run(mobile.command({"text": "/hilfe"}))
    assert any(b["name"] == "/video" for b in hilfe["befehle"])
    assert "unbekannt" not in hilfe["text"].lower()
    unbekannt = asyncio.run(mobile.command({"text": "/quatsch"}))
    assert "kenne ich nicht" in unbekannt["text"]
    with pytest.raises(HTTPException):
        asyncio.run(mobile.command({"text": "hallo"}))


def test_video_befehl(monkeypatch, raum, tmp_path):
    import app.services.bildschirm_video as video

    quelle = tmp_path / "clip.mp4"
    quelle.write_bytes(b"\0" * 2048)
    aufrufe = []

    async def clip(welcher="maus", sekunden=10.0):
        aufrufe.append((welcher, sekunden))
        return quelle

    monkeypatch.setattr(video, "clip", clip)
    antwort = asyncio.run(mobile.command({"text": "/video 999 alle"}))
    assert aufrufe == [("alle", 60.0)]
    assert Path(antwort["video"]["pfad"]).is_file()
    assert antwort["video"]["pfad"].endswith(".mp4")


def test_werkzeug_umfang():
    from app.services.tools import CODING_TOOLS, KLEIN_TOOLS, ToolBox

    box = ToolBox()
    klein = {t["function"]["name"] for t in box.schema("mach mir eine website", umfang="klein")}
    assert "run_cmd" not in klein and "write_file" not in klein
    assert klein <= KLEIN_TOOLS | {n for n in klein if n.startswith("fitness_")}
    alle = {t["function"]["name"] for t in box.schema("baue eine website und erstelle ein bild", coding=True, umfang="alle")}
    assert CODING_TOOLS & alle == CODING_TOOLS & {t["function"]["name"] for t in box._all_tools()}
    assert "create_image" in alle and "datei_erstellen" in alle
    nur_code = {t["function"]["name"] for t in box.schema("baue eine website", coding=True)}
    assert "create_image" not in nur_code


def test_alles_erlauben_ist_gueltig():
    from app.schemas import ChatIn

    assert ChatIn(messages=[], tool_mode="alles").tool_mode == "alles"
    with pytest.raises(Exception):
        ChatIn(messages=[], tool_mode="immer")
