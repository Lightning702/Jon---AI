from __future__ import annotations

import asyncio
import sys

import pytest

from app.core import proactor_fix

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Nur die Windows-Ereignisschleife ist betroffen")


def test_port_bleibt_nach_winerror_64_offen():
    proactor_fix.anwenden()

    async def ablauf():
        loop = asyncio.get_running_loop()
        angenommen: list[str] = []

        async def bediene(leser, schreiber):
            angenommen.append((await leser.readline()).decode().strip())
            schreiber.write(b"ok\n")
            await schreiber.drain()
            schreiber.close()

        server = await asyncio.start_server(bediene, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        proactor = loop._proactor
        echt = proactor.accept
        zaehler = {"n": 0}

        def accept(sock):
            zaehler["n"] += 1
            if zaehler["n"] == 2:
                kaputt = loop.create_future()
                kaputt.set_exception(OSError(22, "Der angegebene Netzwerkname ist nicht mehr verfuegbar", None, 64))
                return kaputt
            return echt(sock)

        proactor.accept = accept
        for nummer in range(3):
            leser, schreiber = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), 5)
            schreiber.write(f"hallo {nummer}\n".encode())
            await schreiber.drain()
            assert (await asyncio.wait_for(leser.readline(), 5)).strip() == b"ok"
            schreiber.close()
        server.close()
        await server.wait_closed()
        return angenommen

    loop = asyncio.ProactorEventLoop()
    try:
        angenommen = loop.run_until_complete(ablauf())
    finally:
        loop.close()
    assert angenommen == ["hallo 0", "hallo 1", "hallo 2"]


def test_echter_fehler_schliesst_weiterhin():
    assert proactor_fix.voruebergehend(OSError(22, "weg", None, 64))
    assert not proactor_fix.voruebergehend(OSError(22, "anderes", None, 995))
    assert not proactor_fix.voruebergehend(ValueError("x"))
