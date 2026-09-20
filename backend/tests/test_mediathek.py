from __future__ import annotations

import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import mediathek_service
from app.services.mediathek_service import MediathekService

client = TestClient(app)


@pytest.fixture
def dienst(tmp_path, monkeypatch):
    monkeypatch.setattr(mediathek_service, "ORDNER", tmp_path / "mediathek")
    monkeypatch.setattr(mediathek_service, "INDEX", tmp_path / "mediathek.json")
    eigener = MediathekService()
    monkeypatch.setattr(mediathek_service, "_service", eigener)
    return eigener


def ton_datei(pfad: Path, sekunden: float = 0.2) -> Path:
    with wave.open(str(pfad), "wb") as datei:
        datei.setnchannels(1)
        datei.setsampwidth(2)
        datei.setframerate(8000)
        datei.writeframes(b"\x00\x00" * int(8000 * sekunden))
    return pfad


def test_aufnahme_bleibt_dauerhaft_liegen(dienst, tmp_path):
    quelle = ton_datei(tmp_path / "roh.wav")
    eintrag = dienst.aufnehmen(quelle, "Mein Lied.wav", "https://beispiel.de/x", 12.0, "Kanal")
    assert eintrag is not None
    assert eintrag["art"] == "musik"
    assert eintrag["dauer"] == 12.0
    assert eintrag["kanal"] == "Kanal"
    assert Path(eintrag["datei"]).is_file()
    assert quelle.is_file()

    liste = dienst.liste()
    assert [e["id"] for e in liste["eintraege"]] == [eintrag["id"]]
    assert liste["groesse"] > 0


def test_zwei_gleiche_namen_stossen_sich_nicht(dienst, tmp_path):
    ton_datei(tmp_path / "a.wav")
    erste = dienst.aufnehmen(tmp_path / "a.wav", "Lied.wav")
    zweite = dienst.aufnehmen(tmp_path / "a.wav", "Lied.wav")
    assert erste and zweite
    assert erste["datei"] != zweite["datei"]
    assert len(dienst.liste()["eintraege"]) == 2


def test_fremde_dateien_kommen_nicht_hinein(dienst, tmp_path):
    (tmp_path / "notiz.txt").write_text("hallo", encoding="utf-8")
    assert dienst.aufnehmen(tmp_path / "notiz.txt", "notiz.txt") is None
    assert dienst.aufnehmen(tmp_path / "fehlt.mp3", "fehlt.mp3") is None


def test_verschwundene_datei_faellt_aus_der_liste(dienst, tmp_path):
    ton_datei(tmp_path / "a.wav")
    eintrag = dienst.aufnehmen(tmp_path / "a.wav", "Weg.wav")
    Path(eintrag["datei"]).unlink()
    assert dienst.liste()["eintraege"] == []


def test_loeschen_raeumt_die_datei_weg(dienst, tmp_path):
    ton_datei(tmp_path / "a.wav")
    eintrag = dienst.aufnehmen(tmp_path / "a.wav", "Weg.wav")
    pfad = Path(eintrag["datei"])
    assert dienst.loeschen(eintrag["id"]) is True
    assert pfad.exists() is False
    assert dienst.loeschen(eintrag["id"]) is False


def test_player_bekommt_die_datei_stueckweise(dienst, tmp_path):
    ton_datei(tmp_path / "a.wav", 1.0)
    eintrag = dienst.aufnehmen(tmp_path / "a.wav", "Probe.wav")
    ganz = client.get(f"/api/mediathek/datei/{eintrag['id']}")
    assert ganz.status_code == 200
    assert ganz.headers["accept-ranges"] == "bytes"
    laenge = len(ganz.content)

    teil = client.get(
        f"/api/mediathek/datei/{eintrag['id']}", headers={"Range": "bytes=0-99"}
    )
    assert teil.status_code == 206
    assert teil.headers["content-range"] == f"bytes 0-99/{laenge}"
    assert len(teil.content) == 100
    assert teil.content == ganz.content[:100]

    schluss = client.get(
        f"/api/mediathek/datei/{eintrag['id']}", headers={"Range": "bytes=-50"}
    )
    assert schluss.status_code == 206
    assert schluss.content == ganz.content[-50:]


def test_kaputter_bereich_liefert_die_ganze_datei(dienst, tmp_path):
    ton_datei(tmp_path / "a.wav")
    eintrag = dienst.aufnehmen(tmp_path / "a.wav", "Probe.wav")
    antwort = client.get(
        f"/api/mediathek/datei/{eintrag['id']}", headers={"Range": "seiten=1-2"}
    )
    assert antwort.status_code == 200


def test_liste_ueber_die_schnittstelle(dienst, tmp_path):
    ton_datei(tmp_path / "a.wav")
    dienst.aufnehmen(tmp_path / "a.wav", "Aus dem Netz.wav", "https://beispiel.de/y")
    daten = client.get("/api/mediathek").json()
    assert daten["eintraege"][0]["name"] == "Aus dem Netz"
    assert daten["eintraege"][0]["quelle"] == "https://beispiel.de/y"
    assert daten["ordner"]


def test_unbekannte_aufnahme_meldet_sich_sauber(dienst):
    assert client.get("/api/mediathek/datei/gibtsnicht").status_code == 404
    assert client.delete("/api/mediathek/gibtsnicht").status_code == 404


def test_downloader_legt_fertige_dateien_in_die_mediathek(dienst, tmp_path):
    from app.services.downloader_service import _in_die_mediathek

    ton_datei(tmp_path / "fertig.wav")
    _in_die_mediathek(
        tmp_path / "fertig.wav", "Song.wav", "https://beispiel.de/z", 30.0, "Band", ""
    )
    eintraege = dienst.liste()["eintraege"]
    assert len(eintraege) == 1
    assert eintraege[0]["name"] == "Song"
    assert eintraege[0]["dauer"] == 30.0
