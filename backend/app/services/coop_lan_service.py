from __future__ import annotations

import asyncio
import ctypes
import ipaddress
import json
import os
import secrets
import socket
import subprocess
import time
from typing import Any

DISCOVERY_PORT = int(os.environ.get("JON_COOP_DISCOVERY_PORT", "8761"))
MAGIC = "jon-coop"
CACHE_TTL = 20.0
FIREWALL_RULE_TCP = "Jon Koop (Spiele)"
FIREWALL_RULE_UDP = "Jon Koop (Suche)"

VIRTUAL_HINTS = (
    "vethernet",
    "hyper-v",
    "virtualbox",
    "vmware",
    "vmnet",
    "virtual",
    "wsl",
    "docker",
    "loopback",
    "bluetooth",
    "tap-",
    "tap ",
    "tun",
    "vpn",
    "wireguard",
    "openvpn",
    "zerotier",
    "tailscale",
    "hamachi",
    "radmin",
    "nordlynx",
    "mullvad",
    "teredo",
    "isatap",
    "pseudo",
    "npcap",
)

REAL_TYPES = (6, 71)


class SockAddr(ctypes.Structure):
    _fields_ = [("family", ctypes.c_ushort), ("data", ctypes.c_ubyte * 26)]


class SocketAddress(ctypes.Structure):
    _fields_ = [("addr", ctypes.POINTER(SockAddr)), ("length", ctypes.c_int)]


class Unicast(ctypes.Structure):
    pass


Unicast._fields_ = [
    ("length", ctypes.c_ulong),
    ("flags", ctypes.c_ulong),
    ("next", ctypes.POINTER(Unicast)),
    ("address", SocketAddress),
    ("prefix_origin", ctypes.c_int),
    ("suffix_origin", ctypes.c_int),
    ("dad_state", ctypes.c_int),
    ("valid_lifetime", ctypes.c_ulong),
    ("preferred_lifetime", ctypes.c_ulong),
    ("lease_lifetime", ctypes.c_ulong),
    ("prefix_length", ctypes.c_ubyte),
]


class Gateway(ctypes.Structure):
    pass


Gateway._fields_ = [
    ("length", ctypes.c_ulong),
    ("reserved", ctypes.c_ulong),
    ("next", ctypes.POINTER(Gateway)),
    ("address", SocketAddress),
]


class Adapter(ctypes.Structure):
    pass


Adapter._fields_ = [
    ("length", ctypes.c_ulong),
    ("index", ctypes.c_ulong),
    ("next", ctypes.POINTER(Adapter)),
    ("name", ctypes.c_char_p),
    ("first_unicast", ctypes.POINTER(Unicast)),
    ("first_anycast", ctypes.c_void_p),
    ("first_multicast", ctypes.c_void_p),
    ("first_dns", ctypes.c_void_p),
    ("dns_suffix", ctypes.c_wchar_p),
    ("description", ctypes.c_wchar_p),
    ("friendly_name", ctypes.c_wchar_p),
    ("physical", ctypes.c_ubyte * 8),
    ("physical_length", ctypes.c_ulong),
    ("flags", ctypes.c_ulong),
    ("mtu", ctypes.c_ulong),
    ("if_type", ctypes.c_ulong),
    ("oper_status", ctypes.c_int),
    ("ipv6_index", ctypes.c_ulong),
    ("zone_indices", ctypes.c_ulong * 16),
    ("first_prefix", ctypes.c_void_p),
    ("transmit_speed", ctypes.c_ulonglong),
    ("receive_speed", ctypes.c_ulonglong),
    ("first_wins", ctypes.c_void_p),
    ("first_gateway", ctypes.POINTER(Gateway)),
]


def _is_virtual(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in VIRTUAL_HINTS)


