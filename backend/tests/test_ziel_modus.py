from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.services import ziel_modus
from app.services.ziel_modus import ZielModus, befehl, ende_text


class Harness:
    def __init__(self, ergebnisse, langsam=False):
        self.ergebnisse = list(ergebnisse)
        self.tasks: dict[str, dict] = {}
        self.gestartet: list[tuple[str, str, str]] = []
        self.abgebrochen: list[str] = []
        self.langsam = langsam

    def start(self, goal, root="", source="app", provider="", model="", thread="", modus="code"):
        nummer = len(self.gestartet) + 1
        kennung = f"t{nummer}"
        self.gestartet.append((goal, thread, modus))
        status, zusammenfassung = self.ergebnisse[min(nummer - 1, len(self.ergebnisse) - 1)]
        self.tasks[kennung] = {"id": kennung, "thread": thread or "s1", "root": "C:/arbeit", "status": status, "summary": zusammenfassung, "provider": "nvidia", "model": "m", "dateien": [{"path": f"C:/arbeit/folien{nummer}.pptx"}], "changes": [], "checks": []}
        return dict(self.tasks[kennung])

    @staticmethod
    def sitzung_von(task):
        return task.get("thread") or task["id"]

    async def stream(self, kennung):
        yield {"type": "gedanke", "message": "Ich plane zuerst die Folien."}
        yield {"type": "notiz", "message": "Folien bauen"}
        yield {"type": "action", "tool": "jon", "pfad": "C:/arbeit/folien.pptx"}
        if self.langsam:
            await asyncio.sleep(30)

    def get(self, kennung):
        return dict(self.tasks[kennung])

    async def cancel(self, kennung):
        self.abgebrochen.append(kennung)


@pytest.fixture
def umgebung(monkeypatch):
    urteile: list[str] = []
    fragen: list[str] = []

    async def anfragen(zugang, system, nutzer):
        fragen.append(nutzer)
        return SimpleNamespace(text=urteile.pop(0) if urteile else "ZIEL ERREICHT: fertig")

    monkeypatch.setattr("app.services.harness.modell.anfragen", anfragen)

    def setzen(harness):
        monkeypatch.setattr("app.services.harness.get_harness_service", lambda: harness)

    return SimpleNamespace(urteile=urteile, fragen=fragen, setzen=setzen)


def _lauf(ziel="Präsentation über Datensicherung", source="app"):
    async def lauf():
        modus = ZielModus()
        eintrag = modus.starten(ziel, source)
        ereignisse = [e async for e in modus.verfolgen(eintrag["id"])]
        return modus.get(eintrag["id"]), ereignisse

    return asyncio.run(lauf())


def test_befehl_wird_erkannt():
    assert befehl("/goal Baue ein Spiel") == "Baue ein Spiel"
    assert befehl("/ziel   mach die Website schöner ") == "mach die Website schöner"
    assert befehl("/goal@jon_bot stopp") == "stopp"
    assert befehl("/goal") == ""
    assert befehl("/goals bitte") is None
    assert befehl("Was ist ein goal?") is None


def test_arbeitet_in_runden_bis_das_ziel_erreicht_ist(umgebung):
    harness = Harness([("done", "Folien erstellt, Bilder fehlen"), ("done", "Bilder ergänzt")])
    umgebung.setzen(harness)
    umgebung.urteile.extend(["WEITER: Bilder fehlen noch", "ZIEL ERREICHT: alles da"])
    stand, ereignisse = _lauf()
    assert stand["status"] == "erreicht" and stand["runde"] == 2
    assert len(harness.gestartet) == 2
    assert harness.gestartet[0][2] == "allgemein"
    assert harness.gestartet[1][1] == "s1" and "Bilder fehlen noch" in harness.gestartet[1][0]
    arten = [e["art"] for e in ereignisse]
    assert arten.count("runde") == 2 and arten[-1] == "ende" and "urteil" in arten
    assert any(e.get("typ") == "gedanke" for e in ereignisse)
    assert stand["dateien"] == ["C:/arbeit/folien1.pptx", "C:/arbeit/folien2.pptx"]
    assert "Ziel erreicht" in ende_text(stand)


def test_zweimal_gescheitert_haelt_an(umgebung):
    umgebung.setzen(Harness([("failed", "Modell antwortet nicht")]))
    umgebung.urteile.append("WEITER: nochmal")
    stand, _ = _lauf()
    assert stand["status"] == "fehler" and stand["runde"] == 2


def test_nach_der_letzten_runde_wird_angehalten(umgebung, monkeypatch):
    monkeypatch.setattr(ziel_modus, "RUNDEN", 3)
    umgebung.setzen(Harness([("done", "Teil fertig")]))
    umgebung.urteile.extend(["WEITER: mehr"] * 5)
    stand, _ = _lauf()
    assert stand["status"] == "angehalten" and stand["runde"] == 3
    assert "/goal weiter" in ende_text(stand)


def test_stoppen_bricht_den_harness_ab(umgebung):
    harness = Harness([("done", "x")], langsam=True)
    umgebung.setzen(harness)

    async def lauf():
        modus = ZielModus()
        eintrag = modus.starten("Langes Ziel", "telegram:1")
        await asyncio.sleep(0.05)
        with pytest.raises(ValueError):
            modus.starten("Zweites Ziel", "telegram:1")
        await modus.stoppen(eintrag["id"])
        return modus.get(eintrag["id"])

    stand = asyncio.run(lauf())
    assert stand["status"] == "abgebrochen"
    assert harness.abgebrochen == ["t1"]


def test_leeres_ziel_wird_erklaert():
    async def lauf():
        with pytest.raises(ValueError):
            ZielModus().starten("   ", "app")

    asyncio.run(lauf())


def test_telegram_zeigt_fortschritt_und_schickt_dateien(umgebung, monkeypatch, tmp_path):
    from app.services import telegram_service as ts

    datei = tmp_path / "folien.pptx"
    datei.write_bytes(b"x")
    class MitDatei(Harness):
        def start(self, *argumente, **werte):
            task = super().start(*argumente, **werte)
            self.tasks[task["id"]]["dateien"] = [{"path": str(datei)}]
            return task

    umgebung.setzen(MitDatei([("done", "Präsentation fertig")]))
    monkeypatch.setattr(ziel_modus, "_dienst", None)
    dienst = ts.TelegramService()
    gesendet, geaendert, dateien = [], [], []

    async def nachricht(chat_id, text, knoepfe=None):
        gesendet.append(text)
        return 5

    async def aendern(chat_id, nummer, text, knoepfe=None):
        geaendert.append(text)
        return True

    async def send(chat_id, text):
        gesendet.append(text)

    async def send_datei(chat_id, eintrag):
        dateien.append(eintrag["path"])
        return True

    monkeypatch.setattr(dienst, "_nachricht", nachricht)
    monkeypatch.setattr(dienst, "_aendern", aendern)
    monkeypatch.setattr(dienst, "send", send)
    monkeypatch.setattr(dienst, "send_datei", send_datei)
    monkeypatch.setattr(ts, "ZIEL_TAKT", 0)
    asyncio.run(dienst._ziel("7", "Präsentation über Datensicherung"))
    assert gesendet[0].startswith("Ziel: Präsentation über Datensicherung")
    assert any("Runde 1" in t for t in geaendert)
    assert any("Ziel erreicht" in t for t in gesendet)
    assert dateien == [str(datei)]
