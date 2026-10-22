from __future__ import annotations

import asyncio
import ipaddress
import threading
import time

import httpx

DOH = (
    ("https://cloudflare-dns.com/dns-query", {"accept": "application/dns-json"}),
    ("https://dns.google/resolve", {}),
)
ENDUNGEN = (".ts.net",)
_cache: dict[str, tuple[float, list[str]]] = {}
_lock = threading.Lock()


def umleitbar(host: str) -> bool:
    return bool(host) and host.lower().endswith(ENDUNGEN)


def oeffentlich_aufloesen(host: str) -> list[str]:
    jetzt = time.time()
    with _lock:
        eintrag = _cache.get(host)
        if eintrag and jetzt - eintrag[0] < 900 and eintrag[1]:
            return list(eintrag[1])
    adressen: list[str] = []
    for adresse, kopf in DOH:
        try:
            antwort = httpx.get(adresse, params={"name": host, "type": "A"}, headers=kopf, timeout=6)
            for eintrag in antwort.json().get("Answer", []) or []:
                wert = str(eintrag.get("data") or "")
                try:
                    ip = ipaddress.ip_address(wert)
                except ValueError:
                    continue
                if not ip.is_private and not ip.is_loopback and wert not in adressen and not wert.startswith("100."):
                    adressen.append(wert)
        except Exception:
            continue
        if adressen:
            break
    with _lock:
        _cache[host] = (jetzt, adressen)
    return adressen


def _umgeleitet(request: httpx.Request, ip: str) -> httpx.Request:
    host = request.url.host
    request.url = request.url.copy_with(host=ip)
    request.headers["Host"] = host
    request.extensions = {**request.extensions, "sni_hostname": host}
    return request


class AusweichTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        try:
            return await super().handle_async_request(request)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            if not umleitbar(host):
                raise
            adressen = await asyncio.to_thread(oeffentlich_aufloesen, host)
            if not adressen:
                raise
        letzter: Exception | None = None
        for ip in adressen[:3]:
            try:
                return await super().handle_async_request(_umgeleitet(request, ip))
            except (httpx.ConnectError, httpx.ConnectTimeout) as fehler:
                letzter = fehler
        raise letzter or httpx.ConnectError("keine Verbindung")


class AusweichTransportSync(httpx.HTTPTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        try:
            return super().handle_request(request)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            if not umleitbar(host):
                raise
            adressen = oeffentlich_aufloesen(host)
            if not adressen:
                raise
        letzter: Exception | None = None
        for ip in adressen[:3]:
            try:
                return super().handle_request(_umgeleitet(request, ip))
            except (httpx.ConnectError, httpx.ConnectTimeout) as fehler:
                letzter = fehler
        raise letzter or httpx.ConnectError("keine Verbindung")


def async_client(**optionen) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=AusweichTransport(), **optionen)


def sync_client(**optionen) -> httpx.Client:
    return httpx.Client(transport=AusweichTransportSync(), **optionen)
