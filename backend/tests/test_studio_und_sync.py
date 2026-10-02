from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import pytest

from app.services.connectors.studio import StudioConnector, teile_lesen


def test_skript_zeilen_werden_zu_teilen():
    teile = teile_lesen({"skript": "A: Hallo und willkommen!\nB: Danke, schön hier zu sein.\nweiter im Text\nJon: Los geht's."})
    assert teile == [("a", "Hallo und willkommen!"), ("b", "Danke, schön hier zu sein. weiter im Text"), ("a", "Los geht's.")]


def test_lange_teile_werden_zerlegt():
    lang = "Das ist ein Satz. " * 150
    teile = teile_lesen({"teile": [{"sprecher": "gast", "text": lang}]})
    assert len(teile) > 1 and all(s == "b" and len(t) <= 1100 for s, t in teile)


def test_podcast_wird_als_mp3_gespeichert(monkeypatch, tmp_path):
    import app.services.dateiraum_service as raum
    import app.services.voice_service as stimme

    stimmen = []

    async def sprechen(text, voice="x", rate="+0%", volume="+0%", pitch="+0Hz"):
        stimmen.append(voice)
        return b"ID3" + text.encode()

    class Raum:
        def ordner(self, name):
            ziel = tmp_path / name
            ziel.mkdir(parents=True, exist_ok=True)
            return ziel

    monkeypatch.setattr(stimme, "synthesize_speech", sprechen)
    monkeypatch.setattr(raum, "get_dateiraum_service", lambda: Raum())
    ergebnis = asyncio.run(StudioConnector().ausfuehren("podcast_erstellen", {"titel": "KI heute", "teile": [{"sprecher": "a", "text": "Hallo"}, {"sprecher": "b", "text": "Hi"}]}))
    assert ergebnis["ok"] and ergebnis["teile"] == 2
    pfad = Path(ergebnis["datei"]["path"])
    assert pfad.suffix == ".mp3" and pfad.read_bytes().startswith(b"ID3")
    assert stimmen == ["de-DE-ConradNeural", "de-DE-KatjaNeural"]
    assert "error" in asyncio.run(StudioConnector().ausfuehren("podcast_erstellen", {"titel": "Leer"}))


def test_podcast_karte_und_auswahl():
    from app.services.chat_service import card_payload
    from app.services.tools import select_tools

    karte = card_payload("podcast_erstellen", '{"ok": true, "datei": {"path": "/x/a.mp3", "name": "a.mp3"}}')
    assert karte == {"kind": "datei", "data": {"dateien": [{"path": "/x/a.mp3", "name": "a.mp3"}]}}
    assert "podcast_erstellen" in select_tools("mach mir einen podcast über den mond")


def test_fitness_abgleich(monkeypatch, tmp_path):
    from app.services import fitness_service as modul

    monkeypatch.setattr(modul, "STORE", tmp_path / "fitness.json")
    monkeypatch.setattr(modul, "_dienst", None)
    dienst = modul.get_fitness_service()
    eigenes = dienst.training_eintragen({"art": "gym", "text": "Kniebeugen 3x5 90kg"})
    heute = date.today().isoformat()
    ergebnis = dienst.abgleichen(
        [{"id": "h1", "datum": heute, "art": "laufen", "dauer_min": 30, "distanz_km": 5}, {"id": "h1", "art": "gym"}, {"id": "", "art": "gym"}, "kaputt"],
        [eigenes["id"]],
        {heute: 9000},
    )
    assert ergebnis["neu"] == 1
    ids = [t["id"] for t in ergebnis["trainings"]]
    assert ids == ["h1"]
    assert dienst.uebersicht()["heute"]["schritte"] == 9000
    assert dienst.abgleichen([{"id": "h1", "art": "gym"}], [], None)["neu"] == 0


@pytest.mark.parametrize("sprecher", ["b", "Gast", "2"])
def test_zweite_stimme(sprecher):
    assert teile_lesen({"teile": [{"sprecher": sprecher, "text": "x"}]}) == [("b", "x")]
