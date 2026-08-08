from __future__ import annotations

import pytest

import app.services.phone.netinfo as netinfo


@pytest.fixture(autouse=True)
def frischer_cache():
    netinfo.reset_cache()
    yield
    netinfo.reset_cache()


def _entries(raw):
    result = []
    for item in raw:
        item = dict(item)
        item.setdefault("status", "Up")
        item.setdefault("description", "")
        item["kind"] = netinfo._kind(item)
        item["score"] = netinfo._score(item)
        item["usable"] = item["score"] > -50
        result.append(item)
    result.sort(key=lambda e: e["score"], reverse=True)
    return result


def test_wlan_schlaegt_vpn_und_virtuelle_adapter(monkeypatch):
    raw = [
        {"ip": "10.2.0.2", "name": "ProTUN", "description": "Proton VPN Windows Tunnel"},
        {"ip": "172.30.176.1", "name": "vEthernet (Default Switch)", "description": ""},
        {"ip": "192.168.56.1", "name": "Ethernet 3", "description": "VirtualBox Host-Only"},
        {"ip": "10.0.0.253", "name": "WLAN", "description": "Intel Dual Band Wireless-AC"},
        {"ip": "169.254.13.48", "name": "LAN-Verbindung* 2", "description": ""},
    ]
    monkeypatch.setattr(netinfo, "_powershell_interfaces", lambda: raw)
    monkeypatch.setattr(netinfo, "_fallback_interfaces", lambda: [])
    entries = netinfo.interfaces(refresh=True)
    assert entries[0]["ip"] == "10.0.0.253"
    assert entries[0]["kind"] == "lan"
    assert netinfo.best_address() == "10.0.0.253"


def test_vpn_und_virtuell_werden_erkannt():
    entries = _entries(
        [
            {"ip": "10.2.0.2", "name": "ProTUN", "description": "Proton VPN Tunnel"},
            {"ip": "172.30.176.1", "name": "vEthernet (Default Switch)"},
            {"ip": "100.83.1.4", "name": "Tailscale", "description": "Tailscale Tunnel"},
            {"ip": "10.0.0.253", "name": "WLAN"},
        ]
    )
    kinds = {entry["ip"]: entry["kind"] for entry in entries}
    assert kinds["10.2.0.2"] == "vpn"
    assert kinds["172.30.176.1"] == "virtual"
    assert kinds["100.83.1.4"] == "mesh"
    assert kinds["10.0.0.253"] == "lan"


def test_tailscale_gewinnt_wenn_kein_lan_da_ist(monkeypatch):
    raw = [
        {"ip": "10.2.0.2", "name": "ProTUN", "description": "Proton VPN Tunnel"},
        {"ip": "100.83.1.4", "name": "Tailscale", "description": "Tailscale Tunnel"},
    ]
    monkeypatch.setattr(netinfo, "_powershell_interfaces", lambda: raw)
    monkeypatch.setattr(netinfo, "_fallback_interfaces", lambda: [])
    assert netinfo.best_address() == "100.83.1.4"


def test_eigene_vorgabe_gewinnt_immer(monkeypatch):
    monkeypatch.setattr(
        netinfo, "_powershell_interfaces", lambda: [{"ip": "10.0.0.253", "name": "WLAN"}]
    )
    monkeypatch.setattr(netinfo, "_fallback_interfaces", lambda: [])
    assert netinfo.best_address("100.64.0.9") == "100.64.0.9"


def test_link_local_und_abgeschaltete_adapter_fallen_raus():
    entries = _entries(
        [
            {"ip": "169.254.13.48", "name": "LAN-Verbindung* 2"},
            {"ip": "10.0.0.253", "name": "Ethernet", "status": "Disconnected"},
            {"ip": "10.0.0.7", "name": "WLAN"},
        ]
    )
    usable = [entry["ip"] for entry in entries if entry["usable"]]
    assert usable == ["10.0.0.7"]


def test_ohne_netzwerk_bleibt_loopback(monkeypatch):
    monkeypatch.setattr(netinfo, "_powershell_interfaces", lambda: [])
    monkeypatch.setattr(netinfo, "_fallback_interfaces", lambda: [])
    assert netinfo.best_address() == "127.0.0.1"


def test_beschreibung_ist_lesbar():
    entry = {"ip": "10.2.0.2", "name": "ProTUN", "description": "Proton VPN", "kind": "vpn"}
    assert "ProTUN" in netinfo.describe(entry)
    assert "VPN-Tunnel" in netinfo.describe(entry)


def test_diagnose_warnt_bei_vpn_adresse(tmp_path, monkeypatch):
    import app.services.phone_service as ps

    monkeypatch.setattr(ps, "CALLS_FILE", tmp_path / "calls.json")
    monkeypatch.setattr(ps, "LOG_FILE", tmp_path / "log.json")
    service = ps.PhoneService()
    monkeypatch.setattr(
        service, "settings", lambda: {"phone_enabled": True, "phone_sip_port": 5060}
    )
    monkeypatch.setattr(service, "firewall_state", lambda: {"ok": True, "detail": "ok"})
    monkeypatch.setattr(
        service,
        "addresses",
        lambda: [
            {
                "ip": "10.2.0.2",
                "label": "ProTUN (VPN-Tunnel)",
                "kind": "vpn",
                "usable": True,
                "selected": True,
            }
        ],
    )
    report = service.diagnostics()
    address_check = next(c for c in report["checks"] if c["name"] == "Serveradresse")
    assert address_check["ok"] is False
    assert "VPN" in address_check["detail"]


def test_diagnose_bietet_firewall_befehl_an(tmp_path, monkeypatch):
    import app.services.phone_service as ps

    monkeypatch.setattr(ps, "CALLS_FILE", tmp_path / "calls.json")
    monkeypatch.setattr(ps, "LOG_FILE", tmp_path / "log.json")
    service = ps.PhoneService()
    monkeypatch.setattr(
        service, "settings", lambda: {"phone_enabled": True, "phone_sip_port": 5060}
    )
    monkeypatch.setattr(
        service,
        "firewall_state",
        lambda: {"ok": False, "detail": "fehlt", "fix": "New-NetFirewallRule ..."},
    )
    monkeypatch.setattr(service, "addresses", lambda: [])
    report = service.diagnostics()
    firewall = next(c for c in report["checks"] if c["name"] == "Firewall")
    assert firewall["ok"] is False
    assert firewall["fix"].startswith("New-NetFirewallRule")


def test_firewall_befehl_hebt_rechte_selbst_an():
    from app.services.phone_service import firewall_command

    cmd = firewall_command(5060)
    assert cmd.startswith("Start-Process powershell -Verb RunAs")
    assert "'-NoProfile','-Command'" in cmd
    assert cmd.count('"') == 2
    assert "\\" not in cmd
    assert "-LocalPort 5060" in cmd
    assert "-LocalPort 16384-32768" in cmd
    assert cmd.count("-Profile Any") == 2


def test_firewall_befehl_nimmt_eigenen_port():
    from app.services.phone_service import firewall_command

    assert "-LocalPort 5070" in firewall_command(5070)


def test_taubheit_wird_gemeldet():
    from app.services.phone.conversation import DEAF_NOTICE

    assert "hoere dich" in DEAF_NOTICE.lower()
    assert "firewall" in DEAF_NOTICE.lower()


def test_sip_bindet_mit_reuseaddr():
    import inspect

    from app.services.phone.stack import SipStack

    quelle = inspect.getsource(SipStack.start)
    assert "SO_REUSEADDR" in quelle
    assert "reuse_address=True" in quelle
