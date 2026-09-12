from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from app.services import plattform
from app.services.dateiindex_service import get_dateiindex_service, karte, lesbar
from app.services.dateiraum_service import UNTERORDNER, get_dateiraum_service, saeubern
from app.services.dokument_service import get_dokument_service


@pytest.fixture()
def raum(tmp_path, monkeypatch):
    wurzel = tmp_path / "Jon"
    dienst = get_dateiraum_service()
    monkeypatch.setattr(dienst, "wurzel", lambda: wurzel)
    monkeypatch.setattr(
        dienst, "erlaubte_wurzeln", lambda: [wurzel.resolve(), tmp_path.resolve()]
    )
    dienst.sicherstellen()
    return dienst


def test_jon_ordner_entsteht_mit_allen_faechern(raum):
    wurzel = raum.wurzel()
    assert wurzel.is_dir()
    for name in UNTERORDNER:
        assert (wurzel / name).is_dir(), name


def test_namen_werden_entschaerft():
    assert saeubern('a/b:c*?.txt') == "a-bc.txt"
    assert saeubern("   ") == "Datei"
    assert len(saeubern("x" * 400 + ".pdf")) <= 110


def test_zielort_folgt_dem_wunsch_des_nutzers(raum, tmp_path, monkeypatch):
    schreibtisch = tmp_path / "Desktop"
    schreibtisch.mkdir()
    monkeypatch.setattr(
        "app.services.dateiraum_service.bekannte_ordner",
        lambda: {"desktop": schreibtisch, "dokumente": tmp_path / "Documents"},
    )
    ziel = raum.zielpfad("Pizza.pdf", "desktop")
    assert Path(ziel["ordner"]) == schreibtisch

    tiefer = raum.zielpfad("Pizza.pdf", "desktop/Meine Projekte/Essen")
    assert Path(tiefer["ordner"]) == schreibtisch / "Meine Projekte" / "Essen"
    assert Path(tiefer["ordner"]).is_dir()


def test_ohne_wunsch_sortiert_jon_nach_dateityp(raum):
    assert Path(raum.zielpfad("a.pdf")["ordner"]).name == "PDFs"
    assert Path(raum.zielpfad("a.docx")["ordner"]).name == "Documents"
    assert Path(raum.zielpfad("a.png")["ordner"]).name == "Images"
    assert Path(raum.zielpfad("a.py")["ordner"]).name == "Code"
    assert Path(raum.zielpfad("a.blend")["ordner"]).name == "Blender"
    assert Path(raum.zielpfad("a.unbekannt")["ordner"]).name == "Generated"


def test_nichts_wird_versehentlich_ueberschrieben(raum):
    erste = Path(raum.zielpfad("Bericht.pdf")["pfad"])
    erste.write_text("x", encoding="utf-8")
    zweite = Path(raum.zielpfad("Bericht.pdf")["pfad"])
    assert zweite != erste
    assert zweite.name == "Bericht-2.pdf"


def test_systemordner_bleiben_gesperrt(raum):
    gesperrt = [
        Path("C:/Windows/System32/drivers"),
        Path("/etc/passwd"),
        Path("C:/Program Files/Jon"),
    ]
    for pfad in gesperrt:
        erlaubt, grund = raum.frei(pfad)
        assert erlaubt is False, pfad
        assert grund


def test_ausbruch_aus_dem_freigegebenen_bereich_wird_gestoppt(raum, tmp_path):
    erlaubt, grund = raum.frei(tmp_path.parent / "woanders" / "geheim.txt")
    assert erlaubt is False
    assert "ausserhalb" in grund.lower()


def test_pfadtricks_greifen_nicht(raum):
    ergebnis = raum.zielordner("../../../../Windows/System32")
    assert ergebnis.get("error")


