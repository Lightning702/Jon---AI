from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.uninstall_service as us


class FakeSystemService:
    aufrufe: list[bool] = []

    def set_autostart(self, enabled: bool) -> bool:
        FakeSystemService.aufrufe.append(enabled)
        return enabled


@pytest.fixture(autouse=True)
def kein_echter_systemzugriff(monkeypatch):
    FakeSystemService.aufrufe = []
    monkeypatch.setattr(
        "app.services.system_service.SystemService", FakeSystemService
    )
    monkeypatch.setattr(
        us.subprocess, "Popen", lambda *a, **k: pytest.fail("Popen darf nicht laufen")
    )
    yield


@pytest.fixture
def wegwerf(tmp_path, monkeypatch):
    daten = tmp_path / "daten"
    daten.mkdir()
    (daten / "jon.db").write_text("datenbank", encoding="utf-8")
    (daten / "unter").mkdir()
    (daten / "unter" / "peers.json").write_text("[]", encoding="utf-8")
    env = tmp_path / ".env"
    env.write_text("NVIDIA_API_KEY=geheim\n", encoding="utf-8")

    monkeypatch.setattr(us, "DATA_DIR", daten)
    monkeypatch.setattr(us, "ENV_FILE", env)
    monkeypatch.setattr(us, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(us, "uninstaller_pfad", lambda: "")
    return daten, env


def test_plan_zaehlt_alles_auf(wegwerf):
    daten, env = wegwerf
    ergebnis = us.plan()
    ids = {e["id"] for e in ergebnis["eintraege"]}
    assert ids == {"daten", "env"}
    assert ergebnis["dateien_gesamt"] == 3
    assert ergebnis["bytes_gesamt"] > 0
    assert ergebnis["bestaetigung"] == "JON LOESCHEN"
    assert daten.exists() and env.exists()


def test_plan_loescht_nichts(wegwerf):
    daten, env = wegwerf
    us.plan()
    us.plan()
    assert (daten / "jon.db").exists()
    assert (daten / "unter" / "peers.json").exists()
    assert env.exists()


@pytest.mark.parametrize("eingabe", ["", "loeschen", "JON LOESCHE", "jon  loeschen", "ja"])
def test_falsche_bestaetigung_loescht_nichts(wegwerf, eingabe):
    daten, env = wegwerf
    with pytest.raises(ValueError):
        us.ausfuehren(eingabe, False)
    assert (daten / "jon.db").exists()
    assert env.exists()


def test_richtige_bestaetigung_loescht(wegwerf):
    daten, env = wegwerf
    ergebnis = us.ausfuehren("jon loeschen", False)
    assert ergebnis["erledigt"] is True
    assert not daten.exists()
    assert not env.exists()
    assert ergebnis["deinstallierer_gestartet"] is False


def test_deinstallierer_wird_nur_auf_wunsch_gestartet(wegwerf, monkeypatch):
    gestartet = []
    monkeypatch.setattr(us, "uninstaller_pfad", lambda: "C:\\Jon\\Uninstall.exe")
    monkeypatch.setattr(
        us.subprocess, "Popen", lambda *a, **k: gestartet.append(a[0])
    )

    us.ausfuehren("JON LOESCHEN", False)
    assert gestartet == []


def test_schutz_vor_systempfaden(tmp_path, monkeypatch):
    assert us._sicher(Path("C:\\")) is False
    assert us._sicher(Path.home()) is False
    assert us._sicher(Path("C:\\gibtesnicht_12345")) is False
    echt = tmp_path / "ordner"
    echt.mkdir()
    assert us._sicher(echt) is True


def test_geschuetzter_pfad_wird_nicht_geloescht(monkeypatch):
    ok, hinweis = us._loeschen(Path.home())
    assert ok is False
    assert "Sicherheits" in hinweis
    assert Path.home().exists()


def test_quellordner_bleibt_stehen(wegwerf):
    daten, env = wegwerf
    quelle = Path(us.plan()["quellordner"])
    us.ausfuehren("JON LOESCHEN", False)
    assert quelle.exists()
