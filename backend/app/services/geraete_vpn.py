from __future__ import annotations

import ipaddress
import json
import os
import shutil
import socket
import subprocess
import time
from functools import lru_cache
from urllib.parse import urlsplit


def tailscale_status() -> dict:
    return _tailscale_status(int(time.monotonic() // 5))


@lru_cache(maxsize=1)
def _tailscale_status(zeitfenster: int) -> dict:
    pfad = shutil.which("tailscale")
    if not pfad and os.name == "nt":
        kandidat = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe")
        if os.path.isfile(kandidat):
            pfad = kandidat
    if not pfad:
        return {"installiert": False, "verbunden": False, "adressen": [], "geraete": []}
    try:
        optionen = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        result = subprocess.run([pfad, "status", "--json"], capture_output=True, text=True, timeout=5, **optionen)
        daten = json.loads(result.stdout)
        return {
            "installiert": True,
            "verbunden": daten.get("BackendState") == "Running",
            "adressen": daten.get("TailscaleIPs") or [],
            "geraete": [
                {"name": p.get("HostName", ""), "adresse": next((a for a in (p.get("TailscaleIPs") or []) if ":" not in a), ""), "online": bool(p.get("Online")), "system": p.get("OS", "")}
                for p in (daten.get("Peer") or {}).values()
            ],
        }
    except Exception:
        return {"installiert": True, "verbunden": False, "adressen": [], "geraete": []}


def private_adresse(roh: str) -> str:
    adresse = roh.strip().rstrip("/")
    if "://" not in adresse:
        adresse = "http://" + adresse
    parsed = urlsplit(adresse)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("Eine reine LAN- oder Tailscale-Serveradresse eingeben.")
    port = parsed.port or 8756
    netze = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "fd7a:115c:a1e0::/48")]
    ips = [ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)]
    if not ips or not all(any(ip in netz for netz in netze if ip.version == netz.version) for ip in ips):
        raise ValueError("Der Pi muss über LAN oder Tailscale erreichbar sein.")
    host = f"[{ips[0]}]" if ips[0].version == 6 else str(ips[0])
    return f"{parsed.scheme}://{host}:{port}"


class DirektDraht:
    def __init__(self, adresse: str):
        self.adresse = private_adresse(adresse)

    def frage(self, thema, art, kennung, schluessel, inhalt, wartezeit=25.0):
        import httpx
        from app.services.handy_service import _verschluesseln, _entschluesseln
        from app.services.verbund_service import VerbundFehler

        aad = f"{art}:{kennung}".encode()
        paket = {"v": 2, "k": art, "i": kennung, **_verschluesseln(schluessel, aad, inhalt)}
        try:
            response = httpx.post(self.adresse + "/api/handy/gate", json=paket, timeout=wartezeit, follow_redirects=False)
            response.raise_for_status()
            return _entschluesseln(schluessel, aad, response.json())
        except Exception as exc:
            raise VerbundFehler("Der Pi antwortet nicht über die verschlüsselte Direktverbindung.") from exc