@pytest.mark.parametrize("art", ["pdf", "docx", "odt", "txt", "md", "html"])
def test_textdokumente_entstehen_wirklich(raum, art):
    ergebnis = get_dokument_service().erstellen(
        art, "Gesunde Ernaehrung", "# Gesunde Ernaehrung\n\nViel Gemuese.\n\n- Obst\n- Wasser"
    )
    assert not ergebnis.get("error"), ergebnis
    datei = Path(ergebnis["datei"]["path"])
    assert datei.is_file() and datei.stat().st_size > 0
    assert ergebnis["datei"]["actions"] == ["open", "download", "open_folder"]
    assert ergebnis["datei"]["type"] == "file"


def test_pdf_enthaelt_den_text_nur_einmal(raum):
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    ergebnis = get_dokument_service().erstellen(
        "pdf", "Pizza", "# Pizza\n\nTeig ruhen lassen.\n\n- Mehl\n- Hefe\n\n1. Kneten\n2. Backen"
    )
    text = PdfReader(ergebnis["datei"]["path"]).pages[0].extract_text()
    assert text.count("Pizza") == 1
    assert "Teig ruhen lassen" in text
    assert "\x7f" not in text


@pytest.mark.parametrize("art", ["xlsx", "ods", "csv"])
def test_tabellen_entstehen_mit_kopfzeile(raum, art):
    zeilen = [["Zutat", "Menge"], ["Mehl", "500g"], ["Hefe", "1 Wuerfel"]]
    ergebnis = get_dokument_service().erstellen(art, "Einkauf", zeilen)
    assert not ergebnis.get("error"), ergebnis
    assert Path(ergebnis["datei"]["path"]).stat().st_size > 0


def test_xlsx_hat_die_richtigen_werte(raum):
    pytest.importorskip("openpyxl")
    import openpyxl

    zeilen = [["Zutat", "Menge"], ["Mehl", "500g"]]
    ergebnis = get_dokument_service().erstellen("xlsx", "Einkauf", zeilen)
    blatt = openpyxl.load_workbook(ergebnis["datei"]["path"]).active
    assert [[z.value for z in r] for r in blatt.iter_rows()] == zeilen
    assert blatt["A1"].font.bold is True


def test_unbekannter_dateityp_wird_ehrlich_abgelehnt(raum):
    ergebnis = get_dokument_service().erstellen("dwg", "Plan", "x")
    assert ergebnis.get("error")
    assert "moeglich" in ergebnis


def test_datei_landet_im_index_und_ist_wiederfindbar(raum):
    get_dokument_service().erstellen(
        "pdf", "Italienisches Essen", "# Italienisches Essen\n\nPasta und Pizza."
    )
    treffer = get_dateiindex_service().suchen("die PDF ueber Essen")
    assert treffer, "nichts gefunden"
    assert "Essen" in treffer[0]["titel"]


def test_index_merkt_wenn_eine_datei_verschwindet(raum):
    ergebnis = get_dokument_service().erstellen("txt", "Weg", "verschwindet")
    Path(ergebnis["datei"]["path"]).unlink()
    assert get_dateiindex_service().pruefen()["verschwunden"] >= 1


def test_dateikarte_hat_alles_was_die_oberflaeche_braucht(raum):
    ergebnis = get_dokument_service().erstellen("txt", "Karte", "Inhalt")
    daten = ergebnis["datei"]
    for schluessel in (
        "type",
        "name",
        "path",
        "mimeType",
        "size",
        "sizeText",
        "folder",
        "actions",
    ):
        assert schluessel in daten, schluessel
    assert daten["mimeType"] == "text/plain"
    assert daten["exists"] is True


def test_groessen_lesbar():
    assert lesbar(0) == "0 B"
    assert lesbar(2048) == "2.0 KB"
    assert lesbar(5 * 1024 * 1024) == "5.0 MB"


def test_werkzeug_erstellt_datei_und_liefert_karte(raum):
    from app.services.tools import ToolBox

    ergebnis = asyncio.run(
        ToolBox().execute(
            "datei_erstellen",
            {"art": "md", "titel": "Notiz", "inhalt": "# Notiz\n\nText."},
        )
    )
    daten = json.loads(ergebnis)
    assert daten["ok"] is True
    assert Path(daten["datei"]["path"]).is_file()


