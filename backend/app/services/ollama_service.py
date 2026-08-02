from __future__ import annotations

import ipaddress
import json
import re
import socket
import threading
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import DATA_DIR, get_settings

OLLAMA_FILE = DATA_DIR / "ollama.json"

DEFAULT_PORT = 11434
DEFAULT_HOST = "127.0.0.1"
STATUS_TTL = 15.0
PROBE_TIMEOUT = 4.0
KEEP_ALIVE = re.compile(r"^-?\d+(\.\d+)?(ns|us|ms|s|m|h)?$")
HOST_CHARS = re.compile(r"^[A-Za-z0-9._:\-\[\]%]+$")

FALLBACK_MODELS = ["llama3.2", "qwen2.5", "mistral"]

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "scheme": "http",
    "host": DEFAULT_HOST,
    "port": DEFAULT_PORT,
    "model": "",
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_tokens": 32768,
    "context_length": 4096,
    "keep_alive": "5m",
    "seed": -1,
    "system_prompt": "",
    "stream": True,
    "timeout": 120.0,
    "auto_reconnect": True,
    "auto_load_models": True,
    "last_success": "",
}

BOUNDS: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "top_k": (0, 200),
    "max_tokens": (1, 131072),
    "context_length": (256, 1048576),
    "timeout": (5.0, 3600.0),
    "port": (1, 65535),
}


class OllamaConfigError(ValueError):
    pass


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "ja", "yes", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return fallback


def _as_number(key: str, value: Any, integer: bool) -> float | int:
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError):
        raise OllamaConfigError(f"{key}: Bitte eine Zahl eintragen.") from None
    low, high = BOUNDS[key]
    if number < low or number > high:
        pretty_low = int(low) if integer else low
        pretty_high = int(high) if integer else high
        raise OllamaConfigError(
            f"{key}: Wert muss zwischen {pretty_low} und {pretty_high} liegen."
        )
    return number


def _clean_host(value: Any) -> str:
    host = str(value or "").strip().strip("/")
    if not host:
        raise OllamaConfigError("Host: Bitte eine Adresse eintragen.")
    if "://" in host:
        host = urlsplit(host).hostname or ""
    if not host or not HOST_CHARS.match(host):
        raise OllamaConfigError(
            "Host: Erlaubt sind Name oder IP, zum Beispiel 127.0.0.1, "
            "192.168.1.50 oder 100.101.102.103."
        )
    return host


