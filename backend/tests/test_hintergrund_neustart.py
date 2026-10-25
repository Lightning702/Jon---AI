from __future__ import annotations

import asyncio

from app import main


def test_beendeter_netzdienst_startet_spaeter_neu_und_stoppt_sauber(monkeypatch):
    gestartet: list[str] = []

    async def dienst():
        gestartet.append("lauf")

    monkeypatch.setattr(main, "NEUSTART_PAUSEN", (0.01, 0.01, 0.01))
    monkeypatch.setattr(main, "_neu_startbar", lambda: {"multiplayer_server": dienst})

    async def ablauf():
        main._dienste_aktiv = True
        main._spawn("multiplayer_server", dienst())
        await asyncio.sleep(0.1)
        assert len(gestartet) >= 2
        main._stop_all()
        anzahl = len(gestartet)
        await asyncio.sleep(0.1)
        assert len(gestartet) == anzahl
        assert not main._neustarts and not main._dienste_aktiv

    asyncio.run(ablauf())


def test_andere_dienste_werden_nicht_neu_gestartet(monkeypatch):
    aufrufe: list[str] = []

    async def wache():
        aufrufe.append("lauf")

    monkeypatch.setattr(main, "NEUSTART_PAUSEN", (0.01,))

    async def ablauf():
        main._dienste_aktiv = True
        main._spawn("dream_watcher", wache())
        await asyncio.sleep(0.08)
        main._stop_all()

    asyncio.run(ablauf())
    assert aufrufe == ["lauf"]