def test_chatkarte_entsteht_aus_dem_werkzeugergebnis(raum):
    from app.services.chat_service import card_payload

    ergebnis = get_dokument_service().erstellen("txt", "Karte", "Inhalt")
    karte_ = card_payload("datei_erstellen", json.dumps(ergebnis, ensure_ascii=False))
    assert karte_["kind"] == "datei"
    assert karte_["data"]["dateien"][0]["name"].endswith(".txt")


def test_mehrere_dateien_landen_in_einer_karte():
    from app.services.chat_service import card_payload

    roh = json.dumps(
        {
            "ok": True,
            "dateien": [
                {"path": "/a/x.blend", "name": "x.blend"},
                {"path": "/a/x.png", "name": "x.png"},
                {"path": "/a/x.png", "name": "x.png"},
            ],
        }
    )
    karte_ = card_payload("blender_szene", roh)
    assert len(karte_["data"]["dateien"]) == 2


def test_ordner_werkzeug_legt_an_und_bleibt_im_rahmen(raum):
    from app.services.tools import ToolBox

    ergebnis = json.loads(
        asyncio.run(
            ToolBox().execute("ordner_anlegen", {"name": "YouTube Projekt"})
        )
    )
    assert ergebnis["ok"] is True
    assert Path(ergebnis["ordner"]).is_dir()

    verboten = json.loads(
        asyncio.run(
            ToolBox().execute(
                "ordner_anlegen", {"name": "x", "ort": "C:/Windows/System32"}
            )
        )
    )
    assert verboten.get("error")


def test_oeffnen_ausserhalb_des_rahmens_wird_verweigert(raum, tmp_path):
    from app.services.tools import ToolBox

    ergebnis = json.loads(
        asyncio.run(
            ToolBox().execute(
                "datei_oeffnen", {"pfad": str(tmp_path.parent / "fremd.txt")}
            )
        )
    )
    assert ergebnis.get("error")


def test_plattform_kennt_dieses_system():
    assert plattform.name() in ("windows", "macos", "linux")
    assert plattform.dateimanager()
    assert plattform.datei_oeffnen("/gibt/es/nicht/wirklich.txt").get("error")


def test_plattform_findet_vorhandene_werkzeuge():
    ergebnis = plattform.werkzeug_da("python")
    assert ergebnis["da"] is True
    assert plattform.werkzeug_da("gibt-es-sicher-nicht-xyz")["da"] is False


def test_umgebung_meldet_was_fehlt():
    from app.services.umgebung_service import get_umgebung_service

    stand = get_umgebung_service().pruefen(neu=True)
    assert stand["plattform"] in ("windows", "macos", "linux")
    namen = {w["befehl"] for w in stand["werkzeuge"]}
    assert {"python", "git", "blender"} <= namen
    assert isinstance(stand["fehlt"], list)
    assert any(p["modul"] == "reportlab" for p in stand["pakete"])


def _stub_blender(tmp_path: Path) -> Path:
    skript = tmp_path / "blender_stub.py"
    skript.write_text(
        "import sys, re\n"
        "args = sys.argv[1:]\n"
        "if '--version' in args:\n"
        "    print('Blender 4.2.0 (stub)')\n"
        "    sys.exit(0)\n"
        "pfad = args[args.index('--python') + 1]\n"
        "quelle = open(pfad, encoding='utf-8').read()\n"
        "if 'ABSICHTLICHER_FEHLER' in quelle:\n"
        "    print('Error: name \\'ABSICHTLICHER_FEHLER\\' is not defined')\n"
        "    sys.exit(1)\n"
        "for muster in (r'save_as_mainfile\\(filepath=\"(.*?)\"',"
        " r'render.filepath = \"(.*?)\"', r'filepath=\"(.*?)\"'):\n"
        "    treffer = re.search(muster, quelle)\n"
        "    if treffer:\n"
        "        open(treffer.group(1), 'wb').write(b'JONSTUB')\n"
        "        break\n"
        "print('JON_OK objekte=3')\n",
        encoding="utf-8",
    )
    if sys.platform == "win32":
        starter = tmp_path / "blender.cmd"
        starter.write_text(
            f'@echo off\r\n"{sys.executable}" "{skript}" %*\r\n', encoding="utf-8"
        )
    else:
        starter = tmp_path / "blender.sh"
        starter.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{skript}" "$@"\n', encoding="utf-8"
        )
        starter.chmod(0o755)
    return starter


