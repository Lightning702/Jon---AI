from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import Counter, deque
from datetime import date
from pathlib import Path

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

ZEICHEN = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
LAENGE = 20
MAX_CODES = 500
FEHLER_PRO_IP = 8
FEHLER_FENSTER = 900
FEHLER_GESAMT = 120
GERAET = "^[a-f0-9]{20}$"
KENNUNG = "^[a-f0-9]{12}$"
TAG = 86400
ARTEN = {"entwickler": "Entwickler", "premium": "Premium", "admin": "Admin"}
TEAM = {"admin", "entwickler"}
FLAGS = {
    "beta": ("Beta-Versionen", "Neue Jon-Versionen früher als alle anderen bekommen"),
    "inspektor": ("Jon-Inspektor", "Jede Modellanfrage mit Werkzeugen, Tokens und Dauer ansehen"),
    "modell": ("Modellzugang über FelWorks", "Cloud-Modelle über den FelWorks-Zugang nutzen, ohne eigenen Schlüssel"),
    "skills": ("Skills teilen", "Eigene Skills mit dem Team teilen und Skills anderer installieren"),
    "fehlerbericht": ("Fehler mit einem Klick", "Log, System und Bildschirm direkt an den Admin schicken"),
}
NACHRICHTEN = {"idee", "fehler", "nachricht", "rundschreiben"}
IDEE_STATUS = {"neu": "Neu", "geplant": "Geplant", "in_arbeit": "In Arbeit", "fertig": "Fertig", "abgelehnt": "Abgelehnt"}
MAX_NACHRICHTEN = 3000
MAX_BILD = 1_200_000
MAX_SKILL = 100_000
KONTINGENT = 300
KOSTENLOS_PRO_IP = 12
KOSTENLOS_MAX = 200_000
KOSTENLOS_NAME = "Jon Premium kostenlos"
DIENSTE = ("jon", "jon-codes", "jon-demo")
MODELLE = ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3.5-lightning-30b-a3b", "mistralai/mistral-nemotron"]
WURZEL = Path(__file__).resolve().parents[2]


