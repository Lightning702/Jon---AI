from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.config import DATA_DIR, get_settings
from app.core.store import atomic_write_text

OEFFENTLICH = "cJYQcvvuqg2j3a1Rnqyg+YdlBD6XIwhENSF4HKcpaQw="
CODE_OEFFENTLICH = "dkdz3y9XOspsQOQdubK5s2rqZ0L4+hkwqWzq1EuWuyQ="
VERSION = "JON1"
STUFEN = {"standard": "Standard", "premium": "Premium", "admin": "Admin", "entwickler": "Entwickler"}
UNBEGRENZT = {"premium", "admin", "entwickler"}
TEAM = {"admin", "entwickler"}
TEAM_AKTIONEN = {"liste", "erstellen", "bearbeiten", "geraet-entfernen", "sperren", "team/liste", "team/ungelesen", "team/senden", "team/gelesen", "team/anhang", "team/stimme", "team/status", "team/loeschen", "flags/liste", "flags/setzen", "statistik", "llm/kontingent", "pi/status", "pi/neustart", "pi/log", "pi/aktualisieren", "skills/liste", "skills/teilen", "skills/holen", "skills/entfernen", "kostenlos/stand", "kostenlos/setzen"}
GEHEIM_MUSTER = re.compile(r"(?:nvapi-|sk-|sk_live_|sk_test_|rk_live_|ghp_|gsk_|xai-|AIza)[A-Za-z0-9_\-]{8,}|Bearer\s+\S+|JON1\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
GEHEIM_FELD = re.compile(r"(?i)\b(token|key|passwort|password|secret|api_key|apikey)(\s*[=:]\s*)\S+")


def schwaerzen(text: str) -> str:
    return GEHEIM_FELD.sub(lambda m: m.group(1) + m.group(2) + "[entfernt]", GEHEIM_MUSTER.sub("[entfernt]", text or ""))
PLAENE = [{"key": "monat", "name": "Monatlich", "preis": "6,99 €", "zeitraum": "pro Monat"}, {"key": "jahr", "name": "Jährlich", "preis": "59,99 €", "zeitraum": "pro Jahr", "hinweis": "2 Monate geschenkt"}]
FEATURES = {
    "harness": ("Jon Harness Pro", "Unbegrenzte Aufträge, Projektvorschau und Fachagenten im Harness"),
    "fachteam": ("Fachteam", "Bis zu vier Fachagenten mit Gegenprüfung, so oft du willst"),
    "fernsteuerung": ("Fernsteuerung", "PC per Telegram steuern, Freigaben unterwegs"),
    "recherche": ("Deep Learning & Recherche", "Lange Recherche-Berichte und Lernpläne"),
    "studio": ("Studio", "Video, Foto und Präsentationen erstellen"),
    "stimmen": ("Stimmen & Transkripte", "Lange Audiodateien, Sprecher und Export"),
    "bildschirm": ("Bildschirmanalyse", "Jon sieht und prüft, was auf dem Bildschirm ist"),
    "browser": ("Browser-Agent", "Jon erledigt Aufgaben selbstständig im Browser"),
    "aussehen": ("MiniJon-Aussehen", "Alle zehn Auftritte und die 3D-Varianten"),
    "familie": ("Familienpaket", "Kinderschutz-Profile für die ganze Familie"),
    "sync": ("Cloud-Sync & Backup", "Gedächtnis und Einstellungen verschlüsselt sichern und auf jedes Gerät holen"),
    "automatik": ("Alltags-Automatisierung", "Inbox, Wochenbericht und wiederkehrende Abläufe"),
    "spiele": ("Alle Spiele", "Alle Spiele und Welten statt nur dem ersten"),
}
KONTINGENT = {"harness": 3, "fachteam": 1}
WERKZEUGE = {"team": "fachteam", "deep_learning": "recherche", "create_image": "studio", "create_pptx": "studio", "youtube_transkript": "stimmen", "understand_screen": "bildschirm", "recall_screen": "bildschirm", "ausloeser": "automatik"}
FREIE_SPIELE = {"blockwelt"}


def werkzeug_feature(name: str, args: dict | None = None) -> str:
    if name == "harness_task":
        return "harness" if (args or {}).get("action", "start") == "start" else ""
    if name.startswith("browser_"):
        return "browser"
    return WERKZEUGE.get(name, "")


def b64url(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode()


def b64url_lesen(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def lesen(token: str, oeffentlich: str = "") -> dict:
    teile = (token or "").strip().split(".")
    if len(teile) != 3 or teile[0] != VERSION:
        raise ValueError("Das ist kein gültiger Jon-Lizenzschlüssel.")
    for schluessel, stufen in ((oeffentlich or OEFFENTLICH, {"premium", "admin"}), (CODE_OEFFENTLICH, {"admin", "entwickler", "premium"})):
        if not schluessel:
            continue
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(schluessel)).verify(b64url_lesen(teile[2]), f"{teile[0]}.{teile[1]}".encode())
            daten = json.loads(b64url_lesen(teile[1]))
        except (InvalidSignature, ValueError, TypeError):
            continue
        if not isinstance(daten, dict) or daten.get("stufe") not in stufen:
            raise ValueError("Der Lizenzschlüssel enthält keine gültige Stufe.")
        return daten
    raise ValueError("Die Signatur des Lizenzschlüssels ist ungültig. Er wurde nicht von FelWorks ausgestellt oder verändert.")


def _maschine() -> str:
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as schluessel:
                return str(winreg.QueryValueEx(schluessel, "MachineGuid")[0])
        except OSError:
            return ""
    for pfad in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            wert = Path(pfad).read_text(encoding="utf-8").strip()
            if wert:
                return wert
        except OSError:
            continue
    if sys.platform == "darwin":
        try:
            ausgabe = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True, timeout=5).stdout
            for zeile in ausgabe.splitlines():
                if "IOPlatformUUID" in zeile:
                    return zeile.split("=")[-1].strip().strip('"')
        except (OSError, subprocess.SubprocessError):
            return ""
    return ""


class Abgelehnt(ValueError):
    pass


class PremiumNoetig(ValueError):
    def __init__(self, feature: str, text: str = "") -> None:
        name = FEATURES.get(feature, (feature, ""))[0]
        self.feature = feature
        self.text = text or f"{name} ist eine Premium-Funktion. Schalte Jon Premium frei, um sie zu nutzen."
        super().__init__(self.text)


class Premium:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory or DATA_DIR)
        self.datei = self.directory / "lizenz.json"
        self.nutzung_datei = self.directory / "premium_nutzung.json"
        self.zustand_datei = self.directory / "team_zustand.json"
        self.lock = threading.Lock()
        self._geraet = ""
        self._cache: tuple[str, dict] | None = None
        self.offen: dict = {}
        self._kostenlos: tuple[float, bool] = (0.0, False)

    def geraet(self) -> str:
        if self._geraet:
            return self._geraet
        roh = _maschine()
        if not roh:
            pfad = self.directory / "geraet.json"
            try:
                roh = json.loads(pfad.read_text(encoding="utf-8"))["id"]
            except (OSError, ValueError, KeyError, TypeError):
                roh = secrets.token_hex(16)
                pfad.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_text(pfad, json.dumps({"id": roh}))
        self._geraet = hashlib.sha256(f"jon-geraet:{roh}".encode()).hexdigest()[:20]
        return self._geraet

    def token(self) -> str:
        try:
            return str(json.loads(self.datei.read_text(encoding="utf-8")).get("token", ""))
        except (OSError, ValueError, AttributeError):
            return ""

    def speichern(self, token: str) -> dict:
        daten = lesen(token)
        if self.geraet() not in daten.get("geraete", []):
            raise ValueError("Dieser Lizenzschlüssel gilt nicht für dieses Gerät.")
        self.directory.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.datei, json.dumps({"token": token.strip(), "gespeichert": time.time()}))
        self._cache = None
        return self.status()

    def abmelden(self) -> dict:
        self.datei.unlink(missing_ok=True)
        self.zustand_datei.unlink(missing_ok=True)
        self._cache = None
        return self.status()

    def lizenz(self) -> dict:
        token = self.token()
        if not token:
            return {}
        if self._cache and self._cache[0] == token:
            return self._cache[1]
        try:
            daten = lesen(token)
        except ValueError as exc:
            daten = {"fehler": str(exc)}
        self._cache = (token, daten)
        return daten

    def stufe(self) -> str:
        daten = self.lizenz()
        if not daten or daten.get("fehler"):
            return "standard"
        if self.geraet() not in daten.get("geraete", []):
            return "standard"
        if daten.get("exp") and float(daten["exp"]) < time.time():
            return "standard"
        return daten["stufe"]

    def premium(self) -> bool:
        return self.stufe() in UNBEGRENZT

    def vom_codeserver(self) -> bool:
        daten = self.lizenz()
        return bool(daten) and not daten.get("fehler") and daten.get("quelle") == "codes"

    def im_team(self) -> bool:
        return self.stufe() in TEAM and self.vom_codeserver()

    def zustand(self) -> dict:
        try:
            wert = json.loads(self.zustand_datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            wert = {}
        return wert if isinstance(wert, dict) else {}

    def _zustand_setzen(self, **werte) -> dict:
        neu = {**self.zustand(), **werte}
        self.directory.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.zustand_datei, json.dumps(neu, ensure_ascii=False))
        return neu

    def flags(self) -> dict:
        if not self.im_team():
            return {}
        zustand = self.zustand()
        gespeichert = zustand["flags"] if isinstance(zustand.get("flags"), dict) else {k: True for k in ("beta", "inspektor", "modell", "skills", "fehlerbericht")}
        if self.stufe() == "admin":
            return {**{k: True for k in ("beta", "inspektor", "modell", "skills", "fehlerbericht")}, **{k: True for k in gespeichert}}
        return {k: bool(v) for k, v in gespeichert.items()}

    def flag(self, schluessel: str) -> bool:
        if not self.im_team():
            return False
        if self.stufe() == "admin":
            return True
        return bool((self.zustand().get("flags") or {}).get(schluessel, True))

    def felworks_schluessel(self) -> str | None:
        return self.token() if self.flag("modell") else None

    def beta_aktiv(self) -> bool:
        return self.flag("beta") and bool(self.zustand().get("beta"))

    def beta_setzen(self, an: bool) -> dict:
        if not self.flag("beta"):
            raise ValueError("Beta-Versionen gibt es für Entwickler und Admins, wenn der Admin sie freigegeben hat.")
        self._zustand_setzen(beta=bool(an))
        return self.status()

    def _nutzung(self) -> dict:
        heute = date.today().isoformat()
        try:
            werte = json.loads(self.nutzung_datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            werte = {}
        return werte if isinstance(werte, dict) and werte.get("datum") == heute else {"datum": heute}

    def erlaubt(self, feature: str) -> bool:
        if self.premium():
            return True
        grenze = KONTINGENT.get(feature)
        return grenze is not None and int(self._nutzung().get(feature, 0)) < grenze

    def pruefen(self, feature: str) -> None:
        if not self.premium() and feature not in KONTINGENT:
            raise PremiumNoetig(feature)

    def verbrauchen(self, feature: str) -> None:
        if self.premium():
            return
        grenze = KONTINGENT.get(feature)
        if grenze is None:
            raise PremiumNoetig(feature)
        with self.lock:
            werte = self._nutzung()
            if int(werte.get(feature, 0)) >= grenze:
                name = FEATURES[feature][0]
                raise PremiumNoetig(feature, f"Heute sind {'alle ' if grenze > 1 else ''}{grenze} kostenlose{'n' if grenze > 1 else ''} {name}-{'Aufträge' if grenze > 1 else 'Auftrag'} aufgebraucht. Mit Jon Premium arbeitest du unbegrenzt weiter.")
            werte[feature] = int(werte.get(feature, 0)) + 1
            self.directory.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self.nutzung_datei, json.dumps(werte))

    def sperrtext(self, feature: str) -> str:
        return f"Fehler: {PremiumNoetig(feature).text} Der Nutzer kann Premium oben links neben „JON“ freischalten."

    def status(self) -> dict:
        daten = self.lizenz()
        stufe = self.stufe()
        nutzung = self._nutzung()
        hinweis = ""
        if daten.get("fehler"):
            hinweis = daten["fehler"]
        elif daten and self.geraet() not in daten.get("geraete", []):
            hinweis = "Der gespeicherte Lizenzschlüssel gilt für ein anderes Gerät."
        elif daten and daten.get("exp") and float(daten["exp"]) < time.time():
            hinweis = "Deine Lizenz ist abgelaufen. Jon erneuert sie automatisch, sobald der FelWorks-Codeserver erreichbar ist." if daten.get("quelle") == "codes" else "Deine Premium-Lizenz ist abgelaufen. Jon erneuert sie automatisch, sobald dein Abo aktiv ist."
        return {
            "stufe": stufe,
            "name": STUFEN[stufe],
            "geraet": self.geraet(),
            "gueltig_bis": float(daten.get("exp") or 0) if stufe != "standard" else 0,
            "inhaber": str(daten.get("name", ""))[:80] if stufe != "standard" else "",
            "abo": bool(daten.get("abo")) and stufe == "premium",
            "kostenlos": bool(daten.get("kostenlos")) and stufe == "premium",
            "hinweis": hinweis,
            "token": self.token() if stufe != "standard" else "",
            "offen": bool(self.offen),
            "codes": stufe == "admin" and self.vom_codeserver(),
            "team": stufe in TEAM and self.vom_codeserver(),
            "haupt": bool(stufe == "admin" and daten.get("pk")),
            "flags": self.flags(),
            "beta": self.beta_aktiv(),
            "ungelesen": int(self.zustand().get("ungelesen") or 0) if stufe in TEAM else 0,
            "plaene": PLAENE,
            "features": [{"key": key, "name": name, "beschreibung": text, "frei": stufe != "standard", "kontingent": KONTINGENT.get(key, 0), "verbraucht": int(nutzung.get(key, 0))} for key, (name, text) in FEATURES.items()],
        }

    async def _senden(self, adresse: str, daten: dict, wer: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                for _ in range(3):
                    antwort = await client.post(adresse, json=daten)
                    if antwort.status_code not in {301, 302, 307, 308} or not antwort.headers.get("location"):
                        break
                    adresse = str(antwort.url.join(antwort.headers["location"]))
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Der {wer} ist nicht erreichbar ({type(exc).__name__}). Prüfe deine Internetverbindung.") from exc
        try:
            inhalt = antwort.json()
        except ValueError:
            inhalt = {}
        if antwort.status_code >= 400 or not isinstance(inhalt, dict):
            inhalt = inhalt if isinstance(inhalt, dict) else {}
            detail = inhalt.get("detail") if isinstance(inhalt.get("detail"), str) else ""
            text = str(inhalt.get("fehler") or detail or f"Der {wer} antwortet mit Fehler {antwort.status_code}.")
            raise (Abgelehnt if antwort.status_code in {401, 403} else ValueError)(text)
        return inhalt

    async def rufen(self, name: str, daten: dict) -> dict:
        return await self._senden(get_settings().jon_premium_url.rstrip("/") + f"/premium-{name}", daten, "FelWorks-Lizenzserver")

    async def codeserver(self, name: str, daten: dict) -> dict:
        basis = get_settings().jon_codes_url.rstrip("/")
        if not basis:
            raise ConnectionError("Es ist kein FelWorks-Codeserver eingestellt.")
        return await self._senden(f"{basis}/{name}", daten, "FelWorks-Codeserver")

    async def kaufen(self, plan: str) -> dict:
        antwort = await self.rufen("checkout", {"plan": plan, "geraet": self.geraet()})
        self.offen = {"id": antwort["id"], "seit": time.time()}
        return {"url": antwort["url"]}

    async def abholen(self) -> dict:
        if not self.offen:
            return {"fertig": self.premium(), **self.status()}
        antwort = await self.rufen("lizenz", {"aktion": "abholen", "session_id": self.offen["id"], "geraet": self.geraet()})
        if not antwort.get("token"):
            if time.time() - self.offen["seit"] > 3600:
                self.offen = {}
            return {"fertig": False, **self.status()}
        self.offen = {}
        return {"fertig": True, **self.speichern(antwort["token"])}

    async def eingeben(self, token: str) -> dict:
        if not token.strip().startswith(VERSION + "."):
            return await self.einloesen(token)
        daten = lesen(token)
        if self.geraet() in daten.get("geraete", []):
            return self.speichern(token)
        antwort = await self.rufen("lizenz", {"aktion": "geraet", "token": token.strip(), "geraet": self.geraet()})
        return self.speichern(antwort["token"])

    async def einloesen(self, code: str) -> dict:
        antwort = await self.codeserver("einloesen", {"code": code.strip(), "geraet": self.geraet()})
        self.zustand_datei.unlink(missing_ok=True)
        status = self.speichern(antwort["token"])
        if self.im_team():
            try:
                return await self.erneuern()
            except Exception:
                return status
        return status

    async def admin(self, passwort: str) -> dict:
        return await self.einloesen(passwort)

    async def kostenlos_verfuegbar(self) -> bool:
        if self.premium():
            return False
        jetzt = time.time()
        zeit, wert = self._kostenlos
        if jetzt - zeit < 120:
            return wert
        try:
            wert = bool((await self.codeserver("kostenlos/verfuegbar", {})).get("verfuegbar"))
        except (ConnectionError, ValueError):
            wert = False
        self._kostenlos = (jetzt, wert)
        return wert

    async def kostenlos_holen(self) -> dict:
        if self.premium():
            return self.status()
        try:
            antwort = await self.codeserver("kostenlos", {"geraet": self.geraet()})
        except Abgelehnt:
            self._kostenlos = (time.time(), False)
            raise
        self.zustand_datei.unlink(missing_ok=True)
        self._kostenlos = (0.0, False)
        return self.speichern(antwort["token"])

    async def erneuern(self) -> dict:
        token = self.token()
        if not token:
            return self.status()
        if self.vom_codeserver():
            anfrage = {"token": token, "geraet": self.geraet()}
            if self.stufe() in TEAM:
                anfrage["bericht"] = self.bericht()
            try:
                antwort = await self.codeserver("erneuern", anfrage)
            except Abgelehnt:
                self.abmelden()
                raise
            if "flags" in antwort:
                self._zustand_setzen(flags=antwort.get("flags") or {}, ungelesen=int(antwort.get("ungelesen") or 0), rolle=antwort.get("rolle", ""), geprueft=time.time())
            return self.speichern(antwort["token"])
        antwort = await self.rufen("lizenz", {"aktion": "erneuern", "token": token, "geraet": self.geraet()})
        return self.speichern(antwort["token"])

    def _admin_lizenz(self) -> dict:
        if self.stufe() != "admin" or not self.vom_codeserver():
            raise ValueError("Entwickler-Codes verwaltet nur der Admin. Melde dich dafür einmal mit dem Admin-Code an.")
        return {"token": self.token(), "geraet": self.geraet()}

    async def codes(self) -> dict:
        return await self.codeserver("liste", self._admin_lizenz())

    async def code_erstellen(self, name: str, geraete: int, art: str = "entwickler", tage: int = 0) -> dict:
        return await self.codeserver("erstellen", {**self._admin_lizenz(), "name": name.strip(), "geraete": geraete, "art": art, "tage": tage})

    def bericht(self) -> dict:
        from app.services.inspektor import get_inspektor

        return {"version": get_settings().app_version, "system": f"{platform.system()} {platform.release()}", "nutzung": get_inspektor().nutzung()}

    def _team_lizenz(self) -> dict:
        if not self.im_team():
            raise ValueError("Das gibt es nur für Entwickler und Admins.")
        return {"token": self.token(), "geraet": self.geraet()}

    async def team(self, aktion: str, daten: dict | None = None) -> dict:
        if aktion not in TEAM_AKTIONEN:
            raise ValueError("Unbekannte Aktion.")
        antwort = await self.codeserver(aktion, {**(daten or {}), **self._team_lizenz()})
        if aktion == "kostenlos/setzen":
            self._kostenlos = (0.0, False)
        if isinstance(antwort, dict) and "ungelesen" in antwort:
            self._zustand_setzen(ungelesen=int(antwort.get("ungelesen") or 0))
        return antwort

    def systembericht(self) -> str:
        from app.services.settings_service import get_settings_service

        anbieter, modell = get_settings_service().selection()
        return f"Jon {get_settings().app_version} · {STUFEN[self.stufe()]} · {platform.system()} {platform.release()} · Python {platform.python_version()} · Modell {anbieter or '-'} / {modell or '-'}"

    async def fehlerbericht(self, text: str, bild: bool = False) -> dict:
        if not self.flag("fehlerbericht"):
            raise ValueError("Fehlerberichte mit einem Klick hat der Admin für dich ausgeschaltet.")
        import asyncio

        from app.core.logbook import export_text

        log = schwaerzen("\n".join(export_text().splitlines()[-220:]))
        anhang = {"system": self.systembericht(), "log": log}
        if bild:
            try:
                from app.services.system_service import SystemService

                anhang["bild"] = await asyncio.to_thread(SystemService().screenshot_data_url, 1280, 55)
            except Exception:
                anhang["system"] += " · Bildschirmfoto nicht möglich"
        return await self.team("team/senden", {"art": "fehler", "text": text.strip() or "Fehlerbericht", "an": "admin", "anhang": anhang})

    async def skill_installieren(self, kennung: str) -> dict:
        import asyncio

        from app.services.skill_service import SkillService

        skill = await self.team("skills/holen", {"id": kennung})
        ergebnis = await asyncio.to_thread(SkillService().write, str(skill["name"]), str(skill["inhalt"]))
        return {**ergebnis, "titel": skill.get("titel", skill["name"])}

    async def code_sperren(self, kennung: str, gesperrt: bool = True) -> dict:
        return await self.codeserver("sperren", {**self._admin_lizenz(), "id": kennung, "gesperrt": gesperrt})

    async def portal(self) -> dict:
        if self.stufe() != "premium":
            raise ValueError("Die Abo-Verwaltung gibt es nur mit einem Premium-Abo.")
        return await self.rufen("portal", {"token": self.token()})

    def braucht_erneuerung(self) -> bool:
        daten = self.lizenz()
        if self.vom_codeserver():
            return True
        return bool(daten) and not daten.get("fehler") and bool(daten.get("exp")) and float(daten["exp"]) - time.time() < 10 * 86400


_premium: Premium | None = None


def get_premium() -> Premium:
    global _premium
    if _premium is None:
        _premium = Premium()
    return _premium
