from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.cli import kunst
from app.cli.sitzung import (
    VSCODE_MARKEN,
    JonTerminal,
    baum,
    in_vscode,
    ist_projekt,
)

WURZEL = Path(__file__).resolve().parents[2]


@pytest.fixture
def stift():
    return kunst.Stift()


@pytest.fixture
def ohne_editor(monkeypatch):
    for name in VSCODE_MARKEN + ("TERM_PROGRAM", "GIT_ASKPASS", "TERMINAL_EMULATOR"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _ohne_editor(umgebung: dict) -> dict:
    for name in VSCODE_MARKEN + ("TERM_PROGRAM", "GIT_ASKPASS", "TERMINAL_EMULATOR"):
        umgebung.pop(name, None)
    return umgebung


async def _leer(*args, **kwargs):
    return None


def test_banner_zeigt_logo_menue_und_figur(stift):
    text = kunst.kopf(stift, "4.51.3", "Felix", False)
    assert "Hallo Felix!" in text
    assert "v4.51.3" in text
    for eintrag in ("Chat", "Code", "Dateien", "System", "Browser", "Projekte"):
        assert eintrag in text
    for eintrag in ("Tools", "Memory", "Agent", "Einstellungen"):
        assert eintrag in text
    assert "███   ███" in text
    assert "Einfach jon" in text
    assert "ÜBERALL." in text and "DEIN JON." in text


def test_banner_bleibt_im_schmalen_terminal_lesbar(stift):
    text = kunst.kopf(stift, "4.51.3", "Felix", True)
    assert "███" not in text
    assert max(len(z) for z in text.splitlines()) < 80


def test_banner_zeilen_sind_gleich_lang(stift):
    zeilen = kunst.kopf(stift, "4.51.3", "Felix", False).splitlines()
    anfang = [z.index("╭") for z in zeilen if "╭" in z and z.strip().startswith("╭")]
    assert anfang and len(set(anfang)) == 1


def test_hilfe_zeigt_beispiele_und_orte(stift):
    text = kunst.hilfe(stift, False)
    assert "erkläre mir dieses Projekt" in text
    assert "Windows CMD" in text and "PowerShell" in text
    assert "macOS Terminal (zsh, bash)" in text and "Linux Terminal" in text
    assert "Als globaler Befehl: jon" in text
    for befehl in ("chat", "code", "tools", "memory", "projekte", "ende"):
        assert befehl in text


def test_hilfe_bricht_nicht_um(stift):
    for zeile in kunst.hilfe(stift, False).splitlines():
        assert "│" not in zeile or zeile.count("│") >= 2


def test_vscode_wird_erkannt(ohne_editor):
    ohne_editor.setenv("TERM_PROGRAM", "vscode")
    assert in_vscode() is True
    ohne_editor.setenv("TERM_PROGRAM", "Apple_Terminal")
    assert in_vscode() is False
    ohne_editor.setenv("VSCODE_PID", "1234")
    assert in_vscode() is True


def test_vscode_wird_auch_ohne_term_program_erkannt(ohne_editor):
    assert in_vscode() is False
    ohne_editor.setenv("VSCODE_GIT_ASKPASS_NODE", r"C:\\Code\\node.exe")
    assert in_vscode() is True


def test_projekt_wird_erkannt(tmp_path):
    assert ist_projekt(tmp_path) is False
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    assert ist_projekt(tmp_path) is True


def test_einzelne_codedatei_zaehlt_schon_als_projekt(tmp_path):
    (tmp_path / "notiz.txt").write_text("x", encoding="utf-8")
    assert ist_projekt(tmp_path) is False
    (tmp_path / "index.html").write_text("<h1>x</h1>", encoding="utf-8")
    assert ist_projekt(tmp_path) is True


def test_baum_ueberspringt_ballast(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "krams.js").write_text("x", encoding="utf-8")
    (tmp_path / "liesmich.md").write_text("x", encoding="utf-8")
    zeilen, dateien, ordner = baum(tmp_path, 2)
    text = "\n".join(zeilen)
    assert "main.py" in text and "liesmich.md" in text
    assert "node_modules" not in text and "krams.js" not in text
    assert dateien == 2 and ordner == 1


def test_terminal_startet_im_codemodus_in_vscode(ohne_editor, tmp_path):
    leer = tmp_path / "leer"
    leer.mkdir()
    ohne_editor.chdir(leer)
    assert JonTerminal().modus == "chat"
    ohne_editor.setenv("TERM_PROGRAM", "vscode")
    terminal = JonTerminal()
    assert terminal.modus == "code"
    assert terminal.editor == "VS Code"
    ohne_editor.setenv("TERM_PROGRAM", "xterm")
    assert JonTerminal().modus == "chat"
    assert JonTerminal("code").modus == "code"


def test_terminal_startet_im_projektordner_im_codemodus(ohne_editor, tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    ohne_editor.chdir(tmp_path)
    assert JonTerminal().modus == "code"
    assert JonTerminal("chat").modus == "chat"


def test_jon_antwortet_ohne_anbieter_mit_klartext(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    terminal.anbieter = "gibtesnicht"
    import asyncio

    asyncio.run(terminal._runde("hallo"))
    assert "Fehler" in capsys.readouterr().out


def test_befehle_gehen_nicht_ans_modell(monkeypatch, tmp_path, capsys):
    import asyncio

    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    assert asyncio.run(terminal._befehl("hilfe")) is True
    assert "Windows CMD" in capsys.readouterr().out
    assert asyncio.run(terminal._befehl("ende")) is False
    assert asyncio.run(terminal._befehl("code")) is True
    assert terminal.modus == "code"
    assert asyncio.run(terminal._befehl("chat")) is True
    assert terminal.modus == "chat"


def test_unbekanntes_wort_bleibt_eine_frage(monkeypatch, tmp_path):
    import asyncio

    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    assert asyncio.run(terminal._befehl("erklaer mir das")) is True


def test_satz_mit_befehlswort_ist_kein_befehl(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    for satz in (
        "Code mir mit HTML eine Website",
        "Code mir ein 3d spiel nutze nicht nur index.html",
        "chat fenster bauen",
        "tools fuer den build zeigen",
        "hilfe beim debuggen",
        "agent fuer meine tests schreiben",
    ):
        assert terminal._ist_befehl(satz) is False
    for befehl in (
        "code",
        "  chat  ",
        "TOOLS",
        "/code",
        "/code mir eine Website",
        "modell 3",
        "anbieter ollama",
    ):
        assert terminal._ist_befehl(befehl) is True


def test_saetze_gehen_ans_modell_befehle_nicht(monkeypatch, tmp_path):
    import asyncio

    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    gefragt: list[str] = []

    async def _runde(text: str) -> None:
        gefragt.append(text)

    async def _wege():
        return []

    monkeypatch.setattr(terminal, "_runde", _runde)
    monkeypatch.setattr(terminal, "_wege", _wege)
    monkeypatch.setattr(terminal, "_modell_pruefen", _leer)
    zeilen = iter(
        [
            "Code mir mit HTML eine Website",
            "code",
            "Code mir ein 3d spiel nutze nicht nur index.html",
            "/code bau mir ein Menue",
            "ende",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda *args: next(zeilen))
    asyncio.run(terminal.laufen())
    assert gefragt == [
        "Code mir mit HTML eine Website",
        "Code mir ein 3d spiel nutze nicht nur index.html",
        "bau mir ein Menue",
    ]
    assert terminal.modus == "code"


def test_codemodus_analysiert_nur_einmal(monkeypatch, tmp_path, capsys):
    import asyncio

    (tmp_path / "index.html").write_text("<h1>x</h1>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    asyncio.run(terminal._befehl("code"))
    erste = capsys.readouterr().out
    assert "Code-Modus aktiviert" in erste
    assert "1 Datei, 0 Verzeichnisse" in erste
    assert "Web" in erste
    asyncio.run(terminal._befehl("code"))
    zweite = capsys.readouterr().out
    assert "Code-Modus aktiviert" not in zweite
    assert "schon in" in zweite


def test_codemodus_arbeitet_nur_im_projektordner(monkeypatch, tmp_path):
    import asyncio

    from app.services.tools import CODING_TOOLS

    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("code")
    box = terminal._box()
    namen = {t["function"]["name"] for t in box.schema("bau mir etwas", coding=True)}
    assert namen <= CODING_TOOLS
    assert {"write_file", "edit_file", "read_file", "run_powershell"} <= namen

    async def schreiben(pfad: str) -> str:
        return await box.execute("write_file", {"path": pfad, "content": "<h1>x</h1>"})

    assert "error" not in asyncio.run(schreiben("seite.html"))
    assert (tmp_path / "seite.html").exists()
    draussen = json.loads(asyncio.run(schreiben(str(tmp_path.parent / "fremd.html"))))
    assert "blockiert" in draussen["error"]
    assert not (tmp_path.parent / "fremd.html").exists()


def test_codemodus_prompt_kennt_ordner_und_design(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<h1>Hallo</h1>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    text = JonTerminal("code")._prompt_text("mach index.html schoener")
    assert str(tmp_path) in text
    assert "index.html" in text
    assert "Glassmorphism" in text
    assert "<h1>Hallo</h1>" in text


def test_terminalbefehl_wird_angelegt_und_entfernt(monkeypatch, tmp_path):
    from app.services import terminal_service

    monkeypatch.setattr(terminal_service, "bin_ordner", lambda: tmp_path / "bin")
    monkeypatch.setattr(terminal_service, "im_pfad", lambda _o: True)
    ergebnis = terminal_service.einrichten()
    assert ergebnis["installiert"] is True
    pfad = Path(ergebnis["befehl"])
    assert pfad.exists()
    inhalt = pfad.read_text(encoding="utf-8")
    assert "app.cli" in inhalt or "cli" in inhalt
    assert not inhalt.startswith("﻿")

    assert terminal_service.stand()["installiert"] is True
    terminal_service.entfernen()
    assert pfad.exists() is False


def test_terminalstand_nennt_pfad_und_system():
    from app.services.terminal_service import bin_ordner, befehl_pfad, stand

    daten = stand()
    assert daten["ordner"] == str(bin_ordner())
    assert daten["befehl"] == str(befehl_pfad())
    assert daten["system"]


def test_terminalweg_laeuft_wirklich_durch():
    umgebung = dict(
        os.environ,
        PYTHONPATH=str(WURZEL / "backend"),
        PYTHONIOENCODING="utf-8",
        JON_CLI_EINFARBIG="1",
        COLUMNS="160",
    )
    _ohne_editor(umgebung)
    ergebnis = subprocess.run(
        [sys.executable, "-m", "app.cli"],
        input="chat\nhilfe\nende\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=umgebung,
        cwd=str(WURZEL / "backend"),
        timeout=240,
    )
    assert ergebnis.returncode == 0
    assert "Hallo" in ergebnis.stdout
    assert "Code-Modus aktiviert" in ergebnis.stdout
    assert "Du (code)>" in ergebnis.stdout
    assert "Du>" in ergebnis.stdout
    assert "Als globaler Befehl: jon" in ergebnis.stdout
    assert "In jedem Terminal" in ergebnis.stdout


def test_modellwahl_bleibt_gemerkt(monkeypatch, tmp_path):
    import asyncio

    from app.services import settings_service

    monkeypatch.chdir(tmp_path)
    dienst = settings_service.get_settings_service()
    vorher = dienst.terminal_selection()
    try:
        terminal = JonTerminal("chat")
        alle = list(terminal.registry.all().keys())
        ziel = next(n for n in alle if n != terminal.anbieter)
        asyncio.run(terminal._anbieter_befehl(ziel))
        assert terminal.anbieter == ziel
        assert dienst.terminal_selection()[0] == ziel

        zweiter = JonTerminal("chat")
        if ziel in zweiter._verfuegbar():
            assert zweiter.anbieter == ziel
        dienst.remember_terminal(ziel, "mein-lieblingsmodell")
        dritter = JonTerminal("chat")
        if ziel in dritter._verfuegbar():
            assert dritter.modell == "mein-lieblingsmodell"
    finally:
        dienst.remember_terminal(vorher[0], vorher[1])


def test_websuche_oeffnet_ohne_auftrag_keinen_browser(monkeypatch):
    import asyncio

    from app.services.tools import ToolBox, runde_beginnen

    async def _direkt(frage, anzahl=6, read=False):
        return {"treffer": [{"title": "A"}, {"title": "B"}], "mager": False}

    def _verboten(frage, anzahl):
        raise AssertionError("Ohne Auftrag darf kein Browser starten.")

    monkeypatch.setattr("app.services.websearch_service.search_web", _direkt)
    monkeypatch.setattr("app.services.websuche_browser.suchen", _verboten)
    box = ToolBox()

    async def lauf():
        runde_beginnen()
        return json.loads(await box.execute("web_search", {"query": "was ist python"}))

    assert asyncio.run(lauf())["browser"] == "Direktsuche"

    def _browser(frage, anzahl):
        return {"treffer": [{"titel": "Aus dem Browser", "url": "https://x.de"}]}

    monkeypatch.setattr("app.services.websuche_browser.suchen", _browser)

    async def mit_wunsch():
        runde_beginnen()
        return json.loads(
            await box.execute(
                "web_search", {"query": "was ist python", "browser": "jon"}
            )
        )

    assert asyncio.run(mit_wunsch())["treffer"][0]["titel"] == "Aus dem Browser"


def test_kaputte_werkzeugnamen_werden_gesaeubert():
    from app.services.tools import _name_saeubern

    assert _name_saeubern("open_url<|channel|>commentary") == "open_url"
    assert _name_saeubern("  web_search  ") == "web_search"
    assert _name_saeubern("start_timer") == "start_timer"
    assert _name_saeubern("android_device_status") == "android_device_status"


def test_terminal_kennt_das_heutige_datum(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    text = JonTerminal("chat")._prompt_text()
    assert "HEUTE IST" in text
    assert "web_search" in text
    assert "das neueste" in text


def test_terminal_weicht_auf_ein_anderes_modell_aus(monkeypatch, tmp_path):
    import asyncio

    from app.services import chat_service

    monkeypatch.chdir(tmp_path)
    terminal = JonTerminal("chat")
    terminal.anbieter = "nvidia"
    terminal.modell = "modell-a"
    monkeypatch.setattr(chat_service, "_slow_routes", {})
    monkeypatch.setattr(chat_service, "_slow_loaded", True)
    monkeypatch.setattr(chat_service, "_slow_sichern", lambda: None)
    monkeypatch.setattr(
        chat_service, "route_providers", lambda *a, **k: _fertig(["nvidia"])
    )
    wege = asyncio.run(terminal._wege())
    assert wege[0] == ("nvidia", "modell-a")

    chat_service.mark_slow("nvidia", "modell-a")
    wege = asyncio.run(terminal._wege())
    assert wege[0] != ("nvidia", "modell-a")
    assert ("nvidia", "modell-a") in wege


async def _fertig(wert):
    return wert


def test_langsame_wege_ueberleben_den_neustart(monkeypatch, tmp_path):
    from app.services import chat_service

    monkeypatch.setattr(chat_service, "SLOW_ROUTE_FILE", tmp_path / "langsam.json")
    monkeypatch.setattr(chat_service, "_slow_routes", {})
    monkeypatch.setattr(chat_service, "_slow_loaded", True)
    chat_service.mark_slow("nvidia", "traeges-modell")
    assert (tmp_path / "langsam.json").exists()

    monkeypatch.setattr(chat_service, "_slow_routes", {})
    monkeypatch.setattr(chat_service, "_slow_loaded", False)
    assert chat_service.is_slow("nvidia", "traeges-modell") is True
    assert chat_service.is_slow("nvidia", "flinkes-modell") is False


def test_duenne_direktsuche_faellt_auf_jons_browser_zurueck(monkeypatch):
    import asyncio

    from app.services.tools import ToolBox

    async def _direkt(frage, anzahl=6, read=False):
        return {"treffer": [{"title": "Wikipedia"}], "mager": True}

    def _browser(frage, anzahl):
        return {"treffer": [{"titel": "Echter Treffer", "url": "https://x.de"}]}

    monkeypatch.setattr("app.services.websearch_service.search_web", _direkt)
    monkeypatch.setattr("app.services.websuche_browser.suchen", _browser)
    daten = json.loads(
        asyncio.run(ToolBox().execute("web_search", {"query": "neuestes iphone"}))
    )
    assert daten["treffer"][0]["titel"] == "Echter Treffer"
    assert "Direktsuche gab zu wenig her" in daten["hinweis"]


def test_gute_direktsuche_bleibt_ohne_browser(monkeypatch):
    import asyncio

    from app.services.tools import ToolBox

    async def _direkt(frage, anzahl=6, read=False):
        return {"treffer": [{"title": "A"}, {"title": "B"}], "mager": False}

    def _verboten(frage, anzahl):
        raise AssertionError("Bei guten Treffern darf kein Browser starten.")

    monkeypatch.setattr("app.services.websearch_service.search_web", _direkt)
    monkeypatch.setattr("app.services.websuche_browser.suchen", _verboten)
    daten = json.loads(
        asyncio.run(ToolBox().execute("web_search", {"query": "was ist python"}))
    )
    assert daten["browser"] == "Direktsuche"
    assert len(daten["treffer"]) == 2


def test_hoechstens_drei_suchen_pro_frage(monkeypatch):
    import asyncio

    from app.services.tools import MAX_SUCHEN, ToolBox, runde_beginnen

    async def _direkt(frage, anzahl=6, read=False):
        return {"treffer": [{"title": "A"}, {"title": "B"}], "mager": False}

    monkeypatch.setattr("app.services.websearch_service.search_web", _direkt)
    box = ToolBox()

    async def lauf():
        runde_beginnen()
        antworten = []
        for i in range(MAX_SUCHEN + 2):
            antworten.append(
                json.loads(await box.execute("web_search", {"query": f"probe {i}"}))
            )
        return antworten

    antworten = asyncio.run(lauf())
    assert all("error" not in a for a in antworten[:MAX_SUCHEN])
    assert all("Genug gesucht" in a["error"] for a in antworten[MAX_SUCHEN:])

    async def neue_runde():
        runde_beginnen()
        return json.loads(await box.execute("web_search", {"query": "frisch"}))

    assert "error" not in asyncio.run(neue_runde())


def test_ohne_auftrag_gibt_es_kein_open_url():
    from app.services.tools import ToolBox

    box = ToolBox()
    for frage in ("was ist das neueste iphone", "wer ist bundeskanzler", "rechne 2+2"):
        namen = [t["function"]["name"] for t in box.schema(frage)]
        assert "open_url" not in namen
    for auftrag in ("oeffne mir youtube", "zeig mir die apple seite", "geh auf ebay"):
        namen = [t["function"]["name"] for t in box.schema(auftrag)]
        assert "open_url" in namen


def test_leere_suche_zaehlt_nicht_mit(monkeypatch):
    import asyncio

    from app.services.tools import MAX_SUCHEN, ToolBox, runde_beginnen

    gerufen: list[str] = []

    async def _direkt(frage, anzahl=6, read=False):
        gerufen.append(frage)
        return {"treffer": [{"title": "A"}, {"title": "B"}], "mager": False}

    monkeypatch.setattr("app.services.websearch_service.search_web", _direkt)
    box = ToolBox()

    async def lauf():
        runde_beginnen()
        leer = json.loads(await box.execute("web_search", {"query": "   "}))
        gute = [
            json.loads(await box.execute("web_search", {"query": f"frage {i}"}))
            for i in range(MAX_SUCHEN)
        ]
        return leer, gute

    leer, gute = asyncio.run(lauf())
    assert "Ohne Suchbegriff" in leer["error"]
    assert gerufen == [f"frage {i}" for i in range(MAX_SUCHEN)]
    assert all("error" not in g for g in gute)


def test_preisfrage_liest_die_seiten(monkeypatch):
    import asyncio

    from app.services.tools import ToolBox, runde_beginnen

    gelesen: list[bool] = []

    async def _direkt(frage, anzahl=6, read=False):
        gelesen.append(read)
        return {"treffer": [{"title": "A"}, {"title": "B"}], "mager": False}

    monkeypatch.setattr("app.services.websearch_service.search_web", _direkt)
    box = ToolBox()

    async def lauf(frage):
        runde_beginnen()
        await box.execute("web_search", {"query": frage})

    asyncio.run(lauf("was kostet das iPhone"))
    asyncio.run(lauf("iPhone 18 Preis"))
    asyncio.run(lauf("wer ist bundeskanzler"))
    assert gelesen == [True, True, False]


def test_duenne_treffer_landen_nicht_im_zwischenspeicher(monkeypatch):
    from app.services.tools import _zu_duenn

    assert _zu_duenn("web_search", json.dumps({"treffer": [{"a": 1}], "mager": True}))
    assert _zu_duenn("web_search", json.dumps({"treffer": []}))
    assert not _zu_duenn(
        "web_search", json.dumps({"treffer": [{"a": 1}], "mager": False})
    )
    assert not _zu_duenn("start_timer", json.dumps({"treffer": [], "mager": True}))


def test_bing_weiterleitungen_werden_aufgeloest():
    import base64

    from app.services.websuche_browser import _echte_url

    ziel = "https://www.apple.com/de/iphone/"
    roh = "a1" + base64.urlsafe_b64encode(ziel.encode()).decode().rstrip("=")
    adresse = f"https://www.bing.com/ck/a?!&&p=abc&u={roh}&ntb=1"
    assert _echte_url(adresse, "https://www.bing.com/search") == ziel
    assert _echte_url("https://x.de/seite", "https://www.bing.com/") == "https://x.de/seite"