@pytest.fixture()
def blender(raum, tmp_path, monkeypatch):
    from app.services.blender_service import get_blender_service

    starter = _stub_blender(tmp_path)
    dienst = get_blender_service()
    monkeypatch.setattr(dienst, "_suchen", lambda: str(starter))
    dienst._pfad = None
    dienst._version = ""
    return dienst


def test_blender_wird_erkannt_und_gemeldet(blender):
    stand = blender.gefunden(neu=True)
    assert stand["da"] is True
    assert "4.2.0" in stand["version"]


def test_fehlendes_blender_wird_ehrlich_gemeldet(raum, monkeypatch):
    from app.services.blender_service import get_blender_service

    dienst = get_blender_service()
    monkeypatch.setattr(dienst, "_suchen", lambda: "")
    dienst._pfad = None
    stand = dienst.gefunden(neu=True)
    assert stand["da"] is False
    assert "blender.org" in stand["hinweis"]
    ergebnis = asyncio.run(dienst.szene("ein Wuerfel"))
    assert ergebnis["error"] == stand["hinweis"]


def test_blender_szene_entsteht_rendert_und_exportiert(blender, monkeypatch):
    async def _complete(system, user, *args, **kwargs):
        return "```python\nimport bpy\nbpy.ops.mesh.primitive_cube_add()\n```"

    monkeypatch.setattr("app.services.llm.complete", _complete)
    ergebnis = asyncio.run(
        blender.szene("ein Wuerfel mit Metall", projekt="Wuerfel", export="glb")
    )
    assert ergebnis.get("ok") is True, ergebnis
    assert Path(ergebnis["blend"]).is_file()
    assert ergebnis["render"] and Path(ergebnis["render"]["path"]).is_file()
    assert ergebnis["export"] == ["glb"]
    assert len(ergebnis["dateien"]) == 3
    assert ergebnis["versuche"] == 1


def test_blender_repariert_ein_fehlerhaftes_skript(blender, monkeypatch):
    versuche = {"n": 0}

    async def _complete(system, user, *args, **kwargs):
        versuche["n"] += 1
        if versuche["n"] == 1:
            return "import bpy\nABSICHTLICHER_FEHLER\n"
        return "import bpy\nbpy.ops.mesh.primitive_cube_add()\n"

    monkeypatch.setattr("app.services.llm.complete", _complete)
    ergebnis = asyncio.run(blender.szene("ein Wuerfel", rendern=False))
    assert ergebnis.get("ok") is True, ergebnis
    assert ergebnis["versuche"] == 2
    assert ergebnis["protokoll"][0]["ok"] is False
    assert "not defined" in ergebnis["protokoll"][0]["fehler"]


def test_blender_gibt_nach_drei_versuchen_ehrlich_auf(blender, monkeypatch):
    async def _complete(system, user, *args, **kwargs):
        return "import bpy\nABSICHTLICHER_FEHLER\n"

    monkeypatch.setattr("app.services.llm.complete", _complete)
    ergebnis = asyncio.run(blender.szene("ein Wuerfel", rendern=False))
    assert ergebnis.get("error")
    assert "3 Versuchen" in ergebnis["error"]
    assert len(ergebnis["protokoll"]) == 3


def test_blender_laesst_kein_systemzugriff_skript_durch(blender, monkeypatch):
    async def _complete(system, user, *args, **kwargs):
        return "import bpy\nimport os\nos.system('echo weg')\n"

    monkeypatch.setattr("app.services.llm.complete", _complete)
    ergebnis = asyncio.run(blender.szene("boeses Skript", rendern=False))
    assert ergebnis.get("error")
    assert "System oder Netzwerk" in ergebnis["protokoll"][0]["fehler"]