def _usable(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if address.is_loopback or address.is_link_local or address.is_multicast:
        return False
    return not address.is_unspecified


def _probe_address() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return str(probe.getsockname()[0])
    except Exception:
        return ""
    finally:
        probe.close()


def _windows_interfaces() -> list[dict]:
    found: list[dict] = []
    size = ctypes.c_ulong(16384)
    for _ in range(4):
        buffer = ctypes.create_string_buffer(size.value)
        head = ctypes.cast(buffer, ctypes.POINTER(Adapter))
        result = ctypes.windll.iphlpapi.GetAdaptersAddresses(
            2, 0x0002 | 0x0004 | 0x0008 | 0x0080, None, head, ctypes.byref(size)
        )
        if result == 111:
            continue
        if result != 0:
            return []
        node = head
        while node:
            entry = node.contents
            name = entry.friendly_name or entry.description or ""
            gateway = ""
            hop = entry.first_gateway
            while hop and not gateway:
                sockaddr = hop.contents.address.addr
                if sockaddr and sockaddr.contents.family == socket.AF_INET:
                    found_hop = socket.inet_ntoa(bytes(sockaddr.contents.data[2:6]))
                    if found_hop != "0.0.0.0":
                        gateway = found_hop
                hop = hop.contents.next
            unicast = entry.first_unicast
            while unicast:
                item = unicast.contents
                sockaddr = item.address.addr
                if sockaddr and sockaddr.contents.family == socket.AF_INET:
                    raw = bytes(sockaddr.contents.data[2:6])
                    ip = socket.inet_ntoa(raw)
                    if _usable(ip):
                        found.append(
                            {
                                "ip": ip,
                                "prefix": int(item.prefix_length) or 24,
                                "name": str(name),
                                "type": int(entry.if_type),
                                "up": int(entry.oper_status) == 1,
                                "gateway": gateway,
                                "dhcp": int(item.prefix_origin) == 3,
                            }
                        )
                unicast = item.next
            node = entry.next
        return found
    return found


def _fallback_interfaces() -> list[dict]:
    found: list[dict] = []
    template = {"prefix": 24, "name": "", "type": 6, "up": True, "gateway": "", "dhcp": True}
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if _usable(ip):
                found.append({**template, "ip": ip})
    except Exception:
        pass
    probe = _probe_address()
    if probe and _usable(probe) and all(item["ip"] != probe for item in found):
        found.insert(0, {**template, "ip": probe})
    return found


_cache: dict[str, Any] = {"at": 0.0, "items": []}


def interfaces() -> list[dict]:
    now = time.monotonic()
    if _cache["items"] and now - float(_cache["at"]) < CACHE_TTL:
        return list(_cache["items"])
    raw: list[dict] = []
    if os.name == "nt":
        try:
            raw = _windows_interfaces()
        except Exception:
            raw = []
    if not raw:
        raw = _fallback_interfaces()

    def score(item: dict) -> tuple:
        try:
            private = 1 if ipaddress.ip_address(item["ip"]).is_private else 0
        except ValueError:
            private = 0
        clean = 0 if _is_virtual(str(item.get("name", ""))) else 1
        up = 1 if item.get("up", True) else 0
        routed = 1 if str(item.get("gateway", "")) else 0
        dhcp = 1 if item.get("dhcp") else 0
        real = 1 if int(item.get("type", 0)) in REAL_TYPES else 0
        wide = 1 if int(item.get("prefix", 24)) < 32 else 0
        return (clean, up, routed, dhcp, wide, real, private)

    ranked = sorted(raw, key=score, reverse=True)
    _cache["at"] = now
    _cache["items"] = ranked
    return list(ranked)


def local_addresses() -> list[str]:
    seen: list[str] = []
    for item in interfaces():
        ip = str(item.get("ip", ""))
        if ip and ip not in seen:
            seen.append(ip)
    return seen


def invite_host() -> str:
    addresses = local_addresses()
    return addresses[0] if addresses else "127.0.0.1"


def address_for_peer(peer: str) -> str:
    try:
        other = ipaddress.ip_address(peer)
    except ValueError:
        return invite_host()
    for item in interfaces():
        try:
            network = ipaddress.ip_network(
                f"{item['ip']}/{int(item.get('prefix', 24))}", strict=False
            )
        except ValueError:
            continue
        if other in network:
            return str(item["ip"])
    return invite_host()


def broadcast_targets() -> list[str]:
    targets = ["255.255.255.255"]
    for item in interfaces():
        try:
            network = ipaddress.ip_network(
                f"{item['ip']}/{int(item.get('prefix', 24))}", strict=False
            )
        except ValueError:
            continue
        if network.num_addresses < 4 or network.num_addresses > 65536:
            continue
        address = str(network.broadcast_address)
        if address not in targets:
            targets.append(address)
    return targets


def _powershell(command: str, timeout: float = 20.0) -> tuple[int, str]:
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return 1, ""
    return done.returncode, (done.stdout or "").strip()


_firewall_cache: dict[str, Any] = {"at": 0.0, "state": None}


def firewall_state(refresh: bool = False) -> dict:
    if os.name != "nt":
        return {"supported": False, "ok": True, "rules": []}
    now = time.monotonic()
    cached = _firewall_cache["state"]
    if cached is not None and not refresh and now - float(_firewall_cache["at"]) < 15.0:
        return dict(cached)
    code, out = _powershell(
        "$n=@('" + FIREWALL_RULE_TCP + "','" + FIREWALL_RULE_UDP + "');"
        "($n | Where-Object { Get-NetFirewallRule -DisplayName $_ "
        "-ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq 'True' } }) -join ','",
        timeout=25.0,
    )
    rules = [part for part in out.split(",") if part.strip()] if code == 0 else []
    state = {
        "supported": True,
        "ok": len(rules) >= 2,
        "rules": rules,
    }
    _firewall_cache["at"] = now
    _firewall_cache["state"] = state
    return dict(state)


def ensure_firewall(tcp_ports: list[int], udp_ports: list[int]) -> dict:
    if os.name != "nt":
        return {"started": False, "supported": False}
    tcp = ",".join(str(int(port)) for port in tcp_ports)
    udp = ",".join(str(int(port)) for port in udp_ports)
    inner = (
        f"Remove-NetFirewallRule -DisplayName '{FIREWALL_RULE_TCP}' -ErrorAction SilentlyContinue;"
        f"Remove-NetFirewallRule -DisplayName '{FIREWALL_RULE_UDP}' -ErrorAction SilentlyContinue;"
        f"New-NetFirewallRule -DisplayName '{FIREWALL_RULE_TCP}' -Direction Inbound -Action Allow "
        f"-Protocol TCP -LocalPort {tcp} -Profile Any | Out-Null;"
        f"New-NetFirewallRule -DisplayName '{FIREWALL_RULE_UDP}' -Direction Inbound -Action Allow "
        f"-Protocol UDP -LocalPort {udp} -Profile Any | Out-Null"
    )
    escaped = inner.replace("'", "''")
    outer = (
        "Start-Process powershell -Verb RunAs -WindowStyle Hidden "
        f"-ArgumentList '-NoProfile','-NonInteractive','-Command','{escaped}'"
    )
    code, _ = _powershell(outer, timeout=60.0)
    _firewall_cache["state"] = None
    return {"started": code == 0, "supported": True}


class CoopBeacon:
    def __init__(self) -> None:
        self._service: Any = None
        self._transport: asyncio.DatagramTransport | None = None
        self._node = secrets.token_hex(4)
        self._queries: dict[str, dict] = {}
        self._tcp_port = 8759
        self._ws_port = 8760
        self._answers = False

    def bind(self, service: Any, tcp_port: int, ws_port: int) -> None:
        self._service = service
        self._tcp_port = tcp_port
        self._ws_port = ws_port

    @property
    def online(self) -> bool:
        return self._transport is not None

    @property
    def findable(self) -> bool:
        return self._transport is not None and self._answers

    @property
    def tcp_port(self) -> int:
        return self._tcp_port

    @property
    def ws_port(self) -> int:
        return self._ws_port

    def _entry(self, lobby: dict, sender: str) -> dict:
        return {
            **lobby,
            "host": sender,
            "tcp_port": self._tcp_port,
            "ws_port": self._ws_port,
            "origin": f"http://{sender}:{self._ws_port}",
        }

    def _send(self, payload: dict, target: tuple | None = None) -> None:
        if self._transport is None:
            return
        packet = json.dumps(payload).encode("utf-8")
        targets = [target] if target else [(host, DISCOVERY_PORT) for host in broadcast_targets()]
        for address in targets:
            try:
                self._transport.sendto(packet, address)
            except Exception:
                continue

    def _reply(self, lobby: dict, query: str, addr: tuple) -> None:
        self._send(
            {
                "jon": MAGIC,
                "t": "here",
                "q": query,
                "node": self._node,
                "tcp": self._tcp_port,
                "ws": self._ws_port,
                "hint": address_for_peer(addr[0]),
                "hosts": local_addresses(),
                "lobby": lobby,
            },
            (addr[0], int(addr[1]) or DISCOVERY_PORT),
        )

    def _on_packet(self, data: bytes, addr: tuple) -> None:
        try:
            payload = json.loads(data.decode("utf-8", errors="replace"))
        except Exception:
            return
        if not isinstance(payload, dict) or payload.get("jon") != MAGIC:
            return
        kind = str(payload.get("t", ""))
        query = str(payload.get("q", ""))

        if kind == "where" and self._service is not None:
            lobby = self._service.beacon_lookup(str(payload.get("code", "")))
            if lobby is not None:
                self._reply(lobby, query, addr)
            return

        if kind == "scan" and self._service is not None:
            for lobby in self._service.beacon_list():
                self._reply(lobby, query, addr)
            return

        if kind != "here":
            return
        if str(payload.get("node", "")) == self._node:
            return
        pending = self._queries.get(query)
        if pending is None:
            return
        lobby = payload.get("lobby")
        if not isinstance(lobby, dict):
            return
        host = str(payload.get("hint") or "").strip() or addr[0]
        entry = self._entry(lobby, host)
        entry["tcp_port"] = int(payload.get("tcp") or self._tcp_port)
        entry["ws_port"] = int(payload.get("ws") or self._ws_port)
        entry["origin"] = f"http://{host}:{entry['ws_port']}"
        entry["source"] = addr[0]
        hosts = payload.get("hosts")
        entry["hosts"] = [str(item) for item in hosts] if isinstance(hosts, list) else [host]
        pending["results"].append(entry)
        future = pending.get("future")
        if future is not None and not future.done():
            future.set_result(entry)

    async def serve(self, tcp_port: int, ws_port: int) -> None:
        self._tcp_port = tcp_port
        self._ws_port = ws_port
        loop = asyncio.get_running_loop()
        beacon = self

        class Protocol(asyncio.DatagramProtocol):
            def connection_made(self, transport) -> None:
                beacon._transport = transport

            def datagram_received(self, data: bytes, addr) -> None:
                beacon._on_packet(data, addr)

            def error_received(self, exc) -> None:
                return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            self._answers = True
        except Exception:
            try:
                sock.bind(("0.0.0.0", 0))
                self._answers = False
                print(
                    f"Koop-Suche: Port {DISCOVERY_PORT} belegt - dieses Jon findet "
                    "andere Lobbys, wird selbst aber nur ueber CODE@adresse gefunden",
                    flush=True,
                )
            except Exception:
                sock.close()
                return
        try:
            transport, _ = await loop.create_datagram_endpoint(Protocol, sock=sock)
        except Exception:
            sock.close()
            return
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            transport.close()
            self._transport = None

    async def find(self, code: str, timeout: float = 1.8) -> dict | None:
        wanted = str(code or "").strip().upper()
        if not wanted or self._transport is None:
            return None
        query = secrets.token_hex(4)
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._queries[query] = {"future": future, "results": []}
        request = {"jon": MAGIC, "t": "where", "code": wanted, "q": query, "node": self._node}
        try:
            self._send(request)
            await asyncio.sleep(min(0.35, timeout / 3.0))
            if not future.done():
                self._send(request)
            return await asyncio.wait_for(future, timeout)
        except Exception:
            return None
        finally:
            self._queries.pop(query, None)

    async def scan(self, timeout: float = 1.4) -> list[dict]:
        if self._transport is None:
            return []
        query = secrets.token_hex(4)
        self._queries[query] = {"future": None, "results": []}
        request = {"jon": MAGIC, "t": "scan", "q": query, "node": self._node}
        try:
            self._send(request)
            await asyncio.sleep(timeout * 0.5)
            self._send(request)
            await asyncio.sleep(timeout * 0.5)
            results = self._queries[query]["results"]
        except Exception:
            results = []
        finally:
            self._queries.pop(query, None)
        unique: dict[str, dict] = {}
        for entry in results:
            key = f"{entry.get('code', '')}@{entry.get('host', '')}"
            unique[key] = entry
        return list(unique.values())


_beacon: CoopBeacon | None = None


def get_coop_beacon() -> CoopBeacon:
    global _beacon
    if _beacon is None:
        _beacon = CoopBeacon()
    return _beacon