def _clean_max_tokens(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise OllamaConfigError("max_tokens: Bitte eine Zahl eintragen.") from None
    if number == -1:
        return -1
    low, high = BOUNDS["max_tokens"]
    if number < low or number > high:
        raise OllamaConfigError(
            f"max_tokens: Wert muss zwischen {int(low)} und {int(high)} liegen "
            "oder -1 für unbegrenzt sein."
        )
    return number


def _clean_keep_alive(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        return DEFAULTS["keep_alive"]
    if not KEEP_ALIVE.match(text):
        raise OllamaConfigError(
            "Keep Alive: Erlaubt sind zum Beispiel 5m, 30s, 1h, 0 "
            "(sofort entladen) oder -1 (dauerhaft geladen)."
        )
    return text


def _clean_seed(value: Any) -> int:
    if value is None or (isinstance(value, str) and not value.strip()):
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        raise OllamaConfigError("Seed: Bitte eine ganze Zahl oder -1 eintragen.") from None


def split_url(raw: str) -> tuple[str, str, int]:
    text = str(raw or "").strip()
    if not text:
        raise OllamaConfigError("Server-URL: Bitte eine Adresse eintragen.")
    if "://" not in text:
        text = "http://" + text
    parts = urlsplit(text)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise OllamaConfigError("Server-URL: Erlaubt sind http:// und https://.")
    host = parts.hostname or ""
    if not host:
        raise OllamaConfigError("Server-URL: Der Host fehlt.")
    try:
        port = parts.port or (443 if scheme == "https" else DEFAULT_PORT)
    except ValueError:
        raise OllamaConfigError("Server-URL: Der Port ist keine gültige Zahl.") from None
    return scheme, host, int(port)


class OllamaService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()
        self._status: dict[str, Any] = {}
        self._status_at = 0.0
        self._models: list[str] = []

    def _load(self) -> dict[str, Any]:
        data = dict(DEFAULTS)
        try:
            scheme, host, port = split_url(get_settings().ollama_base_url)
            data.update({"scheme": scheme, "host": host, "port": port})
        except Exception:
            pass
        if OLLAMA_FILE.exists():
            try:
                stored = json.loads(OLLAMA_FILE.read_text(encoding="utf-8"))
            except Exception:
                stored = {}
            if isinstance(stored, dict):
                for key in DEFAULTS:
                    if key in stored and stored[key] is not None:
                        data[key] = stored[key]
        try:
            data = self._validate(data, dict(DEFAULTS))
        except OllamaConfigError:
            data = dict(DEFAULTS)
        if not data["model"]:
            data["model"] = self._model_from_settings()
        return data

    @staticmethod
    def _model_from_settings() -> str:
        try:
            from app.services.settings_service import get_settings_service

            provider, model = get_settings_service().selection()
        except Exception:
            return ""
        return model if provider == "ollama" else ""

    def _save(self) -> None:
        try:
            OLLAMA_FILE.parent.mkdir(parents=True, exist_ok=True)
            OLLAMA_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _validate(self, values: dict, base: dict) -> dict[str, Any]:
        data = dict(base)
        incoming = dict(values)
        if "url" in incoming and incoming["url"] is not None:
            scheme, host, port = split_url(incoming.pop("url"))
            incoming.setdefault("scheme", scheme)
            incoming.setdefault("host", host)
            incoming.setdefault("port", port)
        for key, value in incoming.items():
            if key not in DEFAULTS or value is None:
                continue
            if key == "enabled":
                data[key] = _as_bool(value, base[key])
            elif key == "stream":
                data[key] = _as_bool(value, base[key])
            elif key == "auto_reconnect":
                data[key] = _as_bool(value, base[key])
            elif key == "auto_load_models":
                data[key] = _as_bool(value, base[key])
            elif key == "scheme":
                scheme = str(value).strip().lower().replace("://", "")
                if scheme not in ("http", "https"):
                    raise OllamaConfigError("Protokoll: Erlaubt sind http und https.")
                data[key] = scheme
            elif key == "host":
                data[key] = _clean_host(value)
            elif key == "max_tokens":
                data[key] = _clean_max_tokens(value)
            elif key in ("port", "top_k", "context_length"):
                data[key] = _as_number(key, value, True)
            elif key in ("temperature", "top_p", "timeout"):
                data[key] = _as_number(key, value, False)
            elif key == "keep_alive":
                data[key] = _clean_keep_alive(value)
            elif key == "seed":
                data[key] = _clean_seed(value)
            elif key in ("model", "system_prompt", "last_success"):
                data[key] = str(value).strip() if key != "system_prompt" else str(value)
        return data

    def config(self) -> dict[str, Any]:
        with self._lock:
            data = dict(self._data)
        data["url"] = self._url(data)
        data["api_base"] = self._url(data) + "/v1"
        return data

    def update(self, values: dict) -> dict[str, Any]:
        with self._lock:
            data = self._validate(values, self._data)
            changed = data != self._data
            self._data = data
            if changed:
                self._save()
        if changed:
            self._status = {}
            self._status_at = 0.0
        return self.config()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._data = dict(DEFAULTS)
            self._save()
        self._status = {}
        self._status_at = 0.0
        return self.config()

    def _url(self, data: dict) -> str:
        host = data["host"]
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"{data['scheme']}://{host}:{int(data['port'])}"

    def base_url(self) -> str:
        with self._lock:
            return self._url(self._data)

    def openai_base_url(self) -> str:
        return self.base_url() + "/v1"

    def enabled(self) -> bool:
        with self._lock:
            return bool(self._data["enabled"])

    def timeout(self) -> float:
        with self._lock:
            return float(self._data["timeout"])

    def selected_model(self) -> str:
        with self._lock:
            return str(self._data["model"])

    def chat_options(self) -> dict[str, Any]:
        with self._lock:
            data = dict(self._data)
        options: dict[str, Any] = {
            "temperature": float(data["temperature"]),
            "top_p": float(data["top_p"]),
            "top_k": int(data["top_k"]),
            "num_predict": int(data["max_tokens"]),
            "num_ctx": int(data["context_length"]),
        }
        if int(data["seed"]) >= 0:
            options["seed"] = int(data["seed"])
        return options

    def _mark_success(self) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self._data["last_success"] = stamp
            self._save()

    def last_success(self) -> str:
        with self._lock:
            return str(self._data["last_success"])

    def friendly_error(self, exc: Exception) -> str:
        url = self.base_url()
        if isinstance(exc, httpx.ConnectError):
            return (
                f"Keine Verbindung zu Ollama unter {url}. Läuft der Server dort, "
                "und sind Host und Port richtig eingetragen?"
            )
        if isinstance(exc, httpx.ConnectTimeout):
            return (
                f"{url} antwortet nicht. Bei einem Gerät im Netzwerk muss auf dem "
                "Server OLLAMA_HOST=0.0.0.0 gesetzt und der Port in der Firewall "
                "freigegeben sein."
            )
        if isinstance(exc, httpx.ReadTimeout):
            return (
                "Ollama hat zu lange gebraucht. Erhöhe das Timeout oder nimm ein "
                "kleineres Modell."
            )
        if isinstance(exc, httpx.TimeoutException):
            return f"Zeitüberschreitung bei {url}."
        if isinstance(exc, httpx.InvalidURL):
            return f"Die Adresse {url} ist ungültig."
        if isinstance(exc, httpx.HTTPStatusError):
            return f"Ollama meldet Fehler {exc.response.status_code}: {self.detail(exc)}"
        if isinstance(exc, httpx.HTTPError):
            return f"Verbindungsfehler zu {url}: {exc}"
        return str(exc)

    @staticmethod
    def detail(exc: httpx.HTTPStatusError) -> str:
        try:
            payload = exc.response.json()
        except Exception:
            return exc.response.text.strip()[:300] or "unbekannter Fehler"
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                return str(error.get("message", error))[:300]
            if error:
                return str(error)[:300]
        return str(payload)[:300]

    async def _fetch(self, path: str, timeout: float) -> Any:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(self.base_url() + path)
            response.raise_for_status()
            return response.json()

    async def fetch_models(self) -> list[str]:
        data = await self._fetch("/api/tags", PROBE_TIMEOUT)
        items = data.get("models", []) if isinstance(data, dict) else []
        names = [
            str(item.get("name") or item.get("model") or "").strip()
            for item in items
            if isinstance(item, dict)
        ]
        return sorted(name for name in names if name)

    def auto_load_models(self) -> bool:
        with self._lock:
            return bool(self._data["auto_load_models"])

    def known_models(self) -> list[str]:
        return list(self._models)

    async def version(self) -> dict:
        data = await self._fetch("/api/version", PROBE_TIMEOUT)
        return data if isinstance(data, dict) else {}

    async def models(self, refresh: bool = False) -> list[str]:
        if not self.enabled():
            return []
        if not refresh and self._models:
            return list(self._models)
        if not refresh and not self.auto_load_models():
            return []
        try:
            found = await self.fetch_models()
        except Exception:
            return list(self._models)
        self._models = found
        if found:
            self._mark_success()
        return list(found)

    async def status(self, force: bool = False) -> dict[str, Any]:
        config = self.config()
        now = time.monotonic()
        if not force and self._status and now - self._status_at < STATUS_TTL:
            return dict(self._status)
        base = {
            "state": "offline",
            "url": config["url"],
            "host": config["host"],
            "port": config["port"],
            "model": config["model"],
            "models": [],
            "model_count": 0,
            "version": "",
            "response_ms": 0,
            "last_success": config["last_success"],
            "error": "",
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }
        if not config["enabled"]:
            base["state"] = "disabled"
            base["error"] = "Ollama ist in den Einstellungen ausgeschaltet."
            self._status = base
            self._status_at = now
            return dict(base)
        started = time.perf_counter()
        try:
            version = await self._fetch("/api/version", PROBE_TIMEOUT)
            if force or config["auto_load_models"] or not self._models:
                models = await self.fetch_models()
            else:
                models = list(self._models)
        except Exception as exc:
            base["error"] = self.friendly_error(exc)
            base["response_ms"] = int((time.perf_counter() - started) * 1000)
            self._status = base
            self._status_at = now
            return dict(base)
        base["response_ms"] = int((time.perf_counter() - started) * 1000)
        base["state"] = "online"
        base["version"] = str(version.get("version", "")) if isinstance(version, dict) else ""
        base["models"] = models
        base["model_count"] = len(models)
        self._models = models
        self._mark_success()
        base["last_success"] = self.last_success()
        if config["model"] and config["model"] not in models:
            base["error"] = (
                f"Das gewählte Modell {config['model']} ist auf dem Server nicht "
                f"installiert. Dort einmal: ollama pull {config['model']}"
            )
        self._status = base
        self._status_at = now
        return dict(base)

    def host_suggestions(self) -> list[dict[str, str]]:
        found = [
            {
                "label": "Dieser PC",
                "host": DEFAULT_HOST,
                "kind": "localhost",
                "hint": "Ollama läuft auf demselben Rechner wie Jon.",
            }
        ]
        addresses: list[str] = []
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            addresses.append(str(probe.getsockname()[0]))
        except Exception:
            pass
        finally:
            probe.close()
        try:
            addresses.extend(socket.gethostbyname_ex(socket.gethostname())[2])
        except Exception:
            pass
        tailscale = ipaddress.ip_network("100.64.0.0/10")
        seen = {DEFAULT_HOST}
        for raw in addresses:
            text = str(raw)
            if text in seen:
                continue
            try:
                address = ipaddress.ip_address(text)
            except ValueError:
                continue
            if address.is_loopback:
                continue
            seen.add(text)
            if address in tailscale:
                found.append(
                    {
                        "label": "Tailscale",
                        "host": text,
                        "kind": "tailscale",
                        "hint": "Adresse dieses PCs im Tailscale-Netz.",
                    }
                )
            elif address.is_private:
                found.append(
                    {
                        "label": "Heimnetz (LAN)",
                        "host": text,
                        "kind": "lan",
                        "hint": "Adresse dieses PCs im lokalen Netzwerk.",
                    }
                )
        return found

    async def test(self, values: dict | None = None) -> dict[str, Any]:
        if values:
            self.update(values)
        result = await self.status(force=True)
        result["ok"] = result["state"] == "online"
        return result


_service: OllamaService | None = None


def get_ollama_service() -> OllamaService:
    global _service
    if _service is None:
        _service = OllamaService()
    return _service
