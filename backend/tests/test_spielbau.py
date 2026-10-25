from __future__ import annotations

import asyncio

from app.services import spielbau_service


def test_vorlage_schreibt_spielbares_spiel_mit_modellen(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "held.glb").write_bytes(b"glTF")
    (tmp_path / "assets" / "baum.glb").write_bytes(b"glTF")
    ergebnis = spielbau_service.vorlage(str(tmp_path), "Sternenjagd", "fahren", [])
    assert ergebnis["ok"] and ergebnis["art"] == "fahren"
    assert ergebnis["modelle"] == ["assets/baum.glb", "assets/held.glb"]
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    js = (tmp_path / "spiel.js").read_text(encoding="utf-8")
    assert "Sternenjagd" in html and "three@" + spielbau_service.THREE in html and "importmap" in html
    assert 'const ART = "fahren";' in js and '"assets/held.glb"' in js and "GLTFLoader" in js
    assert "//" not in js.replace("https://", "")


def test_vorlage_nimmt_angegebene_modelle_und_kennt_nur_echte_arten(tmp_path):
    ergebnis = spielbau_service.vorlage(str(tmp_path), "", "schwimmen", ["./assets/figur.glb", "assets\\haus.glb"])
    assert ergebnis["art"] == "laufen"
    assert ergebnis["modelle"] == ["assets/figur.glb", "assets/haus.glb"]


def test_ohne_projektordner_kommt_ein_klarer_hinweis():
    assert "pfad" in spielbau_service.vorlage("", "x")["error"]
    antwort = asyncio.run(spielbau_service.modell("ein rotes Auto", "auto", ""))
    assert "pfad" in antwort["error"]


def test_export_nimmt_nur_das_modell_ohne_boden_und_kamera(tmp_path):
    skript = spielbau_service.export_skript(tmp_path / "assets" / "auto.glb")
    assert "use_selection=True" in skript and "export_format='GLB'" in skript
    assert "boden" in skript and "jon_kamera" in skript
    compile(skript, "export", "exec")


def test_werkzeuge_sind_registriert():
    from app.services.tools import ToolBox
    from app.services.werkzeug_register import finden, finden_async, laden

    laden()
    assert finden_async("spiel_modell") is not None and finden("spiel_vorlage") is not None
    namen = {e["function"]["name"] for e in ToolBox()._eigene_tools()}
    assert {"spiel_modell", "spiel_vorlage"} <= namen
