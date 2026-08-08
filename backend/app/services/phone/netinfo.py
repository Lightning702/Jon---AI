from __future__ import annotations

import ipaddress
import json
import socket
import subprocess
import sys
import time

VIRTUAL_HINTS = (
    "vethernet",
    "virtualbox",
    "vmware",
    "hyper-v",
    "loopback",
    "bluetooth",
    "docker",
    "wsl",
    "npcap",
    "default switch",
)
VPN_HINTS = (
    "protun",
    "proton",
    "nordlynx",
    "wireguard",
    "openvpn",
    "tap-windows",
    "tunnel",
    "vpn",
    "zerotier",
    "hamachi",
)
MESH_HINTS = ("tailscale", "tailnet")
PHYSICAL_HINTS = ("wlan", "wi-fi", "wifi", "wireless", "ethernet", "lan-verbindung")

_cache: tuple[float, list[dict]] = (0.0, [])
_CACHE_SECONDS = 20.0


def _powershell_interfaces() -> list[dict]:
    script = (
        "Get-NetIPAddress -AddressFamily IPv4 | "
        "Where-Object { $_.IPAddress -ne '127.0.0.1' } | ForEach-Object { "
        "$a = Get-NetAdapter -InterfaceIndex $_.InterfaceIndex -ErrorAction SilentlyContinue; "
        "[PSCustomObject]@{ ip = $_.IPAddress; name = $_.InterfaceAlias; "
        "status = [string]$a.Status; description = [string]$a.InterfaceDescription } } | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        raw = result.stdout.decode("utf-8", "replace").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [
            {
                "ip": str(item.get("ip", "")),
                "name": str(item.get("name", "")),
                "status": str(item.get("status", "")),
                "description": str(item.get("description", "")),
            }
            for item in data
            if item.get("ip")
        ]
    except Exception:
        return []


def _fallback_interfaces() -> list[dict]:
    found: list[dict] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if address and not address.startswith("127."):
                found.append(
                    {"ip": address, "name": "", "status": "Up", "description": ""}
                )
    except OSError:
        pass
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        found.append(
            {"ip": probe.getsockname()[0], "name": "", "status": "Up", "description": ""}
        )
    except OSError:
        pass
    finally:
        probe.close()
    unique: dict[str, dict] = {}
    for item in found:
        unique.setdefault(item["ip"], item)
    return list(unique.values())


def _kind(entry: dict) -> str:
    haystack = f"{entry.get('name', '')} {entry.get('description', '')}".lower()
    if any(hint in haystack for hint in MESH_HINTS):
        return "mesh"
    if any(hint in haystack for hint in VPN_HINTS):
        return "vpn"
    if any(hint in haystack for hint in VIRTUAL_HINTS):
        return "virtual"
    if any(hint in haystack for hint in PHYSICAL_HINTS):
        return "lan"
    return "unbekannt"


def _score(entry: dict) -> int:
    try:
        address = ipaddress.ip_address(entry["ip"])
    except ValueError:
        return -100
    if address.is_loopback or address.is_link_local or address.is_unspecified:
        return -100
    if str(entry.get("status", "")).lower() in ("down", "disconnected", "notpresent"):
        return -50
    kind = entry["kind"]
    score = 0
    if kind == "lan":
        score += 60
    elif kind == "mesh":
        score += 30
    elif kind == "unbekannt":
        score += 20
    elif kind == "vpn":
        score -= 40
    elif kind == "virtual":
        score -= 60
    if address.is_private:
        score += 10
    text = entry["ip"]
    if text.startswith("192.168.56.") or text.startswith("172.3"):
        score -= 25
    return score


def reset_cache() -> None:
    global _cache
    _cache = (0.0, [])


def interfaces(refresh: bool = False) -> list[dict]:
    global _cache
    now = time.monotonic()
    if not refresh and _cache[1] and now - _cache[0] < _CACHE_SECONDS:
        return _cache[1]
    raw = _powershell_interfaces() if sys.platform == "win32" else []
    if not raw:
        raw = _fallback_interfaces()
    entries: list[dict] = []
    for item in raw:
        item["kind"] = _kind(item)
        item["score"] = _score(item)
        item["usable"] = item["score"] > -50
        entries.append(item)
    entries.sort(key=lambda e: e["score"], reverse=True)
    _cache = (now, entries)
    return entries


def best_address(preferred: str = "") -> str:
    if preferred:
        return preferred
    for entry in interfaces():
        if entry["usable"]:
            return entry["ip"]
    return "127.0.0.1"


def describe(entry: dict) -> str:
    labels = {
        "lan": "LAN oder WLAN",
        "vpn": "VPN-Tunnel",
        "virtual": "virtueller Adapter",
        "mesh": "Tailscale",
        "unbekannt": "unbekannt",
    }
    name = entry.get("name") or entry.get("description") or "Adapter"
    return f"{name} ({labels.get(entry['kind'], entry['kind'])})"
