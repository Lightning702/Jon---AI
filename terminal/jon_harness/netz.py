from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import threading
import time
import urllib.parse

AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
_dns: dict[str, tuple[float, list[str]]] = {}
_dns_lock = threading.Lock()
_kontext: ssl.SSLContext | None = None


class NetzFehler(Exception):
    def __init__(self, text: str, status: int = 0, roh: str = "") -> None:
        super().__init__(text)
        self.status = status
        self.roh = roh


def kontext() -> ssl.SSLContext:
    global _kontext
    if _kontext is None:
        _kontext = ssl.create_default_context()
        try:
            import certifi

            _kontext.load_verify_locations(certifi.where())
        except Exception:
            pass
    return _kontext


def _oeffentlich(host: str) -> list[str]:
    jetzt = time.time()
    with _dns_lock:
        eintrag = _dns.get(host)
        if eintrag and jetzt - eintrag[0] < 900 and eintrag[1]:
            return eintrag[1]
    gefunden: list[str] = []
    for basis, kopf in (("https://cloudflare-dns.com/dns-query", {"accept": "application/dns-json"}), ("https://dns.google/resolve", {})):
        try:
            antwort = anfrage("GET", basis + "?" + urllib.parse.urlencode({"name": host, "type": "A"}), kopf=kopf, zeit=6, umweg=False)
            for satz in antwort.json().get("Answer", []) or []:
                wert = str(satz.get("data") or "")
                try:
                    ip = ipaddress.ip_address(wert)
                except ValueError:
                    continue
                if not ip.is_private and not wert.startswith("100.") and wert not in gefunden:
                    gefunden.append(wert)
        except Exception:
            continue
        if gefunden:
            break
    with _dns_lock:
        _dns[host] = (jetzt, gefunden)
    return gefunden


class _UeberIP(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=kontext())
        self._ip = ip

    def connect(self) -> None:
        roh = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = kontext().wrap_socket(roh, server_hostname=self.host)


class Antwort:
    def __init__(self, status: int, kopf: dict, verbindung, roh) -> None:
        self.status = status
        self.kopf = kopf
        self._verbindung = verbindung
        self._roh = roh
        self._inhalt: bytes | None = None

    def inhalt(self) -> bytes:
        if self._inhalt is None:
            try:
                self._inhalt = self._roh.read()
            finally:
                self.schliessen()
        return self._inhalt

    def text(self) -> str:
        roh = self.inhalt()
        art = self.kopf.get("content-type", "")
        zeichen = "utf-8"
        if "charset=" in art:
            zeichen = art.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
        try:
            return roh.decode(zeichen, errors="replace")
        except LookupError:
            return roh.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text() or "{}")

    def zeilen(self):
        try:
            while True:
                zeile = self._roh.readline()
                if not zeile:
                    break
                yield zeile.decode("utf-8", errors="replace").rstrip("\r\n")
        finally:
            self.schliessen()

    def schliessen(self) -> None:
        try:
            self._verbindung.close()
        except Exception:
            pass


def _verbindung(teile: urllib.parse.SplitResult, zeit: float, ip: str = ""):
    host = teile.hostname or ""
    if teile.scheme == "https":
        port = teile.port or 443
        if ip:
            return _UeberIP(host, port, ip, zeit)
        return http.client.HTTPSConnection(host, port, timeout=zeit, context=kontext())
    return http.client.HTTPConnection(host, teile.port or 80, timeout=zeit)


def anfrage(methode: str, url: str, daten=None, kopf: dict | None = None, zeit: float = 60, strom: bool = False, umweg: bool = True, weiterleitungen: int = 5) -> Antwort:
    teile = urllib.parse.urlsplit(url)
    pfad = teile.path or "/"
    if teile.query:
        pfad += "?" + teile.query
    koerper = None
    alle = {"User-Agent": AGENT, "Accept": "*/*", "Accept-Encoding": "identity"}
    alle.update(kopf or {})
    if daten is not None:
        if isinstance(daten, (bytes, bytearray)):
            koerper = bytes(daten)
        elif isinstance(daten, str):
            koerper = daten.encode("utf-8")
        else:
            koerper = json.dumps(daten, ensure_ascii=False).encode("utf-8")
            alle.setdefault("Content-Type", "application/json")
    versuche = [""]
    letzter: Exception | None = None
    index = 0
    while index < len(versuche):
        ip = versuche[index]
        index += 1
        verbindung = _verbindung(teile, zeit, ip)
        try:
            verbindung.request(methode, pfad, body=koerper, headers=alle)
            roh = verbindung.getresponse()
        except (OSError, http.client.HTTPException) as fehler:
            letzter = fehler
            try:
                verbindung.close()
            except Exception:
                pass
            if umweg and not ip and (teile.hostname or "").endswith(".ts.net") and isinstance(fehler, OSError) and not isinstance(fehler, socket.timeout):
                versuche.extend(_oeffentlich(teile.hostname or "")[:3])
            continue
        kopfzeilen = {k.lower(): v for k, v in roh.getheaders()}
        if roh.status in (301, 302, 303, 307, 308) and kopfzeilen.get("location") and weiterleitungen > 0:
            ziel = urllib.parse.urljoin(url, kopfzeilen["location"])
            roh.read()
            verbindung.close()
            neue = "GET" if roh.status == 303 else methode
            return anfrage(neue, ziel, daten if neue != "GET" else None, kopf, zeit, strom, umweg, weiterleitungen - 1)
        antwort = Antwort(roh.status, kopfzeilen, verbindung, roh)
        if roh.status >= 400:
            text = antwort.text()
            raise NetzFehler(fehlertext(roh.status, text), roh.status, text)
        if not strom:
            antwort.inhalt()
        return antwort
    raise NetzFehler(f"Keine Verbindung zu {teile.hostname}: {letzter}")


def fehlertext(status: int, text: str) -> str:
    meldung = ""
    try:
        daten = json.loads(text)
        if isinstance(daten, dict):
            fehler = daten.get("error")
            if isinstance(fehler, dict):
                meldung = str(fehler.get("message") or "")
            elif isinstance(fehler, str):
                meldung = fehler
            meldung = meldung or str(daten.get("detail") or daten.get("message") or daten.get("fehler") or "")
    except ValueError:
        meldung = text.strip()[:300]
    if status == 401:
        return "Der API-Schlüssel wurde abgelehnt (401). Mit /api kannst du einen neuen eingeben." + (f" {meldung}" if meldung else "")
    if status == 402:
        return "Beim Anbieter ist kein Guthaben mehr (402)." + (f" {meldung}" if meldung else "")
    if status == 429:
        return meldung or "Zu viele Anfragen (429). Warte kurz oder wechsle mit /modell das Modell."
    return f"Fehler {status}: {meldung or 'ohne Beschreibung'}"


def strom_ereignisse(antwort: Antwort):
    for zeile in antwort.zeilen():
        if not zeile.startswith("data:"):
            continue
        inhalt = zeile[5:].strip()
        if not inhalt:
            continue
        if inhalt == "[DONE]":
            break
        try:
            yield json.loads(inhalt)
        except ValueError:
            continue
