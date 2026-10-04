from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

TAG = 86400
ADMIN_TAGE = 90
ENTWICKLER_TAGE = 14
ZEICHEN = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
LAENGE = 20
MAX_CODES = 500
FEHLER_PRO_IP = 8
FEHLER_FENSTER = 900
FEHLER_GESAMT = 120
GERAET = "^[a-f0-9]{20}$"


def b64url(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode()


def b64url_lesen(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def verzeichnis() -> Path:
    return Path(os.environ.get("JON_CODES_DIR") or Path.home() / ".local" / "share" / "jon-codes")


def normalisieren(eingabe: str) -> str:
    code = re.sub(r"[^A-Z0-9]", "", (eingabe or "").upper())
    if len(code) == LAENGE + 3 and code.startswith("ENT"):
        code = code[3:]
    return code if len(code) == LAENGE and all(z in ZEICHEN for z in code) else ""


def anzeigen(code: str) -> str:
    return "ENT-" + "-".join(code[i:i + 4] for i in range(0, LAENGE, 4))


def admin_kennung(passwort: str) -> str:
    return hashlib.sha256(f"jon-admin:{passwort}".encode()).hexdigest()[:16]


def admin_daten(passwort: str) -> dict:
    if len(passwort) < 12:
        raise ValueError("Der Admin-Code braucht mindestens 12 Zeichen.")
    salz = secrets.token_bytes(16)
    return {"salz": salz.hex(), "hash": hashlib.scrypt(passwort.encode(), salt=salz, n=2**14, r=8, p=1, dklen=32).hex(), "pk": admin_kennung(passwort)}


class Codeserver:
    def __init__(self, ordner: Path | None = None, uhr=time.time) -> None:
        self.ordner = Path(ordner or verzeichnis())
        self.uhr = uhr
        self.lock = threading.Lock()
        self.schluessel_lock = threading.Lock()
        self.fehler_ip: dict[str, deque] = {}
        self.fehler_alle: deque = deque()
        self._schluessel: Ed25519PrivateKey | None = None

    def _lesen(self, name: str, standard: dict) -> dict:
        try:
            wert = json.loads((self.ordner / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return standard
        return wert if isinstance(wert, dict) else standard

    def _schreiben(self, name: str, inhalt: bytes) -> None:
        self.ordner.mkdir(parents=True, exist_ok=True)
        os.chmod(self.ordner, 0o700)
        ziel = self.ordner / name
        temp = ziel.with_name(f"{ziel.name}.{os.getpid()}.tmp")
        griff = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(griff, "wb") as datei:
            datei.write(inhalt)
        os.replace(temp, ziel)

    def _json(self, name: str, daten: dict) -> None:
        self._schreiben(name, json.dumps(daten, ensure_ascii=False, indent=1).encode("utf-8"))

    def schluessel(self) -> Ed25519PrivateKey:
        if self._schluessel:
            return self._schluessel
        pfad = self.ordner / "schluessel.pem"
        with self.schluessel_lock:
            try:
                geladen = serialization.load_pem_private_key(pfad.read_bytes(), None)
            except FileNotFoundError:
                geladen = Ed25519PrivateKey.generate()
                self._schreiben("schluessel.pem", geladen.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        if not isinstance(geladen, Ed25519PrivateKey):
            raise RuntimeError("schluessel.pem ist kein Ed25519-Schlüssel.")
        self._schluessel = geladen
        return geladen

    def oeffentlich(self) -> str:
        return base64.b64encode(self.schluessel().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()

    def signieren(self, inhalt: dict) -> str:
        kopf = "JON1." + b64url(json.dumps({**inhalt, "iat": int(self.uhr())}, ensure_ascii=False).encode("utf-8"))
        return kopf + "." + b64url(self.schluessel().sign(kopf.encode()))

    def lesen(self, token: str) -> dict:
        teile = (token or "").strip().split(".")
        if len(teile) != 3 or teile[0] != "JON1":
            raise HTTPException(400, "Das ist keine Jon-Lizenz.")
        try:
            self.schluessel().public_key().verify(b64url_lesen(teile[2]), f"{teile[0]}.{teile[1]}".encode())
            inhalt = json.loads(b64url_lesen(teile[1]))
        except (InvalidSignature, ValueError, TypeError):
            raise HTTPException(403, "Diese Lizenz stammt nicht von diesem Codeserver.")
        if not isinstance(inhalt, dict) or inhalt.get("stufe") not in {"admin", "entwickler"}:
            raise HTTPException(403, "Diese Lizenz stammt nicht von diesem Codeserver.")
        return inhalt

    def admin(self) -> dict:
        return self._lesen("admin.json", {})

    def admin_setzen(self, daten: dict) -> None:
        if not all(isinstance(daten.get(k), str) and daten[k] for k in ("salz", "hash", "pk")):
            raise ValueError("Unvollständige Admin-Daten.")
        with self.lock:
            self._json("admin.json", {"salz": daten["salz"], "hash": daten["hash"], "pk": daten["pk"], "seit": int(self.uhr())})

    def ist_admin_code(self, eingabe: str) -> bool:
        daten = self.admin()
        if not daten.get("hash") or not 12 <= len(eingabe) <= 400:
            return False
        try:
            soll = bytes.fromhex(daten["hash"])
            ist = hashlib.scrypt(eingabe.encode(), salt=bytes.fromhex(daten["salz"]), n=2**14, r=8, p=1, dklen=32)
        except (ValueError, KeyError):
            return False
        return hmac.compare_digest(soll, ist)

    def admin_token(self, geraet: str) -> str:
        pk = self.admin().get("pk")
        if not pk:
            raise HTTPException(503, "Auf dem Codeserver ist noch kein Admin-Code eingerichtet.")
        return self.signieren({"stufe": "admin", "name": "Admin", "geraete": [geraet], "exp": int(self.uhr()) + ADMIN_TAGE * TAG, "pk": pk, "quelle": "codes"})

    def _codes(self) -> dict:
        daten = self._lesen("codes.json", {})
        if not daten.get("pfeffer"):
            daten = {"pfeffer": secrets.token_hex(32), "codes": daten.get("codes", [])}
        daten.setdefault("codes", [])
        return daten

    @staticmethod
    def _hash(daten: dict, code: str) -> str:
        return hmac.new(bytes.fromhex(daten["pfeffer"]), code.encode(), hashlib.sha256).hexdigest()

    def entwickler_token(self, eintrag: dict, geraet: str) -> str:
        return self.signieren({"stufe": "entwickler", "name": eintrag.get("name") or "Entwickler", "geraete": [geraet], "exp": int(self.uhr()) + ENTWICKLER_TAGE * TAG, "code": eintrag["id"], "quelle": "codes"})

    def _bremse(self, ip: str) -> None:
        jetzt = self.uhr()
        verlauf = self.fehler_ip.get(ip, deque())
        while verlauf and jetzt - verlauf[0] > FEHLER_FENSTER:
            verlauf.popleft()
        while self.fehler_alle and jetzt - self.fehler_alle[0] > 3600:
            self.fehler_alle.popleft()
        if len(verlauf) >= FEHLER_PRO_IP:
            raise HTTPException(429, "Zu viele falsche Codes. Bitte warte 15 Minuten.")
        if len(self.fehler_alle) >= FEHLER_GESAMT:
            raise HTTPException(429, "Der Codeserver nimmt gerade keine weiteren Versuche an. Bitte später noch einmal.")

    def _fehlversuch(self, ip: str) -> None:
        jetzt = self.uhr()
        self.fehler_ip.setdefault(ip, deque()).append(jetzt)
        self.fehler_alle.append(jetzt)
        if len(self.fehler_ip) > 5000:
            self.fehler_ip = {k: v for k, v in self.fehler_ip.items() if v and jetzt - v[-1] < FEHLER_FENSTER}

    def einloesen(self, eingabe: str, geraet: str, ip: str) -> dict | None:
        self._bremse(ip)
        roh = (eingabe or "").strip()
        if self.ist_admin_code(roh):
            return {"token": self.admin_token(geraet), "stufe": "admin"}
        code = normalisieren(roh)
        if code:
            with self.lock:
                daten = self._codes()
                gesucht = self._hash(daten, code)
                eintrag = next((c for c in daten["codes"] if hmac.compare_digest(c.get("hash", ""), gesucht)), None)
                if eintrag and eintrag.get("gesperrt"):
                    raise HTTPException(403, "Dieser Entwickler-Code wurde vom Admin gesperrt.")
                if eintrag:
                    if geraet not in eintrag["geraete"]:
                        if len(eintrag["geraete"]) >= int(eintrag.get("max_geraete", 3)):
                            raise HTTPException(403, f"Dieser Entwickler-Code ist schon auf {len(eintrag['geraete'])} Geräten aktiv. Bitte den Admin um einen neuen Code.")
                        eintrag["geraete"].append(geraet)
                    eintrag["zuletzt"] = int(self.uhr())
                    self._json("codes.json", daten)
                    return {"token": self.entwickler_token(eintrag, geraet), "stufe": "entwickler"}
        self._fehlversuch(ip)
        return None

    def erneuern(self, token: str, geraet: str) -> dict:
        inhalt = self.lesen(token)
        if geraet not in inhalt.get("geraete", []):
            raise HTTPException(403, "Diese Lizenz gehört zu einem anderen Gerät.")
        if inhalt["stufe"] == "admin":
            if inhalt.get("pk") != self.admin().get("pk"):
                raise HTTPException(403, "Der Admin-Code wurde geändert. Melde dich mit dem neuen Admin-Code an.")
            return {"token": self.admin_token(geraet)}
        with self.lock:
            daten = self._codes()
            eintrag = next((c for c in daten["codes"] if c["id"] == inhalt.get("code")), None)
            if not eintrag or eintrag.get("gesperrt"):
                raise HTTPException(403, "Dieser Entwickler-Code wurde vom Admin gesperrt.")
            if geraet not in eintrag["geraete"]:
                raise HTTPException(403, "Dieses Gerät ist für den Entwickler-Code nicht mehr freigeschaltet.")
            eintrag["zuletzt"] = int(self.uhr())
            self._json("codes.json", daten)
        return {"token": self.entwickler_token(eintrag, geraet)}

    def admin_pruefen(self, token: str, geraet: str) -> None:
        inhalt = self.lesen(token)
        if inhalt["stufe"] != "admin" or inhalt.get("pk") != self.admin().get("pk") or geraet not in inhalt.get("geraete", []) or float(inhalt.get("exp") or 0) < self.uhr():
            raise HTTPException(403, "Nur der Admin kann Entwickler-Codes verwalten.")

    def liste(self) -> list[dict]:
        daten = self._codes()
        return [{"id": c["id"], "name": c.get("name", ""), "erstellt": c.get("erstellt", 0), "zuletzt": c.get("zuletzt", 0), "geraete": len(c.get("geraete", [])), "max_geraete": int(c.get("max_geraete", 3)), "gesperrt": bool(c.get("gesperrt")), "ende": c.get("ende", "")} for c in sorted(daten["codes"], key=lambda c: c.get("erstellt", 0), reverse=True)]

    def erstellen(self, name: str, max_geraete: int) -> dict:
        code = "".join(secrets.choice(ZEICHEN) for _ in range(LAENGE))
        with self.lock:
            daten = self._codes()
            if len(daten["codes"]) >= MAX_CODES:
                raise HTTPException(409, f"Es gibt schon {MAX_CODES} Codes. Sperre alte Codes, bevor du neue erzeugst.")
            eintrag = {"id": secrets.token_hex(6), "name": name.strip()[:60], "hash": self._hash(daten, code), "ende": code[-4:], "erstellt": int(self.uhr()), "zuletzt": 0, "max_geraete": max_geraete, "geraete": [], "gesperrt": False}
            daten["codes"].append(eintrag)
            self._json("codes.json", daten)
        return {"code": anzeigen(code), "codes": self.liste()}

    def sperren(self, kennung: str, gesperrt: bool) -> dict:
        with self.lock:
            daten = self._codes()
            eintrag = next((c for c in daten["codes"] if c["id"] == kennung), None)
            if not eintrag:
                raise HTTPException(404, "Diesen Code gibt es nicht.")
            eintrag["gesperrt"] = gesperrt
            if gesperrt:
                eintrag["gesperrt_am"] = int(self.uhr())
            self._json("codes.json", daten)
        return {"codes": self.liste()}


class Einloesen(BaseModel):
    code: str = Field(min_length=1, max_length=400)
    geraet: str = Field(pattern=GERAET)


class Lizenz(BaseModel):
    token: str = Field(min_length=20, max_length=4000)
    geraet: str = Field(pattern=GERAET)


class Neu(Lizenz):
    name: str = Field(default="", max_length=60)
    geraete: int = Field(default=3, ge=1, le=20)


class Sperren(Lizenz):
    id: str = Field(pattern="^[a-f0-9]{12}$")
    gesperrt: bool = True


def adresse(request: Request) -> str:
    direkt = request.client.host if request.client else ""
    if direkt in {"127.0.0.1", "::1"}:
        weitergeleitet = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if weitergeleitet:
            return weitergeleitet
    return direkt or "unbekannt"


def erstellen(server: Codeserver | None = None, pause: float = 1.2) -> FastAPI:
    app = FastAPI(title="Jon Codeserver", docs_url=None, redoc_url=None, openapi_url=None)
    dienst = server or Codeserver()

    @app.get("/codes/status")
    async def status() -> dict:
        return {"ok": True, "oeffentlich": dienst.oeffentlich(), "admin": bool(dienst.admin().get("hash"))}

    @app.post("/codes/einloesen")
    async def einloesen(daten: Einloesen, request: Request) -> dict:
        ergebnis = await asyncio.to_thread(dienst.einloesen, daten.code, daten.geraet, adresse(request))
        if ergebnis is None:
            await asyncio.sleep(pause)
            raise HTTPException(403, "Dieser Code ist ungültig.")
        return ergebnis

    @app.post("/codes/erneuern")
    async def erneuern(daten: Lizenz) -> dict:
        return dienst.erneuern(daten.token, daten.geraet)

    @app.post("/codes/liste")
    async def liste(daten: Lizenz) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return {"codes": dienst.liste()}

    @app.post("/codes/erstellen")
    async def neu(daten: Neu) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.erstellen(daten.name, daten.geraete)

    @app.post("/codes/sperren")
    async def sperren(daten: Sperren) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.sperren(daten.id, daten.gesperrt)

    return app


def main(argumente: list[str] | None = None) -> None:
    argumente = sys.argv[1:] if argumente is None else argumente
    server = Codeserver()
    if argumente[:1] == ["admin"]:
        eingabe = sys.stdin.readline().strip()
        server.admin_setzen(json.loads(eingabe) if eingabe.startswith("{") else admin_daten(eingabe))
        print("Admin-Code gespeichert.")
        return
    if argumente[:1] == ["lizenz"] and len(argumente) == 2 and re.fullmatch(GERAET, argumente[1]):
        print(server.admin_token(argumente[1]))
        return
    if argumente[:1] == ["oeffentlich"]:
        print(server.oeffentlich())
        return
    if argumente:
        print("Aufruf: python -m app.codeserver [admin | lizenz <geraet> | oeffentlich]")
        raise SystemExit(2)
    import uvicorn

    server.oeffentlich()
    uvicorn.run(erstellen(server), host=os.environ.get("JON_CODES_HOST", "127.0.0.1"), port=int(os.environ.get("JON_CODES_PORT", "8791")), log_level="warning", proxy_headers=False)


if __name__ == "__main__":
    main()
