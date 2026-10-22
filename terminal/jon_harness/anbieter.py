from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import netz
from .speicher import Einstellungen, ordner, schreiben

CODES = os.environ.get("JON_CODES_URL", "https://felworks.tail661828.ts.net/codes").rstrip("/")
JON_ADRESSE = os.environ.get("JON_ADRESSE", "http://127.0.0.1:8756").rstrip("/")
DENK_SCHALTER = ("nemotron-3", "nemotron-nano-3", "nemotron-3.5")


@dataclass
class Anbieter:
    kennung: str
    name: str
    basis: str
    modelle: list[str] = field(default_factory=list)
    braucht_schluessel: bool = True
    seite: str = ""
    hinweis: str = ""
    lokal: bool = False


KATALOG: dict[str, Anbieter] = {
    a.kennung: a
    for a in [
        Anbieter("felworks", "FelWorks", f"{CODES}/llm/v1", ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-super-120b-a12b"], False, "", "kostenlos, ohne Schlüssel"),
        Anbieter("jon", "Jon (dein Jon am PC)", f"{JON_ADRESSE}/api/llm/v1", ["jon"], False, "", "nutzt Jons Schlüssel und Modelle", True),
        Anbieter("nvidia", "NVIDIA NIM", "https://integrate.api.nvidia.com/v1", ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/nemotron-3.5-lightning-30b-a3b", "deepseek-ai/deepseek-v4.1-flash", "moonshotai/kimi-k2.6", "z-ai/glm-5.3"], True, "https://build.nvidia.com/settings/api-keys", "viele Modelle gratis"),
        Anbieter("openai", "OpenAI", "https://api.openai.com/v1", ["gpt-5.1", "gpt-5-mini", "gpt-4.1"], True, "https://platform.openai.com/api-keys"),
        Anbieter("anthropic", "Anthropic (Claude)", "https://api.anthropic.com/v1", ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"], True, "https://console.anthropic.com/settings/keys"),
        Anbieter("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", ["gemini-2.5-pro", "gemini-2.5-flash"], True, "https://aistudio.google.com/apikey"),
        Anbieter("deepseek", "DeepSeek", "https://api.deepseek.com/v1", ["deepseek-chat", "deepseek-reasoner"], True, "https://platform.deepseek.com/api_keys"),
        Anbieter("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", ["openrouter/auto"], True, "https://openrouter.ai/keys", "hunderte Modelle"),
        Anbieter("groq", "Groq", "https://api.groq.com/openai/v1", ["llama-3.3-70b-versatile"], True, "https://console.groq.com/keys", "sehr schnell"),
        Anbieter("mistral", "Mistral", "https://api.mistral.ai/v1", ["mistral-large-latest", "codestral-latest"], True, "https://console.mistral.ai/api-keys"),
        Anbieter("xai", "xAI (Grok)", "https://api.x.ai/v1", ["grok-4"], True, "https://console.x.ai"),
        Anbieter("ollama", "Ollama (lokal)", os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1", [], False, "https://ollama.com/download", "läuft offline auf deinem PC", True),
        Anbieter("lmstudio", "LM Studio (lokal)", "http://127.0.0.1:1234/v1", [], False, "https://lmstudio.ai", "läuft offline auf deinem PC", True),
    ]
}


class Jon:
    def __init__(self) -> None:
        self.verbunden = False
        self.token = ""
        self.info: dict = {}
        self.grund = ""

    def daten_ordner(self) -> Path | None:
        eigen = os.environ.get("JON_DATA_DIR")
        if eigen:
            return Path(eigen)
        if sys.platform == "win32":
            pfad = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Jon" / "data"
        else:
            pfad = Path.home() / ".local" / "share" / "jon" / "data"
        return pfad if pfad.exists() else None

    def installiert(self) -> bool:
        if self.daten_ordner() is not None:
            return True
        if sys.platform == "win32":
            for basis in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", "")):
                if basis and (Path(basis) / "Programs" / "Jon" / "Jon.exe").exists():
                    return True
        return False

    def verbinden(self, zeit: float = 2.5) -> bool:
        self.verbunden = False
        if os.environ.get("JON_HARNESS_OHNE_JON"):
            self.grund = "abgeschaltet"
            return False
        try:
            gesund = netz.anfrage("GET", f"{JON_ADRESSE}/api/health", zeit=zeit).json()
        except Exception:
            self.grund = "Jon läuft gerade nicht" if self.installiert() else "Jon ist nicht installiert"
            return False
        kandidaten = []
        datei = gesund.get("token_file")
        if datei:
            kandidaten.append(Path(datei))
        ordner_jon = self.daten_ordner()
        if ordner_jon:
            kandidaten.append(ordner_jon / "access.token")
        for pfad in kandidaten:
            try:
                self.token = pfad.read_text(encoding="utf-8").strip()
                break
            except OSError:
                continue
        try:
            self.info = netz.anfrage("GET", f"{JON_ADRESSE}/api/terminal/hallo", kopf=self.kopf(), zeit=zeit).json()
        except netz.NetzFehler as fehler:
            self.grund = "Jon ist zu alt für das Terminal – bitte Jon aktualisieren" if fehler.status == 404 else f"Jon lehnt ab: {fehler}"
            return False
        except Exception as fehler:
            self.grund = str(fehler)
            return False
        self.info["version"] = self.info.get("version") or gesund.get("version", "")
        self.verbunden = True
        self.grund = ""
        return True

    def kopf(self) -> dict:
        return {"X-Jon-Token": self.token} if self.token else {}

    def auftrag(self, text: str, ordner_pfad: str, melden=None) -> str:
        nachricht = {
            "messages": [{"role": "user", "content": text}],
            "persist": False,
            "tool_mode": "allow",
            "source": "terminal",
            "workspace": ordner_pfad,
        }
        antwort = netz.anfrage("POST", f"{JON_ADRESSE}/api/chat", nachricht, kopf=self.kopf(), zeit=900, strom=True)
        teile: list[str] = []
        erledigt: list[str] = []
        for ereignis in netz.strom_ereignisse(antwort):
            art = ereignis.get("type")
            if art == "content":
                teile.append(str(ereignis.get("delta") or ""))
            elif art == "tool" and ereignis.get("status") == "running" and melden:
                melden(str(ereignis.get("summary") or ereignis.get("name") or "Aktion"))
            elif art == "tool" and ereignis.get("status") == "done" and ereignis.get("ok"):
                erledigt.append(str(ereignis.get("name") or ""))
            elif art == "error":
                teile.append(f"[Fehler] {ereignis.get('message', '')}")
        text = "".join(teile).strip() or "Jon hat ohne Text geantwortet."
        if erledigt:
            text += "\n\nJon hat ausgeführt: " + ", ".join(dict.fromkeys(erledigt))
        return text


class FelWorks:
    def __init__(self, einstellungen: Einstellungen) -> None:
        self.einstellungen = einstellungen
        self.fehler = ""

    def token(self, neu: bool = False) -> str:
        gespeichert = self.einstellungen.get("felworks_token")
        if gespeichert and not neu:
            return str(gespeichert)
        try:
            antwort = netz.anfrage("POST", f"{CODES}/gast", {"geraet": self.einstellungen.get("geraet"), "art": "terminal"}, zeit=15).json()
        except netz.NetzFehler as fehler:
            if fehler.status == 404:
                self.fehler = "Der freie FelWorks-Zugang wird gerade eingerichtet. Mit /api kannst du so lange einen eigenen Schlüssel nutzen."
            else:
                self.fehler = str(fehler)
            return ""
        except Exception as fehler:
            self.fehler = f"FelWorks ist gerade nicht erreichbar ({fehler})."
            return ""
        token = str(antwort.get("token") or "")
        if token:
            self.einstellungen.setzen(felworks_token=token)
        return token


class Verbindung:
    def __init__(self, einstellungen: Einstellungen, jon: Jon) -> None:
        self.einstellungen = einstellungen
        self.jon = jon
        self.felworks = FelWorks(einstellungen)
        self.ohne_werkzeuge: set[str] = set()
        self.ohne_denkschalter: set[str] = set()
        self._modelle: dict[str, tuple[float, list[str]]] = {}

    def bereit(self, kennung: str) -> bool:
        eintrag = KATALOG.get(kennung)
        if eintrag is None:
            return False
        if kennung == "jon":
            return self.jon.verbunden
        if kennung == "felworks":
            return True
        if eintrag.braucht_schluessel:
            return bool(self.einstellungen.schluessel(kennung))
        return True

    def kopf(self, kennung: str) -> dict:
        kopf = {"Content-Type": "application/json"}
        if kennung == "jon":
            kopf.update(self.jon.kopf())
            return kopf
        if kennung == "felworks":
            token = self.felworks.token()
            if token:
                kopf["Authorization"] = f"Bearer {token}"
            return kopf
        schluessel = self.einstellungen.schluessel(kennung)
        if schluessel:
            kopf["Authorization"] = f"Bearer {schluessel}"
        if kennung == "anthropic" and schluessel:
            kopf["x-api-key"] = schluessel
            kopf["anthropic-version"] = "2023-06-01"
        if kennung == "openrouter":
            kopf["HTTP-Referer"] = "https://getjon.info"
            kopf["X-Title"] = "Jon Harness"
        return kopf

    def modelle(self, kennung: str, frisch: bool = False) -> list[str]:
        eintrag = KATALOG[kennung]
        zwischen = self._modelle.get(kennung)
        if zwischen and not frisch and time.time() - zwischen[0] < 600:
            return zwischen[1]
        liste: list[str] = []
        try:
            antwort = netz.anfrage("GET", f"{eintrag.basis}/models", kopf=self.kopf(kennung), zeit=8).json()
            for modell in antwort.get("data", []) or antwort.get("models", []) or []:
                name = modell.get("id") if isinstance(modell, dict) else str(modell)
                if name and not any(w in name.lower() for w in ("embed", "rerank", "whisper", "tts", "dall-e", "moderation", "guard", "safety", "parse", "reward", "image", "audio", "transcribe", "vl-1b")):
                    liste.append(str(name).removeprefix("models/"))
        except Exception:
            liste = []
        if not liste:
            liste = list(eintrag.modelle)
        else:
            bevorzugt = [m for m in eintrag.modelle if m in liste]
            liste = bevorzugt + sorted(m for m in liste if m not in bevorzugt)
        self._modelle[kennung] = (time.time(), liste)
        return liste

    def pruefen(self, kennung: str, schluessel: str) -> str:
        eintrag = KATALOG[kennung]
        kopf = {"Authorization": f"Bearer {schluessel}"}
        if kennung == "anthropic":
            kopf.update({"x-api-key": schluessel, "anthropic-version": "2023-06-01"})
        try:
            netz.anfrage("GET", f"{eintrag.basis}/models", kopf=kopf, zeit=12)
            return ""
        except netz.NetzFehler as fehler:
            if fehler.status in (401, 403):
                return "Der Schlüssel wurde abgelehnt."
            if fehler.status == 404:
                return ""
            return str(fehler)
        except Exception as fehler:
            return f"Keine Verbindung: {fehler}"

    def strom(self, kennung: str, modell: str, nachrichten: list[dict], werkzeuge: list[dict] | None, denken: bool | None = None, max_tokens: int = 8192, temperatur: float = 0.4):
        eintrag = KATALOG[kennung]
        koerper: dict = {"model": modell, "messages": nachrichten, "stream": True, "max_tokens": max_tokens, "temperature": temperatur}
        if kennung not in ("anthropic",):
            koerper["stream_options"] = {"include_usage": True}
        nutze_werkzeuge = bool(werkzeuge) and f"{kennung}|{modell}" not in self.ohne_werkzeuge
        if nutze_werkzeuge:
            koerper["tools"] = werkzeuge
            koerper["tool_choice"] = "auto"
        if any(m in modell.lower() for m in DENK_SCHALTER) and f"{kennung}|{modell}" not in self.ohne_denkschalter:
            koerper["chat_template_kwargs"] = {"enable_thinking": bool(denken)}
        for versuch in range(4):
            try:
                return netz.anfrage("POST", f"{eintrag.basis}/chat/completions", koerper, kopf=self.kopf(kennung), zeit=240, strom=True), nutze_werkzeuge
            except netz.NetzFehler as fehler:
                text = (fehler.roh or str(fehler)).lower()
                if fehler.status == 400 and "chat_template" in text and "chat_template_kwargs" in koerper:
                    self.ohne_denkschalter.add(f"{kennung}|{modell}")
                    koerper.pop("chat_template_kwargs", None)
                    continue
                if fehler.status == 400 and koerper.get("tools") and "tool" in text:
                    self.ohne_werkzeuge.add(f"{kennung}|{modell}")
                    koerper.pop("tools", None)
                    koerper.pop("tool_choice", None)
                    nutze_werkzeuge = False
                    continue
                if fehler.status == 400 and "stream_options" in text:
                    koerper.pop("stream_options", None)
                    continue
                if kennung == "felworks" and fehler.status in (401, 403) and versuch == 0:
                    if self.felworks.token(neu=True):
                        continue
                if fehler.status in (429, 500, 502, 503, 504) and versuch < 2:
                    time.sleep(1.5 * (versuch + 1))
                    continue
                raise
        raise netz.NetzFehler("Das Modell hat nicht geantwortet.")


def protokoll(eintrag: dict) -> None:
    try:
        pfad = ordner() / "protokoll.jsonl"
        if pfad.exists() and pfad.stat().st_size > 2_000_000:
            pfad.replace(pfad.with_suffix(".alt.jsonl"))
        with pfad.open("a", encoding="utf-8") as datei:
            datei.write(json.dumps({"zeit": int(time.time()), **eintrag}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def letzte_wahl_speichern(einstellungen: Einstellungen, kennung: str, modell: str) -> None:
    einstellungen.setzen(anbieter=kennung)
    einstellungen.modell_setzen(kennung, modell)


def schreibe_json(pfad: Path, daten) -> None:
    schreiben(pfad, json.dumps(daten, ensure_ascii=False, indent=2))
