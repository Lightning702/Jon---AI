from __future__ import annotations

import asyncio
import ipaddress
import json
import threading
import time

from app.core.fehler import leise

MAGIC = "jon-pc-kopplung"
FENSTER = 300.0
SUCHZEIT = 2.5
NETZE = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]

_lock = threading.Lock()
_offen: dict | None = None


def _privat(adresse: str) -> bool:
    try:
        ip = ipaddress.ip_address(adresse)
    except ValueError:
        return False
    return ip.version == 4 and any(ip in netz for netz in NETZE)


def oeffnen(code: str, name: str, pc_id: str, port: int) -> None:
    global _offen
    with _lock:
        _offen = {"code": code, "name": name, "pc_id": pc_id, "port": port, "bis": time.time() + FENSTER}


def schliessen() -> None:
    global _offen
    with _lock:
        _offen = None


def offen() -> dict | None:
    with _lock:
        if _offen and time.time() < _offen["bis"]:
            return dict(_offen)
    return None


def antwort_fuer(payload: dict, absender: str) -> dict | None:
    if payload.get("magic") != MAGIC or payload.get("q") != "offen" or not _privat(absender):
        return None
    stand = offen()
    if not stand or str(payload.get("pc_id") or "") == stand["pc_id"]:
        return None
    from app.services.handy_service import get_handy_service

    dienst = get_handy_service()
    with dienst._lock:
        sitzung = dict(dienst._sitzung or {})
    if sitzung.get("code") != stand["code"] or sitzung.get("status") != "offen" or time.time() > float(sitzung.get("ablauf") or 0):
        return None
    return {"magic": MAGIC, "name": stand["name"], "code": stand["code"], "pc_id": stand["pc_id"], "port": stand["port"]}


async def suchen(eigene_id: str, zeit: float = SUCHZEIT) -> list[dict]:
    from app.services.coop_lan_service import broadcast_targets
    from app.services.ollama_share_service import DISCOVERY_PORT

    loop = asyncio.get_running_loop()
    gefunden: dict[str, dict] = {}

    class Protokoll(asyncio.DatagramProtocol):
        def datagram_received(self, data: bytes, addr) -> None:
            try:
                paket = json.loads(data.decode("utf-8"))
            except Exception:
                return
            if paket.get("magic") != MAGIC or paket.get("q") or not paket.get("code"):
                return
            if paket.get("pc_id") == eigene_id or not _privat(addr[0]):
                return
            paket["host"] = addr[0]
            gefunden[str(paket.get("pc_id") or addr[0])] = paket

    transport, _ = await loop.create_datagram_endpoint(Protokoll, local_addr=("0.0.0.0", 0), allow_broadcast=True)
    try:
        nachricht = json.dumps({"magic": MAGIC, "q": "offen", "pc_id": eigene_id}).encode("utf-8")
        ende = loop.time() + zeit
        while loop.time() < ende:
            for ziel in broadcast_targets():
                try:
                    transport.sendto(nachricht, (ziel, DISCOVERY_PORT))
                except Exception:
                    continue
            await asyncio.sleep(0.6)
    finally:
        transport.close()
    return list(gefunden.values())


def _passend(kandidaten: list[dict], wunsch: str) -> dict | None:
    if not kandidaten:
        return None
    wunsch = wunsch.strip().lower()
    if wunsch:
        for eintrag in kandidaten:
            if wunsch in str(eintrag.get("name", "")).lower():
                return eintrag
    return kandidaten[0]


async def verbinden(wunsch: str = "") -> dict:
    from app.core.config import get_settings
    from app.services.handy_service import get_handy_service
    from app.services.verbund_service import VerbundFehler, get_verbund_service

    dienst = get_handy_service()
    kennung = dienst.kennung()
    try:
        kandidaten = await suchen(kennung["id"])
    except Exception as fehler:
        leise(fehler, "services/pc_kopplung")
        kandidaten = []
    ziel = _passend(kandidaten, wunsch)
    if ziel:
        adresse = f"http://{ziel['host']}:{int(ziel.get('port') or 8756)}"
        try:
            eintrag = await asyncio.to_thread(get_verbund_service().koppeln, str(ziel["code"]), None, adresse)
        except VerbundFehler as fehler:
            return {"ok": False, "art": "jon", "error": str(fehler)}
        except ValueError as fehler:
            return {"ok": False, "art": "jon", "error": str(fehler)}
        return {"ok": True, "art": "jon", "fertig": True, "jon": eintrag.get("name") or ziel.get("name", ""), "anleitung": f"Verbunden mit {eintrag.get('name') or ziel.get('name', 'dem anderen PC')} über dein Heimnetz."}
    daten = dienst.kopplung_starten(False)
    oeffnen(daten["code"], kennung["name"], kennung["id"], int(get_settings().port))
    return {
        "ok": True,
        "art": "jon",
        "heimnetz": True,
        "code": daten["code"],
        "code_gruppiert": daten["code_gruppiert"],
        "ablauf": min(daten["ablauf"], time.time() + FENSTER),
        "pc": kennung["name"],
        "anleitung": (
            "Sag jetzt auf dem anderen PC zu Jon: „Verbinde meinen PC“. Die beiden Jons finden sich "
            "im Heimnetz von selbst, du tippst dann hier nur noch auf Erlauben. Klappt das nicht, "
            "sag dort: „Verbinde dich mit Code " + daten["code_gruppiert"] + "“."
        ),
    }