def b64url(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode()


def b64url_lesen(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def verzeichnis() -> Path:
    return Path(os.environ.get("JON_CODES_DIR") or Path.home() / ".local" / "share" / "jon-codes")


def normalisieren(eingabe: str) -> str:
    code = re.sub(r"[^A-Z0-9]", "", (eingabe or "").upper())
    if len(code) == LAENGE + 3 and code[:3] in {"ENT", "PRE", "ADM"}:
        code = code[3:]
    return code if len(code) == LAENGE and all(z in ZEICHEN for z in code) else ""


def anzeigen(code: str, art: str = "entwickler") -> str:
    vorsatz = {"entwickler": "ENT", "premium": "PRE", "admin": "ADM"}.get(art, "ENT")
    return vorsatz + "-" + "-".join(code[i:i + 4] for i in range(0, LAENGE, 4))


def admin_kennung(passwort: str) -> str:
    return hashlib.sha256(f"jon-admin:{passwort}".encode()).hexdigest()[:16]


def admin_daten(passwort: str) -> dict:
    if len(passwort) < 12:
        raise ValueError("Der Admin-Code braucht mindestens 12 Zeichen.")
    salz = secrets.token_bytes(16)
    return {"salz": salz.hex(), "hash": hashlib.scrypt(passwort.encode(), salt=salz, n=2**14, r=8, p=1, dklen=32).hex(), "pk": admin_kennung(passwort)}


def befehl_ausfuehren(argumente: list[str], zeit: float = 30) -> tuple[int, str]:
    try:
        ergebnis = subprocess.run(argumente, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=zeit)
    except (OSError, subprocess.SubprocessError) as fehler:
        return 1, str(fehler)
    return ergebnis.returncode, (ergebnis.stdout + ergebnis.stderr).strip()


class Codeserver:
    def __init__(self, ordner: Path | None = None, uhr=time.time) -> None:
        self.ordner = Path(ordner or verzeichnis())
        self.uhr = uhr
        self.lock = threading.Lock()
        self.schluessel_lock = threading.Lock()
        self.fehler_ip: dict[str, deque] = {}
        self.fehler_alle: deque = deque()
        self.kostenlos_ip: dict[str, deque] = {}
        self._schluessel: Ed25519PrivateKey | None = None
        self.befehl = befehl_ausfuehren
        self.melden = self._telegram
        self.llm_transport: httpx.AsyncBaseTransport | None = None
        self.llm_schluessel = ""
        self.llm_basis = ""
        self._modelle: tuple[float, list[str]] = (0.0, [])

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
        temp = ziel.with_name(f"{ziel.name}.{os.getpid()}.{threading.get_ident()}.tmp")
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
        if not isinstance(inhalt, dict) or inhalt.get("stufe") not in ARTEN:
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
        return self.signieren({"stufe": "admin", "name": "Admin", "geraete": [geraet], "pk": pk, "quelle": "codes"})

    def _codes(self) -> dict:
        daten = self._lesen("codes.json", {})
        if not daten.get("pfeffer"):
            daten = {"pfeffer": secrets.token_hex(32), "codes": daten.get("codes", [])}
        daten.setdefault("codes", [])
        return daten

    @staticmethod
    def _hash(daten: dict, code: str) -> str:
        return hmac.new(bytes.fromhex(daten["pfeffer"]), code.encode(), hashlib.sha256).hexdigest()

    def code_token(self, eintrag: dict, geraet: str) -> str:
        art = eintrag.get("art", "entwickler")
        inhalt = {"stufe": art, "name": eintrag.get("name") or ARTEN[art], "geraete": [geraet], "code": eintrag["id"], "quelle": "codes"}
        ablauf = self._ablauf(eintrag, geraet)
        if ablauf:
            inhalt["exp"] = ablauf
        return self.signieren(inhalt)

    def entwickler_token(self, eintrag: dict, geraet: str) -> str:
        return self.code_token(eintrag, geraet)

    def _ablauf(self, eintrag: dict, geraet: str) -> int:
        tage = int(eintrag.get("tage") or 0)
        if eintrag.get("art", "entwickler") != "premium" or tage <= 0:
            return 0
        start = float(eintrag.get("aktiviert", {}).get(geraet) or self.uhr())
        return int(start + tage * TAG)

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
                    raise HTTPException(403, "Dieser Code wurde vom Admin gesperrt.")
                if eintrag:
                    if geraet not in eintrag["geraete"]:
                        if len(eintrag["geraete"]) >= int(eintrag.get("max_geraete", 3)):
                            raise HTTPException(403, f"Dieser Code ist schon auf {len(eintrag['geraete'])} Geräten aktiv. Bitte den Admin um einen neuen Code.")
                        eintrag["geraete"].append(geraet)
                        eintrag.setdefault("aktiviert", {})[geraet] = int(self.uhr())
                    ablauf = self._ablauf(eintrag, geraet)
                    if ablauf and ablauf < self.uhr():
                        raise HTTPException(403, "Dieser Premium-Code ist für dieses Gerät abgelaufen.")
                    eintrag["zuletzt"] = int(self.uhr())
                    self._json("codes.json", daten)
                    art = eintrag.get("art", "entwickler")
                    if art in TEAM:
                        self._melden_im_hintergrund(f"🔑 {ARTEN[art]}-Code „{eintrag.get('name') or eintrag['id']}“ wurde auf einem neuen Gerät eingelöst.")
                    return {"token": self.code_token(eintrag, geraet), "stufe": art}
        self._fehlversuch(ip)
        return None

    def _kostenlos(self) -> dict:
        daten = self._lesen("kostenlos.json", {})
        daten.setdefault("aktiv", True)
        daten.setdefault("geraete", {})
        return daten

    @staticmethod
    def kostenlos_kennung(geraet: str) -> str:
        return "frei-" + geraet[:12]

    def kostenlos_token(self, geraet: str) -> str:
        return self.signieren({"stufe": "premium", "name": KOSTENLOS_NAME, "geraete": [geraet], "code": self.kostenlos_kennung(geraet), "kostenlos": True, "quelle": "codes"})

    def kostenlos_aktiv(self) -> bool:
        return bool(self._kostenlos()["aktiv"])

    def kostenlos_holen(self, geraet: str, ip: str) -> dict:
        jetzt = self.uhr()
        with self.lock:
            daten = self._kostenlos()
            if not daten["aktiv"]:
                raise HTTPException(403, "Jon Premium gibt es gerade nicht mehr kostenlos.")
            eintrag = daten["geraete"].get(geraet)
            if eintrag is None:
                verlauf = self.kostenlos_ip.setdefault(ip, deque())
                while verlauf and jetzt - verlauf[0] > 3600:
                    verlauf.popleft()
                if len(verlauf) >= KOSTENLOS_PRO_IP:
                    raise HTTPException(429, "Von hier wurden gerade zu viele Geräte freigeschaltet. Bitte in einer Stunde noch einmal.")
                if len(daten["geraete"]) >= KOSTENLOS_MAX:
                    raise HTTPException(503, "Gerade können keine weiteren Geräte kostenlos freigeschaltet werden.")
                verlauf.append(jetzt)
                if len(self.kostenlos_ip) > 5000:
                    self.kostenlos_ip = {k: v for k, v in self.kostenlos_ip.items() if v and jetzt - v[-1] < 3600}
                eintrag = daten["geraete"][geraet] = {"seit": int(jetzt)}
            eintrag["zuletzt"] = int(jetzt)
            self._json("kostenlos.json", daten)
        return {"token": self.kostenlos_token(geraet), "stufe": "premium"}

    def kostenlos_stand(self) -> dict:
        daten = self._kostenlos()
        jetzt = self.uhr()
        geraete = daten["geraete"].values()
        return {"aktiv": bool(daten["aktiv"]), "geraete": len(daten["geraete"]), "aktiv_7_tage": sum(1 for g in geraete if jetzt - float(g.get("zuletzt") or 0) < 7 * TAG), "neu_7_tage": sum(1 for g in geraete if jetzt - float(g.get("seit") or 0) < 7 * TAG), "ausgeschaltet": int(daten.get("ausgeschaltet") or 0)}

    def kostenlos_setzen(self, aktiv: bool) -> dict:
        with self.lock:
            daten = self._kostenlos()
            if bool(daten["aktiv"]) != aktiv:
                daten["aktiv"] = aktiv
                if not aktiv:
                    daten["ausgeschaltet"] = int(self.uhr())
                self._json("kostenlos.json", daten)
        return self.kostenlos_stand()

    def person(self, token: str, geraet: str) -> dict:
        inhalt = self.lesen(token)
        if geraet not in inhalt.get("geraete", []):
            raise HTTPException(403, "Diese Lizenz gehört zu einem anderen Gerät.")
        if inhalt.get("kostenlos"):
            daten = self._kostenlos()
            if not daten["aktiv"]:
                raise HTTPException(403, "Das kostenlose Jon Premium ist beendet. Jon läuft jetzt als Standard.")
            if geraet not in daten["geraete"]:
                raise HTTPException(403, "Dieses Gerät ist für das kostenlose Jon Premium nicht mehr freigeschaltet.")
            return {"rolle": "premium", "haupt": False, "id": self.kostenlos_kennung(geraet), "name": KOSTENLOS_NAME, "geraet": geraet, "kostenlos": True}
        if inhalt["stufe"] == "admin" and inhalt.get("pk"):
            if inhalt["pk"] != self.admin().get("pk"):
                raise HTTPException(403, "Der Admin-Code wurde geändert. Melde dich mit dem neuen Admin-Code an.")
            return {"rolle": "admin", "haupt": True, "id": "admin", "name": "Admin", "geraet": geraet}
        eintrag = next((c for c in self._codes()["codes"] if c["id"] == inhalt.get("code")), None)
        if not eintrag or eintrag.get("gesperrt"):
            raise HTTPException(403, "Dieser Code wurde vom Admin gesperrt.")
        if geraet not in eintrag["geraete"]:
            raise HTTPException(403, "Dieses Gerät ist für den Code nicht mehr freigeschaltet.")
        ablauf = self._ablauf(eintrag, geraet)
        if ablauf and ablauf < self.uhr():
            raise HTTPException(403, "Dieser Premium-Code ist abgelaufen.")
        art = eintrag.get("art", "entwickler")
        return {"rolle": art, "haupt": False, "id": eintrag["id"], "name": eintrag.get("name") or ARTEN[art], "geraet": geraet}

    def erneuern(self, token: str, geraet: str, bericht: dict | None = None) -> dict:
        person = self.person(token, geraet)
        if bericht:
            self._bericht(person, bericht)
        with self.lock:
            if person["haupt"]:
                neu = self.admin_token(geraet)
            elif person.get("kostenlos"):
                daten = self._kostenlos()
                daten["geraete"].setdefault(geraet, {"seit": int(self.uhr())})["zuletzt"] = int(self.uhr())
                self._json("kostenlos.json", daten)
                neu = self.kostenlos_token(geraet)
            else:
                daten = self._codes()
                eintrag = next(c for c in daten["codes"] if c["id"] == person["id"])
                eintrag["zuletzt"] = int(self.uhr())
                if bericht:
                    eintrag.setdefault("info", {})[geraet] = {"version": str(bericht.get("version", ""))[:20], "system": str(bericht.get("system", ""))[:80], "zuletzt": int(self.uhr())}
                self._json("codes.json", daten)
                neu = self.code_token(eintrag, geraet)
        antwort = {"token": neu}
        if person["rolle"] in TEAM:
            antwort.update(flags=self.flags_fuer(person), ungelesen=self.ungelesen(person), rolle=person["rolle"], haupt=person["haupt"])
        return antwort

    def admin_pruefen(self, token: str, geraet: str) -> dict:
        try:
            person = self.person(token, geraet)
        except HTTPException as fehler:
            raise HTTPException(403, "Nur ein Admin kann das. " + str(fehler.detail))
        if person["rolle"] != "admin":
            raise HTTPException(403, "Nur ein Admin kann das.")
        return person

    def team_pruefen(self, token: str, geraet: str, flag: str = "") -> dict:
        person = self.person(token, geraet)
        if person["rolle"] not in TEAM:
            raise HTTPException(403, "Das gibt es nur für Entwickler und Admins.")
        if flag and not self.flags_fuer(person).get(flag):
            raise HTTPException(403, f"„{FLAGS[flag][0]}“ hat der Admin für dich ausgeschaltet.")
        return person

    def liste(self) -> list[dict]:
        daten = self._codes()
        ausgabe = []
        for c in sorted(daten["codes"], key=lambda c: c.get("erstellt", 0), reverse=True):
            info = c.get("info", {})
            geraete = [{"geraet": g, "kurz": g[:6], "seit": c.get("aktiviert", {}).get(g, 0), **info.get(g, {}), "ablauf": self._ablauf(c, g)} for g in c.get("geraete", [])]
            ausgabe.append({"id": c["id"], "name": c.get("name", ""), "art": c.get("art", "entwickler"), "tage": int(c.get("tage") or 0), "erstellt": c.get("erstellt", 0), "zuletzt": c.get("zuletzt", 0), "geraete": len(geraete), "geraete_liste": geraete, "max_geraete": int(c.get("max_geraete", 3)), "gesperrt": bool(c.get("gesperrt")), "ende": c.get("ende", "")})
        return ausgabe

    def erstellen(self, name: str, max_geraete: int, art: str = "entwickler", tage: int = 0) -> dict:
        if art not in ARTEN:
            raise HTTPException(400, "Unbekannte Code-Art.")
        code = "".join(secrets.choice(ZEICHEN) for _ in range(LAENGE))
        with self.lock:
            daten = self._codes()
            if len(daten["codes"]) >= MAX_CODES:
                raise HTTPException(409, f"Es gibt schon {MAX_CODES} Codes. Sperre alte Codes, bevor du neue erzeugst.")
            eintrag = {"id": secrets.token_hex(6), "name": name.strip()[:60], "art": art, "tage": max(0, int(tage)) if art == "premium" else 0, "hash": self._hash(daten, code), "ende": code[-4:], "erstellt": int(self.uhr()), "zuletzt": 0, "max_geraete": max_geraete, "geraete": [], "aktiviert": {}, "gesperrt": False}
            daten["codes"].append(eintrag)
            self._json("codes.json", daten)
        return {"code": anzeigen(code, art), "codes": self.liste()}

    def bearbeiten(self, kennung: str, werte: dict) -> dict:
        with self.lock:
            daten = self._codes()
            eintrag = next((c for c in daten["codes"] if c["id"] == kennung), None)
            if not eintrag:
                raise HTTPException(404, "Diesen Code gibt es nicht.")
            if werte.get("name") is not None:
                eintrag["name"] = str(werte["name"]).strip()[:60]
            if werte.get("max_geraete") is not None:
                eintrag["max_geraete"] = max(1, min(50, int(werte["max_geraete"])))
            if werte.get("art") is not None:
                if werte["art"] not in ARTEN:
                    raise HTTPException(400, "Unbekannte Code-Art.")
                eintrag["art"] = werte["art"]
            if werte.get("tage") is not None:
                eintrag["tage"] = max(0, int(werte["tage"]))
            if eintrag.get("art") != "premium":
                eintrag["tage"] = 0
            self._json("codes.json", daten)
        return {"codes": self.liste()}

    def geraet_entfernen(self, kennung: str, geraet: str) -> dict:
        with self.lock:
            daten = self._codes()
            eintrag = next((c for c in daten["codes"] if c["id"] == kennung), None)
            if not eintrag:
                raise HTTPException(404, "Diesen Code gibt es nicht.")
            eintrag["geraete"] = [g for g in eintrag.get("geraete", []) if g != geraet]
            eintrag.get("aktiviert", {}).pop(geraet, None)
            eintrag.get("info", {}).pop(geraet, None)
            self._json("codes.json", daten)
        return {"codes": self.liste()}

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

    def flags(self) -> dict:
        gespeichert = self._lesen("flags.json", {}).get("flags", {})
        ausgabe = {}
        for schluessel, wert in gespeichert.items():
            ausgabe[schluessel] = {"name": wert.get("name", schluessel), "beschreibung": wert.get("beschreibung", ""), "an": bool(wert.get("an", True)), "fuer": wert.get("fuer", "alle"), "codes": list(wert.get("codes", [])), "eigen": schluessel not in FLAGS}
        for schluessel, (name, text) in FLAGS.items():
            ausgabe.setdefault(schluessel, {"name": name, "beschreibung": text, "an": True, "fuer": "alle", "codes": [], "eigen": False})
            ausgabe[schluessel].update(name=name, beschreibung=text)
        return ausgabe

    def flags_fuer(self, person: dict) -> dict:
        alle = self.flags()
        if person["rolle"] == "admin":
            return {k: True for k in alle}
        if person["rolle"] != "entwickler":
            return {}
        return {k: f["an"] and (f["fuer"] == "alle" or person["id"] in f["codes"]) for k, f in alle.items()}

    def flags_setzen(self, schluessel: str, werte: dict) -> dict:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,30}", schluessel):
            raise HTTPException(400, "Der Schlüssel darf nur Kleinbuchstaben, Ziffern und _ enthalten.")
        with self.lock:
            daten = self._lesen("flags.json", {})
            alle = daten.setdefault("flags", {})
            if werte.get("loeschen"):
                if schluessel in FLAGS:
                    raise HTTPException(400, "Eingebaute Schalter kann man nur ausschalten, nicht löschen.")
                alle.pop(schluessel, None)
            else:
                eintrag = alle.setdefault(schluessel, {"an": True, "fuer": "alle", "codes": []})
                for feld in ("name", "beschreibung"):
                    if werte.get(feld) is not None and schluessel not in FLAGS:
                        eintrag[feld] = str(werte[feld]).strip()[:80 if feld == "name" else 200]
                if werte.get("an") is not None:
                    eintrag["an"] = bool(werte["an"])
                if werte.get("fuer") in {"alle", "auswahl"}:
                    eintrag["fuer"] = werte["fuer"]
                if isinstance(werte.get("codes"), list):
                    eintrag["codes"] = [c for c in werte["codes"] if isinstance(c, str) and re.fullmatch(KENNUNG, c)][:200]
            self._json("flags.json", daten)
        return {"flags": self.flags()}

    def _bericht(self, person: dict, bericht: dict) -> None:
        nutzung = bericht.get("nutzung") if isinstance(bericht.get("nutzung"), dict) else {}
        sauber = {"anfragen": int(nutzung.get("anfragen") or 0), "fehler": int(nutzung.get("fehler") or 0), "tokens": int(nutzung.get("tokens") or 0)}
        for feld in ("modelle", "werkzeuge", "anbieter"):
            werte = nutzung.get(feld) if isinstance(nutzung.get(feld), dict) else {}
            sauber[feld] = {str(k)[:60]: int(v) for k, v in list(werte.items())[:40] if isinstance(v, (int, float))}
        with self.lock:
            daten = self._lesen("statistik.json", {})
            geraete = daten.setdefault("geraete", {})
            geraete[person["geraet"]] = {"name": person["name"], "rolle": person["rolle"], "code": person["id"], "version": str(bericht.get("version", ""))[:20], "system": str(bericht.get("system", ""))[:80], "zuletzt": int(self.uhr()), "nutzung": sauber}
            self._json("statistik.json", daten)

    def statistik(self) -> dict:
        daten = self._lesen("statistik.json", {}).get("geraete", {})
        llm = self._llm()
        summen: dict[str, Counter] = {"modelle": Counter(), "werkzeuge": Counter(), "anbieter": Counter()}
        anfragen = tokens = fehler = 0
        geraete = []
        for geraet, eintrag in daten.items():
            nutzung = eintrag.get("nutzung", {})
            anfragen += int(nutzung.get("anfragen") or 0)
            tokens += int(nutzung.get("tokens") or 0)
            fehler += int(nutzung.get("fehler") or 0)
            for feld in summen:
                summen[feld].update(nutzung.get(feld, {}))
            geraete.append({"geraet": geraet, "kurz": geraet[:6], **{k: v for k, v in eintrag.items() if k != "nutzung"}, "anfragen": int(nutzung.get("anfragen") or 0), "tokens": int(nutzung.get("tokens") or 0), "felworks_heute": int(llm["verbrauch"].get(geraet, 0)) if llm["datum"] == date.today().isoformat() else 0})
        geraete.sort(key=lambda g: g.get("zuletzt", 0), reverse=True)
        return {"geraete": geraete, "summe": {"geraete": len(geraete), "anfragen": anfragen, "tokens": tokens, "fehler": fehler, **{feld: summen[feld].most_common(10) for feld in summen}}, "felworks": {"kontingent": int(llm["kontingent"]), "heute": sum(llm["verbrauch"].values()) if llm["datum"] == date.today().isoformat() else 0, "gesamt": int(llm.get("gesamt", 0))}}

    def _team(self) -> dict:
        daten = self._lesen("team.json", {})
        daten.setdefault("nachrichten", [])
        return daten

    @staticmethod
    def _sichtbar(person: dict, nachricht: dict) -> bool:
        if person["rolle"] == "admin":
            return True
        return nachricht["von"]["id"] == person["id"] or nachricht.get("an") in {"team", person["id"]}

    def ungelesen(self, person: dict) -> int:
        return sum(1 for n in self._team()["nachrichten"] if self._sichtbar(person, n) and n["von"]["id"] != person["id"] and person["id"] not in n.get("gelesen", []))

    def team_liste(self, person: dict) -> dict:
        nachrichten = []
        for n in self._team()["nachrichten"]:
            if not self._sichtbar(person, n):
                continue
            eintrag = {k: v for k, v in n.items() if k not in {"anhang", "gelesen", "stimmen"}}
            anhang = n.get("anhang") or {}
            eintrag["anhang"] = {"system": anhang.get("system", ""), "log": anhang.get("log", ""), "bild": bool(anhang.get("bild"))} if anhang else None
            eintrag["stimmen"] = len(n.get("stimmen", []))
            eintrag["meine_stimme"] = person["id"] in n.get("stimmen", [])
            eintrag["gelesen"] = n["von"]["id"] == person["id"] or person["id"] in n.get("gelesen", [])
            eintrag["von_mir"] = n["von"]["id"] == person["id"]
            nachrichten.append(eintrag)
        mitglieder = [{"id": c["id"], "name": c.get("name") or ARTEN[c.get("art", "entwickler")], "rolle": c.get("art", "entwickler")} for c in self._codes()["codes"] if c.get("art", "entwickler") in TEAM and not c.get("gesperrt")]
        return {"nachrichten": nachrichten[-500:], "ungelesen": self.ungelesen(person), "ich": {k: person[k] for k in ("id", "name", "rolle", "haupt")}, "mitglieder": mitglieder if person["rolle"] == "admin" else [], "status": IDEE_STATUS}

    def team_senden(self, person: dict, art: str, text: str, an: str = "admin", antwort_auf: str = "", anhang: dict | None = None) -> dict:
        if art not in NACHRICHTEN:
            raise HTTPException(400, "Unbekannte Nachrichtenart.")
        if art == "rundschreiben" and person["rolle"] != "admin":
            raise HTTPException(403, "Rundschreiben kann nur der Admin senden.")
        if person["rolle"] != "admin" and an not in {"admin", "team"}:
            raise HTTPException(403, "Entwickler schreiben an den Admin oder ans ganze Team.")
        if art == "rundschreiben":
            an = "team"
        sauber = None
        if anhang:
            bild = str(anhang.get("bild") or "")
            if bild and (not bild.startswith("data:image/") or len(bild) > MAX_BILD):
                raise HTTPException(413, "Das Bild ist zu groß.")
            sauber = {"system": str(anhang.get("system", ""))[:2000], "log": str(anhang.get("log", ""))[:30000], "bild": bild}
        with self.lock:
            daten = self._team()
            if antwort_auf and not any(n["id"] == antwort_auf for n in daten["nachrichten"]):
                raise HTTPException(404, "Diese Nachricht gibt es nicht mehr.")
            nachricht = {"id": secrets.token_hex(6), "zeit": int(self.uhr()), "von": {"id": person["id"], "name": person["name"], "rolle": person["rolle"]}, "an": an, "art": art, "text": text.strip()[:8000], "antwort_auf": antwort_auf, "gelesen": [], "stimmen": []}
            if art == "idee":
                nachricht["status"] = "neu"
            if sauber:
                nachricht["anhang"] = sauber
            daten["nachrichten"].append(nachricht)
            daten["nachrichten"] = daten["nachrichten"][-MAX_NACHRICHTEN:]
            self._json("team.json", daten)
        if person["rolle"] != "admin":
            symbol = {"idee": "💡", "fehler": "🐞", "nachricht": "✉️"}.get(art, "✉️")
            self._melden_im_hintergrund(f"{symbol} Jon-Team · {person['name']}: {text.strip()[:600]}")
        return self.team_liste(person)

    def team_gelesen(self, person: dict) -> dict:
        with self.lock:
            daten = self._team()
            for n in daten["nachrichten"]:
                if self._sichtbar(person, n) and person["id"] not in n.setdefault("gelesen", []):
                    n["gelesen"].append(person["id"])
            self._json("team.json", daten)
        return {"ungelesen": 0}

    def team_anhang(self, person: dict, kennung: str) -> dict:
        nachricht = next((n for n in self._team()["nachrichten"] if n["id"] == kennung and self._sichtbar(person, n)), None)
        if not nachricht or not (nachricht.get("anhang") or {}).get("bild"):
            raise HTTPException(404, "Kein Bild vorhanden.")
        return {"bild": nachricht["anhang"]["bild"]}

    def team_stimme(self, person: dict, kennung: str) -> dict:
        with self.lock:
            daten = self._team()
            nachricht = next((n for n in daten["nachrichten"] if n["id"] == kennung and self._sichtbar(person, n)), None)
            if not nachricht or nachricht.get("art") != "idee":
                raise HTTPException(404, "Diese Idee gibt es nicht.")
            stimmen = nachricht.setdefault("stimmen", [])
            if person["id"] in stimmen:
                stimmen.remove(person["id"])
            else:
                stimmen.append(person["id"])
            self._json("team.json", daten)
        return self.team_liste(person)

    def team_status(self, person: dict, kennung: str, status: str) -> dict:
        if status not in IDEE_STATUS:
            raise HTTPException(400, "Unbekannter Status.")
        with self.lock:
            daten = self._team()
            nachricht = next((n for n in daten["nachrichten"] if n["id"] == kennung), None)
            if not nachricht or nachricht.get("art") != "idee":
                raise HTTPException(404, "Diese Idee gibt es nicht.")
            nachricht["status"] = status
            self._json("team.json", daten)
        return self.team_liste(person)

    def team_loeschen(self, person: dict, kennung: str) -> dict:
        with self.lock:
            daten = self._team()
            nachricht = next((n for n in daten["nachrichten"] if n["id"] == kennung), None)
            if not nachricht or (person["rolle"] != "admin" and nachricht["von"]["id"] != person["id"]):
                raise HTTPException(404, "Diese Nachricht kannst du nicht entfernen.")
            daten["nachrichten"] = [n for n in daten["nachrichten"] if n["id"] != kennung]
            self._json("team.json", daten)
        return self.team_liste(person)

    def _skills(self) -> dict:
        daten = self._lesen("skills.json", {})
        daten.setdefault("skills", [])
        return daten

    def skills_liste(self) -> dict:
        return {"skills": [{k: v for k, v in s.items() if k != "inhalt"} | {"zeichen": len(s.get("inhalt", ""))} for s in sorted(self._skills()["skills"], key=lambda s: s.get("zeit", 0), reverse=True)]}

    def skills_teilen(self, person: dict, name: str, titel: str, beschreibung: str, inhalt: str) -> dict:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,48}", name):
            raise HTTPException(400, "Der Skill-Name darf nur Kleinbuchstaben, Ziffern, - und _ enthalten.")
        if not inhalt.strip() or len(inhalt) > MAX_SKILL:
            raise HTTPException(400, "Der Skill ist leer oder größer als 100.000 Zeichen.")
        with self.lock:
            daten = self._skills()
            alt = next((s for s in daten["skills"] if s["name"] == name), None)
            if alt and alt["autor"]["id"] != person["id"] and person["rolle"] != "admin":
                raise HTTPException(409, "Einen Skill mit diesem Namen hat schon jemand anderes geteilt.")
            eintrag = {"id": alt["id"] if alt else secrets.token_hex(6), "name": name, "titel": titel.strip()[:80] or name, "beschreibung": beschreibung.strip()[:300], "inhalt": inhalt, "autor": {"id": person["id"], "name": person["name"]}, "zeit": int(self.uhr()), "downloads": alt.get("downloads", 0) if alt else 0}
            daten["skills"] = [s for s in daten["skills"] if s["name"] != name] + [eintrag]
            self._json("skills.json", daten)
        self._melden_im_hintergrund(f"📚 {person['name']} hat den Skill „{eintrag['titel']}“ geteilt.")
        return self.skills_liste()

    def skills_holen(self, kennung: str) -> dict:
        with self.lock:
            daten = self._skills()
            eintrag = next((s for s in daten["skills"] if s["id"] == kennung), None)
            if not eintrag:
                raise HTTPException(404, "Diesen Skill gibt es nicht.")
            eintrag["downloads"] = int(eintrag.get("downloads", 0)) + 1
            self._json("skills.json", daten)
        return dict(eintrag)

    def skills_entfernen(self, person: dict, kennung: str) -> dict:
        with self.lock:
            daten = self._skills()
            eintrag = next((s for s in daten["skills"] if s["id"] == kennung), None)
            if not eintrag or (person["rolle"] != "admin" and eintrag["autor"]["id"] != person["id"]):
                raise HTTPException(404, "Diesen Skill kannst du nicht entfernen.")
            daten["skills"] = [s for s in daten["skills"] if s["id"] != kennung]
            self._json("skills.json", daten)
        return self.skills_liste()

    def _llm(self) -> dict:
        daten = self._lesen("llm.json", {})
        daten.setdefault("kontingent", KONTINGENT)
        daten.setdefault("datum", "")
        daten.setdefault("verbrauch", {})
        daten.setdefault("gesamt", 0)
        return daten

    def llm_kontingent(self, wert: int) -> dict:
        with self.lock:
            daten = self._llm()
            daten["kontingent"] = max(0, min(100000, int(wert)))
            self._json("llm.json", daten)
        return self.statistik()["felworks"]

    def llm_person(self, kopf: str) -> dict:
        token = kopf[7:].strip() if kopf.lower().startswith("bearer ") else ""
        if not token:
            raise HTTPException(401, "Für den FelWorks-Modellzugang fehlt die Lizenz.")
        inhalt = self.lesen(token)
        geraete = inhalt.get("geraete") or [""]
        return self.team_pruefen(token, geraete[0], "modell")

    def llm_verbrauchen(self, person: dict) -> dict:
        heute = date.today().isoformat()
        with self.lock:
            daten = self._llm()
            if daten["datum"] != heute:
                daten.update(datum=heute, verbrauch={})
            schon = int(daten["verbrauch"].get(person["geraet"], 0))
            if person["rolle"] != "admin" and schon >= int(daten["kontingent"]):
                raise HTTPException(429, f"Dein Tageskontingent von {daten['kontingent']} Anfragen über FelWorks ist aufgebraucht. Morgen geht es weiter, oder frag den Admin.")
            daten["verbrauch"][person["geraet"]] = schon + 1
            daten["gesamt"] = int(daten.get("gesamt", 0)) + 1
            self._json("llm.json", daten)
            return {"heute": schon + 1, "kontingent": int(daten["kontingent"])}

    def llm_zugang(self) -> tuple[str, str]:
        if self.llm_schluessel and self.llm_basis:
            return self.llm_schluessel, self.llm_basis
        from app.core.config import get_settings
        from app.core.keys import KeyManager

        settings = get_settings()
        schluessel = KeyManager(settings).key_for("nvidia", "jon") or ""
        if not schluessel:
            raise HTTPException(503, "Auf dem Pi ist kein NVIDIA-Schlüssel eingerichtet.")
        return schluessel, settings.nvidia_base_url.rstrip("/")

    async def llm_modelle(self) -> list[str]:
        if self._modelle[1] and self.uhr() - self._modelle[0] < 600:
            return self._modelle[1]
        schluessel, basis = self.llm_zugang()
        try:
            async with httpx.AsyncClient(timeout=10, transport=self.llm_transport) as client:
                antwort = await client.get(f"{basis}/models", headers={"Authorization": f"Bearer {schluessel}"})
            vorhanden = {m.get("id") for m in antwort.json().get("data", []) if isinstance(m, dict)}
            liste = [m for m in MODELLE if m in vorhanden] or MODELLE
        except (httpx.HTTPError, ValueError, AttributeError):
            liste = MODELLE
        self._modelle = (self.uhr(), liste)
        return liste

    def _jon_aufruf(self, pfad: str, daten: dict) -> bool:
        try:
            from app.core.config import DATA_DIR

            token = (DATA_DIR / "access.token").read_text(encoding="utf-8").strip()
            antwort = httpx.post(f"http://127.0.0.1:8756/api{pfad}", json=daten, headers={"X-Jon-Token": token}, timeout=15)
            return antwort.status_code < 400
        except Exception:
            return False

    def _telegram(self, text: str) -> bool:
        return self._jon_aufruf("/system/telegram/melden", {"text": text[:3500]})

    def _melden_im_hintergrund(self, text: str) -> None:
        threading.Thread(target=self.melden, args=(text,), daemon=True).start()

    def pi_status(self) -> dict:
        dienste = {}
        for name in DIENSTE:
            argumente = ["systemctl", "is-active", "jon.service"] if name == "jon" else ["systemctl", "--user", "is-active", name]
            code, ausgabe = self.befehl(argumente, 10)
            dienste[name] = (ausgabe.splitlines() or ["unbekannt"])[-1] if ausgabe else ("active" if code == 0 else "unbekannt")
        _, git = self.befehl(["git", "-C", str(WURZEL), "log", "-1", "--format=%h %s"], 10)
        _, funnel = self.befehl(["tailscale", "funnel", "status"], 10)
        _, laufzeit = self.befehl(["uptime", "-p"], 5)
        try:
            platte = shutil.disk_usage(str(WURZEL))
            speicher_platte = {"frei_gb": round(platte.free / 1e9, 1), "gesamt_gb": round(platte.total / 1e9, 1)}
        except OSError:
            speicher_platte = {}
        try:
            werte = dict(zeile.split(":", 1) for zeile in Path("/proc/meminfo").read_text().splitlines() if ":" in zeile)
            ram = {"frei_mb": int(werte["MemAvailable"].split()[0]) // 1024, "gesamt_mb": int(werte["MemTotal"].split()[0]) // 1024}
        except (OSError, KeyError, ValueError):
            ram = {}
        try:
            temperatur = round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000, 1)
        except (OSError, ValueError):
            temperatur = None
        try:
            version = re.search(r'app_version: str = "([^"]+)"', (WURZEL / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")).group(1)
        except (OSError, AttributeError):
            version = ""
        return {"dienste": dienste, "version": version, "git": git[:200], "funnel": funnel[:1500], "laufzeit": laufzeit[:80], "platte": speicher_platte, "ram": ram, "temperatur": temperatur, "zeit": int(self.uhr())}

    def pi_neustart(self, dienst: str) -> dict:
        if dienst not in DIENSTE:
            raise HTTPException(400, "Unbekannter Dienst.")
        if dienst == "jon":
            code, pid = self.befehl(["systemctl", "show", "jon.service", "-p", "MainPID", "--value"], 10)
            try:
                os.kill(int(pid.strip()), signal.SIGTERM)
            except (ValueError, OSError) as fehler:
                raise HTTPException(500, f"Jon konnte nicht neu gestartet werden: {fehler}")
            return {"ok": True, "text": "Jon startet neu. Das dauert etwa eine halbe Minute."}
        if dienst == "jon-codes":
            threading.Timer(1.0, lambda: self.befehl(["systemctl", "--user", "restart", "jon-codes"], 30)).start()
            return {"ok": True, "text": "Der Codeserver startet in einer Sekunde neu."}
        code, ausgabe = self.befehl(["systemctl", "--user", "restart", dienst], 60)
        if code != 0:
            raise HTTPException(500, f"Neustart fehlgeschlagen: {ausgabe[-300:]}")
        return {"ok": True, "text": f"{dienst} wurde neu gestartet."}

    def pi_log(self, dienst: str) -> dict:
        if dienst not in DIENSTE:
            raise HTTPException(400, "Unbekannter Dienst.")
        if dienst == "jon":
            try:
                from app.core.config import DATA_DIR

                zeilen = (DATA_DIR / "jon.log").read_text(encoding="utf-8", errors="replace").splitlines()[-150:]
                return {"log": "\n".join(zeilen)}
            except OSError:
                _, ausgabe = self.befehl(["journalctl", "-u", "jon.service", "-n", "150", "--no-pager"], 15)
                return {"log": ausgabe}
        _, ausgabe = self.befehl(["journalctl", "--user", "-u", dienst, "-n", "150", "--no-pager"], 15)
        return {"log": ausgabe or "Für diesen Dienst gibt es kein Protokoll."}

    def pi_aktualisieren(self) -> dict:
        code, ausgabe = self.befehl(["git", "-C", str(WURZEL), "pull", "--ff-only"], 180)
        if code != 0:
            raise HTTPException(500, f"git pull fehlgeschlagen: {ausgabe[-500:]}")
        code_pip, pip = self.befehl([str(WURZEL / "backend" / ".venv" / "bin" / "python"), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(WURZEL / "backend" / "requirements-pi.txt")], 900)
        return {"ok": True, "text": ausgabe[-800:] + ("" if code_pip == 0 else "\nBibliotheken: " + pip[-300:]), "hinweis": "Starte danach Jon, Demo und Codeserver neu, damit der neue Stand läuft."}


class Einloesen(BaseModel):
    code: str = Field(min_length=1, max_length=400)
    geraet: str = Field(pattern=GERAET)


class Lizenz(BaseModel):
    token: str = Field(min_length=20, max_length=4000)
    geraet: str = Field(pattern=GERAET)


class Erneuern(Lizenz):
    bericht: dict | None = None


class Neu(Lizenz):
    name: str = Field(default="", max_length=60)
    geraete: int = Field(default=3, ge=1, le=50)
    art: str = Field(default="entwickler", pattern="^(entwickler|premium|admin)$")
    tage: int = Field(default=0, ge=0, le=3650)


class Bearbeiten(Lizenz):
    id: str = Field(pattern=KENNUNG)
    name: str | None = Field(default=None, max_length=60)
    max_geraete: int | None = Field(default=None, ge=1, le=50)
    art: str | None = Field(default=None, pattern="^(entwickler|premium|admin)$")
    tage: int | None = Field(default=None, ge=0, le=3650)


class GeraetEntfernen(Lizenz):
    id: str = Field(pattern=KENNUNG)
    entfernen: str = Field(pattern=GERAET)


class Sperren(Lizenz):
    id: str = Field(pattern=KENNUNG)
    gesperrt: bool = True


class Kennung(Lizenz):
    id: str = Field(pattern=KENNUNG)


class Senden(Lizenz):
    art: str = Field(default="nachricht", pattern="^(idee|fehler|nachricht|rundschreiben)$")
    text: str = Field(min_length=1, max_length=8000)
    an: str = Field(default="admin", pattern="^(admin|team|[a-f0-9]{12})$")
    antwort_auf: str = Field(default="", pattern="^$|^[a-f0-9]{12}$")
    anhang: dict | None = None


class Status(Kennung):
    status: str = Field(pattern="^(neu|geplant|in_arbeit|fertig|abgelehnt)$")


class Flag(Lizenz):
    schluessel: str = Field(min_length=2, max_length=31)
    name: str | None = Field(default=None, max_length=80)
    beschreibung: str | None = Field(default=None, max_length=200)
    an: bool | None = None
    fuer: str | None = Field(default=None, pattern="^(alle|auswahl)$")
    codes: list[str] | None = None
    loeschen: bool = False


class Kontingent(Lizenz):
    wert: int = Field(ge=0, le=100000)


class Geraet(BaseModel):
    geraet: str = Field(pattern=GERAET)


class Kostenlos(Lizenz):
    aktiv: bool


class Dienst(Lizenz):
    dienst: str = Field(pattern="^(jon|jon-codes|jon-demo)$")


class Skill(Lizenz):
    name: str = Field(min_length=1, max_length=49)
    titel: str = Field(default="", max_length=80)
    beschreibung: str = Field(default="", max_length=300)
    inhalt: str = Field(min_length=1, max_length=MAX_SKILL)


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
        return {"ok": True, "oeffentlich": dienst.oeffentlich(), "admin": bool(dienst.admin().get("hash")), "kostenlos": dienst.kostenlos_aktiv()}

    @app.post("/codes/kostenlos")
    async def kostenlos(daten: Geraet, request: Request) -> dict:
        return dienst.kostenlos_holen(daten.geraet, adresse(request))

    @app.post("/codes/kostenlos/verfuegbar")
    async def kostenlos_verfuegbar() -> dict:
        return {"verfuegbar": dienst.kostenlos_aktiv()}

    @app.post("/codes/kostenlos/stand")
    async def kostenlos_stand(daten: Lizenz) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.kostenlos_stand()

    @app.post("/codes/kostenlos/setzen")
    async def kostenlos_setzen(daten: Kostenlos) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.kostenlos_setzen(daten.aktiv)

    @app.post("/codes/einloesen")
    async def einloesen(daten: Einloesen, request: Request) -> dict:
        ergebnis = await asyncio.to_thread(dienst.einloesen, daten.code, daten.geraet, adresse(request))
        if ergebnis is None:
            await asyncio.sleep(pause)
            raise HTTPException(403, "Dieser Code ist ungültig.")
        return ergebnis

    @app.post("/codes/erneuern")
    async def erneuern(daten: Erneuern) -> dict:
        return dienst.erneuern(daten.token, daten.geraet, daten.bericht)

    @app.post("/codes/liste")
    async def liste(daten: Lizenz) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return {"codes": dienst.liste()}

    @app.post("/codes/erstellen")
    async def neu(daten: Neu) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.erstellen(daten.name, daten.geraete, daten.art, daten.tage)

    @app.post("/codes/bearbeiten")
    async def bearbeiten(daten: Bearbeiten) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.bearbeiten(daten.id, {"name": daten.name, "max_geraete": daten.max_geraete, "art": daten.art, "tage": daten.tage})

    @app.post("/codes/geraet-entfernen")
    async def geraet_entfernen(daten: GeraetEntfernen) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.geraet_entfernen(daten.id, daten.entfernen)

    @app.post("/codes/sperren")
    async def sperren(daten: Sperren) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.sperren(daten.id, daten.gesperrt)

    @app.post("/codes/team/liste")
    async def team_liste(daten: Lizenz) -> dict:
        return dienst.team_liste(dienst.team_pruefen(daten.token, daten.geraet))

    @app.post("/codes/team/ungelesen")
    async def team_ungelesen(daten: Lizenz) -> dict:
        return {"ungelesen": dienst.ungelesen(dienst.team_pruefen(daten.token, daten.geraet))}

    @app.post("/codes/team/senden")
    async def team_senden(daten: Senden) -> dict:
        person = dienst.team_pruefen(daten.token, daten.geraet, "fehlerbericht" if daten.anhang else "")
        return dienst.team_senden(person, daten.art, daten.text, daten.an, daten.antwort_auf, daten.anhang)

    @app.post("/codes/team/gelesen")
    async def team_gelesen(daten: Lizenz) -> dict:
        return dienst.team_gelesen(dienst.team_pruefen(daten.token, daten.geraet))

    @app.post("/codes/team/anhang")
    async def team_anhang(daten: Kennung) -> dict:
        return dienst.team_anhang(dienst.team_pruefen(daten.token, daten.geraet), daten.id)

    @app.post("/codes/team/stimme")
    async def team_stimme(daten: Kennung) -> dict:
        return dienst.team_stimme(dienst.team_pruefen(daten.token, daten.geraet), daten.id)

    @app.post("/codes/team/status")
    async def team_status(daten: Status) -> dict:
        return dienst.team_status(dienst.admin_pruefen(daten.token, daten.geraet), daten.id, daten.status)

    @app.post("/codes/team/loeschen")
    async def team_loeschen(daten: Kennung) -> dict:
        return dienst.team_loeschen(dienst.team_pruefen(daten.token, daten.geraet), daten.id)

    @app.post("/codes/flags/liste")
    async def flags_liste(daten: Lizenz) -> dict:
        person = dienst.team_pruefen(daten.token, daten.geraet)
        return {"flags": dienst.flags() if person["rolle"] == "admin" else {}, "meine": dienst.flags_fuer(person)}

    @app.post("/codes/flags/setzen")
    async def flags_setzen(daten: Flag) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.flags_setzen(daten.schluessel, {"name": daten.name, "beschreibung": daten.beschreibung, "an": daten.an, "fuer": daten.fuer, "codes": daten.codes, "loeschen": daten.loeschen})

    @app.post("/codes/statistik")
    async def statistik(daten: Lizenz) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.statistik()

    @app.post("/codes/llm/kontingent")
    async def llm_kontingent(daten: Kontingent) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return dienst.llm_kontingent(daten.wert)

    @app.post("/codes/pi/status")
    async def pi_status(daten: Lizenz) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return await asyncio.to_thread(dienst.pi_status)

    @app.post("/codes/pi/neustart")
    async def pi_neustart(daten: Dienst) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return await asyncio.to_thread(dienst.pi_neustart, daten.dienst)

    @app.post("/codes/pi/log")
    async def pi_log(daten: Dienst) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return await asyncio.to_thread(dienst.pi_log, daten.dienst)

    @app.post("/codes/pi/aktualisieren")
    async def pi_aktualisieren(daten: Lizenz) -> dict:
        dienst.admin_pruefen(daten.token, daten.geraet)
        return await asyncio.to_thread(dienst.pi_aktualisieren)

    @app.post("/codes/skills/liste")
    async def skills_liste(daten: Lizenz) -> dict:
        dienst.team_pruefen(daten.token, daten.geraet, "skills")
        return dienst.skills_liste()

    @app.post("/codes/skills/teilen")
    async def skills_teilen(daten: Skill) -> dict:
        person = dienst.team_pruefen(daten.token, daten.geraet, "skills")
        return dienst.skills_teilen(person, daten.name, daten.titel, daten.beschreibung, daten.inhalt)

    @app.post("/codes/skills/holen")
    async def skills_holen(daten: Kennung) -> dict:
        dienst.team_pruefen(daten.token, daten.geraet, "skills")
        return dienst.skills_holen(daten.id)

    @app.post("/codes/skills/entfernen")
    async def skills_entfernen(daten: Kennung) -> dict:
        return dienst.skills_entfernen(dienst.team_pruefen(daten.token, daten.geraet, "skills"), daten.id)

    @app.get("/codes/llm/v1/models")
    async def llm_modelle(request: Request) -> dict:
        dienst.llm_person(request.headers.get("authorization", ""))
        return {"object": "list", "data": [{"id": m, "object": "model", "owned_by": "felworks"} for m in await dienst.llm_modelle()]}

    @app.post("/codes/llm/v1/chat/completions")
    async def llm_chat(request: Request):
        person = dienst.llm_person(request.headers.get("authorization", ""))
        try:
            koerper = await request.json()
        except ValueError:
            raise HTTPException(400, "Ungültige Anfrage.")
        if not isinstance(koerper, dict) or not isinstance(koerper.get("messages"), list):
            raise HTTPException(400, "Ungültige Anfrage.")
        dienst.llm_verbrauchen(person)
        schluessel, basis = dienst.llm_zugang()
        kopf = {"Authorization": f"Bearer {schluessel}", "Content-Type": "application/json"}
        if koerper.get("stream"):
            client = httpx.AsyncClient(timeout=httpx.Timeout(300, connect=20), transport=dienst.llm_transport)
            antwort = await client.send(client.build_request("POST", f"{basis}/chat/completions", json=koerper, headers={**kopf, "Accept": "text/event-stream"}), stream=True)
            if antwort.status_code >= 400:
                inhalt = await antwort.aread()
                await antwort.aclose()
                await client.aclose()
                return Response(content=inhalt, status_code=antwort.status_code, media_type="application/json")

            async def weiter():
                try:
                    if antwort.is_stream_consumed:
                        yield antwort.content
                    else:
                        async for stueck in antwort.aiter_raw():
                            yield stueck
                finally:
                    await antwort.aclose()
                    await client.aclose()

            return StreamingResponse(weiter(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
        async with httpx.AsyncClient(timeout=300, transport=dienst.llm_transport) as client:
            antwort = await client.post(f"{basis}/chat/completions", json=koerper, headers=kopf)
        return Response(content=antwort.content, status_code=antwort.status_code, media_type="application/json")

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