def test_blender_export_kennt_nur_echte_formate(blender, tmp_path):
    datei = tmp_path / "x.blend"
    datei.write_bytes(b"JONSTUB")
    assert blender.exportieren(datei, "docx").get("error")
    assert blender.exportieren(datei, "glb").get("ok") is True


def test_telegram_sammelt_dateien_aus_den_karten():
    from app.services.telegram_service import TelegramService

    karten = [
        {"kind": "datei", "data": {"dateien": [{"path": "/a/x.pdf", "name": "x.pdf"}]}},
        {"kind": "datei", "data": {"dateien": [{"path": "/a/x.pdf", "name": "x.pdf"}]}},
        {"kind": "maps", "data": {}},
    ]
    dateien = TelegramService._karten_dateien(karten)
    assert len(dateien) == 1
    assert dateien[0]["name"] == "x.pdf"


def test_karte_fuer_fehlende_datei_sagt_die_wahrheit(tmp_path):
    daten = karte(tmp_path / "gibtsnicht.pdf")
    assert daten["exists"] is False
    assert daten["size"] == 0


@pytest.mark.parametrize(
    "werkzeug",
    [
        "datei_erstellen",
        "ordner_anlegen",
        "datei_oeffnen",
        "ordner_oeffnen",
        "dateien_finden",
        "dateiraum",
        "umgebung",
        "blender_szene",
        "blender_render",
        "blender_export",
    ],
)
def test_werkzeuge_sind_vollstaendig_angemeldet(werkzeug):
    from app.services.tools import describe_tool, werkzeugnamen
    from app.services.werkzeug_register import finden, finden_async

    assert werkzeug in werkzeugnamen()
    assert finden(werkzeug) or finden_async(werkzeug)
    assert describe_tool(werkzeug, {}) != werkzeug


def test_auswahl_findet_die_werkstatt_bei_normaler_sprache():
    from app.services.tools import select_tools

    for satz, erwartet in (
        ("erstelle mir eine pdf ueber gesunde ernaehrung", "datei_erstellen"),
        ("speicher das auf dem desktop", "datei_erstellen"),
        ("mach einen ordner namens YouTube Projekt", "ordner_anlegen"),
        ("erstelle einen blender wuerfel mit metall", "blender_szene"),
        ("wo liegt die tabelle von letzter woche", "dateien_finden"),
    ):
        auswahl = select_tools(satz)
        assert auswahl is None or erwartet in auswahl, satz


def test_shell_ausgabe_ueberlebt_sonderzeichen():
    from app.services.system_service import SystemService

    dienst = SystemService()
    if sys.platform == "win32":
        ergebnis = dienst.run_cmd("echo Gruesse fuer Jon")
    else:
        ergebnis = dienst.run_cmd("echo Gruesse fuer Jon")
    assert ergebnis.exit_code == 0
    assert "Gruesse fuer Jon" in ergebnis.stdout


def test_shell_vertraegt_mehrfach_zitierte_befehle(tmp_path):
    from app.services.system_service import SystemService

    ziel = tmp_path / "ein ordner mit leerzeichen"
    ziel.mkdir()
    (ziel / "beweis.txt").write_text("da", encoding="utf-8")
    dienst = SystemService()
    if sys.platform == "win32":
        befehl = f'cd /d "{ziel}" && "{sys.executable}" -c "print(open(\'beweis.txt\').read())"'
    else:
        befehl = f'cd "{ziel}" && "{sys.executable}" -c "print(open(\'beweis.txt\').read())"'
    ergebnis = dienst.run_cmd(befehl)
    assert ergebnis.exit_code == 0, ergebnis.stderr
    assert "da" in ergebnis.stdout


def test_shell_dekodiert_umlaute_statt_abzustuerzen():
    from app.services.system_service import SystemService

    dienst = SystemService()
    if sys.platform != "win32":
        return
    ergebnis = dienst.run_powershell("Write-Output 'Groesse und Grüße'")
    assert ergebnis.exit_code == 0
    assert "Grüße" in ergebnis.stdout
