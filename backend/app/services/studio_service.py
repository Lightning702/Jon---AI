from __future__ import annotations

import asyncio
import base64
import json
import re
import threading
import time
import uuid
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import DATA_DIR
from app.core.store import atomic_write_bytes, atomic_write_text

STUDIO_DIR = DATA_DIR / "studio"
CONFIG_FILE = DATA_DIR / "studio.json"
GALLERY_FILE = DATA_DIR / "studio_gallery.json"
MAX_GALLERY = 240
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

PROVIDERS: dict[str, dict[str, Any]] = {
    "pollinations": {
        "label": "Pollinations",
        "auth": "frei",
        "docs": "https://pollinations.ai",
        "hinweis": "Kostenlos und ohne Anmeldung — ideal zum Ausprobieren.",
        "bild_modelle": ["flux", "turbo"],
        "video_modelle": [],
        "standard_bild": "flux",
        "standard_video": "",
        "bearbeiten": False,
        "basis": "",
    },
    "together": {
        "label": "Together AI (FLUX)",
        "auth": "api_key",
        "docs": "https://api.together.xyz/settings/api-keys",
        "hinweis": "FLUX.1-schnell ist dort kostenlos nutzbar.",
        "bild_modelle": [
            "black-forest-labs/FLUX.1-schnell-Free",
            "black-forest-labs/FLUX.1-schnell",
            "black-forest-labs/FLUX.1-dev",
        ],
        "video_modelle": [],
        "standard_bild": "black-forest-labs/FLUX.1-schnell-Free",
        "standard_video": "",
        "bearbeiten": False,
        "basis": "",
    },
    "openai": {
        "label": "OpenAI",
        "auth": "api_key",
        "docs": "https://platform.openai.com/api-keys",
        "hinweis": "gpt-image-1 und DALL-E 3.",
        "bild_modelle": ["gpt-image-1", "dall-e-3"],
        "video_modelle": [],
        "standard_bild": "gpt-image-1",
        "standard_video": "",
        "bearbeiten": True,
        "basis": "",
    },
    "gemini": {
        "label": "Google Gemini & Imagen",
        "auth": "api_key",
        "docs": "https://aistudio.google.com/apikey",
        "hinweis": "Der Schlüssel aus dem Google AI Studio.",
        "bild_modelle": [
            "gemini-2.5-flash-image",
            "imagen-4.0-generate-001",
            "imagen-3.0-generate-002",
        ],
        "video_modelle": [],
        "standard_bild": "gemini-2.5-flash-image",
        "standard_video": "",
        "bearbeiten": True,
        "basis": "",
    },
    "stability": {
        "label": "Stability AI",
        "auth": "api_key",
        "docs": "https://platform.stability.ai/account/keys",
        "hinweis": "Stable Image Core, Ultra und SD 3.5.",
        "bild_modelle": ["core", "ultra", "sd3.5-large", "sd3.5-flash"],
        "video_modelle": [],
        "standard_bild": "core",
        "standard_video": "",
        "bearbeiten": False,
        "basis": "",
    },
    "replicate": {
        "label": "Replicate",
        "auth": "api_key",
        "docs": "https://replicate.com/account/api-tokens",
        "hinweis": "Bilder und echte Videos — Modellname als besitzer/modell.",
        "bild_modelle": [
            "black-forest-labs/flux-schnell",
            "black-forest-labs/flux-dev",
            "stability-ai/sdxl",
        ],
        "video_modelle": [
            "wan-video/wan-2.2-t2v-fast",
            "lightricks/ltx-video",
            "minimax/video-01",
        ],
        "standard_bild": "black-forest-labs/flux-schnell",
        "standard_video": "wan-video/wan-2.2-t2v-fast",
        "bearbeiten": True,
        "basis": "",
    },
    "fal": {
        "label": "fal.ai",
        "auth": "api_key",
        "docs": "https://fal.ai/dashboard/keys",
        "hinweis": "Bilder und Videos, sehr schnell.",
        "bild_modelle": ["fal-ai/flux/schnell", "fal-ai/flux/dev"],
        "video_modelle": ["fal-ai/ltx-video", "fal-ai/minimax-video"],
        "standard_bild": "fal-ai/flux/schnell",
        "standard_video": "fal-ai/ltx-video",
        "bearbeiten": True,
        "basis": "",
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "auth": "api_key",
        "docs": "https://build.nvidia.com",
        "hinweis": (
            "Nimmt automatisch deinen NVIDIA-Schlüssel aus Jon. FLUX läuft direkt "
            "bei NVIDIA, der Modellname ist frei eintragbar — jedes Bildmodell aus "
            "build.nvidia.com funktioniert, sobald NVIDIA es anbietet."
        ),
        "bild_modelle": [
            "black-forest-labs/flux.2-klein-4b",
            "black-forest-labs/flux.1-schnell",
            "black-forest-labs/flux.1-dev",
            "black-forest-labs/flux.1-kontext-dev",
        ],
        "video_modelle": [],
        "standard_bild": "black-forest-labs/flux.2-klein-4b",
        "standard_video": "",
        "bearbeiten": True,
        "basis": "",
    },
    "lokal": {
        "label": "Lokal auf deinem PC",
        "auth": "lokal",
        "docs": "https://github.com/AUTOMATIC1111/stable-diffusion-webui",
        "hinweis": (
            "Läuft auf deinem eigenen Rechner — genau wie Ollama, nur für Bilder. "
            "Ollama selbst erzeugt keine Bilder; nimm dafür Stable Diffusion WebUI "
            "(Port 7860), SD.Next oder Forge auf demselben PC und trag hier die "
            "Adresse ein. Kein Schlüssel, keine Kosten, nichts verlässt dein Gerät."
        ),
        "bild_modelle": [],
        "video_modelle": [],
        "standard_bild": "",
        "standard_video": "",
        "bearbeiten": True,
        "basis": "http://127.0.0.1:7860",
    },
}

SIZES = ["1024x1024", "1024x1536", "1536x1024", "1280x720", "768x768", "512x512"]

INHERITED = {"nvidia": "nvidia", "openai": "openai", "gemini": "gemini", "together": "together"}

PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47])

NVIDIA_SIDES = (768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344)
NVIDIA_RATIOS = (
    ("9:21", 9 / 21),
    ("1:2", 0.5),
    ("3:5", 0.6),
    ("2:3", 2 / 3),
    ("3:4", 0.75),
    ("6:7", 6 / 7),
    ("1:1", 1.0),
    ("7:6", 7 / 6),
    ("4:3", 4 / 3),
    ("3:2", 1.5),
    ("5:3", 5 / 3),
    ("13:7", 13 / 7),
    ("2:1", 2.0),
    ("21:9", 21 / 9),
)


class StudioError(RuntimeError):
    pass


def _extension(mime: str, url: str = "") -> str:
    table = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
    }
    clean = mime.split(";")[0].strip().lower()
    if clean in table:
        return table[clean]
    tail = url.split("?")[0].rsplit(".", 1)
    if len(tail) == 2 and 2 <= len(tail[1]) <= 4:
        return tail[1].lower()
    return "mp4" if clean.startswith("video") else "png"


class StudioService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config = self._load(CONFIG_FILE, {})
        self._gallery = self._load(GALLERY_FILE, [])
        try:
            STUDIO_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @staticmethod
    def _load(path, fallback):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, type(fallback)):
                return data
        except Exception:
            pass
        return json.loads(json.dumps(fallback))

    def _save(self) -> None:
        try:
            atomic_write_text(CONFIG_FILE,
                json.dumps(self._config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            atomic_write_text(GALLERY_FILE,
                json.dumps(self._gallery, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def active(self) -> str:
        name = str(self._config.get("anbieter") or "")
        return name if name in PROVIDERS else ""

    def key(self, provider: str) -> str:
        keys = self._config.get("schluessel")
        stored = ""
        if isinstance(keys, dict):
            stored = str(keys.get(provider) or "").strip()
        if stored:
            return stored
        return self._inherited(provider)

    @staticmethod
    def _inherited(provider: str) -> str:
        if provider not in INHERITED:
            return ""
        try:
            from app.core.keys import KeyManager

            return str(KeyManager().key_for(INHERITED[provider]) or "")
        except Exception:
            return ""

    def base(self, provider: str) -> str:
        bases = self._config.get("basis")
        stored = ""
        if isinstance(bases, dict):
            stored = str(bases.get(provider) or "").strip()
        return (stored or str(PROVIDERS[provider]["basis"])).rstrip("/")

    def model(self, provider: str, kind: str) -> str:
        models = self._config.get("modelle")
        stored = ""
        if isinstance(models, dict) and isinstance(models.get(provider), dict):
            stored = str(models[provider].get(kind) or "").strip()
        if stored:
            return stored
        meta = PROVIDERS[provider]
        return str(meta["standard_video" if kind == "video" else "standard_bild"])

    def _own_key(self, provider: str) -> str:
        keys = self._config.get("schluessel")
        if not isinstance(keys, dict):
            return ""
        return str(keys.get(provider) or "").strip()

    def size(self) -> str:
        value = str(self._config.get("groesse") or "")
        return value if value in SIZES else SIZES[0]

    def ready(self, provider: str) -> bool:
        meta = PROVIDERS.get(provider)
        if meta is None:
            return False
        if meta["auth"] == "api_key":
            return bool(self.key(provider))
        if meta["auth"] == "lokal":
            return bool(self.base(provider))
        return True

    def config(self) -> dict:
        active = self.active()
        return {
            "anbieter": active,
            "bereit": bool(active and self.ready(active)),
            "groesse": self.size(),
            "groessen": SIZES,
            "liste": [
                {
                    "id": key,
                    "label": meta["label"],
                    "auth": meta["auth"],
                    "docs": meta["docs"],
                    "hinweis": meta["hinweis"],
                    "bild_modelle": meta["bild_modelle"],
                    "video_modelle": meta["video_modelle"],
                    "video": bool(meta["video_modelle"]),
                    "bearbeiten": bool(meta["bearbeiten"]),
                    "geerbt": bool(
                        meta["auth"] == "api_key"
                        and not self._own_key(key)
                        and self._inherited(key)
                    ),
                    "basis": self.base(key),
                    "verbunden": self.ready(key),
                    "modell_bild": self.model(key, "bild"),
                    "modell_video": self.model(key, "video"),
                }
                for key, meta in PROVIDERS.items()
            ],
            "galerie": self.gallery(),
        }

    def connect(
        self,
        provider: str,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        video_model: str = "",
        size: str = "",
    ) -> dict:
        if provider not in PROVIDERS:
            raise StudioError("Diesen Anbieter kennt Jon nicht.")
        meta = PROVIDERS[provider]
        if meta["auth"] == "api_key" and not (api_key.strip() or self.key(provider)):
            raise StudioError(f"Für {meta['label']} fehlt noch der API-Schlüssel.")
        if meta["auth"] == "lokal" and not (base_url.strip() or self.base(provider)):
            raise StudioError("Trag die Adresse deines Bilder-Servers ein.")
        with self._lock:
            self._config["anbieter"] = provider
            if api_key.strip():
                keys = self._config.setdefault("schluessel", {})
                keys[provider] = api_key.strip()
            if base_url.strip():
                bases = self._config.setdefault("basis", {})
                bases[provider] = base_url.strip().rstrip("/")
            if model.strip() or video_model.strip():
                models = self._config.setdefault("modelle", {})
                entry = models.setdefault(provider, {})
                if model.strip():
                    entry["bild"] = model.strip()
                if video_model.strip():
                    entry["video"] = video_model.strip()
            if size in SIZES:
                self._config["groesse"] = size
            self._save()
        return self.config()

    def disconnect(self, provider: str) -> dict:
        with self._lock:
            keys = self._config.get("schluessel")
            if isinstance(keys, dict):
                keys.pop(provider, None)
            if self._config.get("anbieter") == provider:
                self._config["anbieter"] = ""
            self._save()
        return self.config()

    def gallery(self) -> list[dict]:
        return list(self._gallery)

    def delete(self, entry_id: str) -> dict:
        with self._lock:
            entry = next((e for e in self._gallery if e.get("id") == entry_id), None)
            if entry is None:
                raise StudioError("Dieses Werk gibt es nicht mehr.")
            self._gallery = [e for e in self._gallery if e.get("id") != entry_id]
            self._save()
        try:
            (STUDIO_DIR / str(entry.get("datei"))).unlink(missing_ok=True)
        except Exception:
            pass
        return {"geloescht": entry_id}

    def file(self, name: str):
        if not SAFE_NAME.match(name):
            raise StudioError("Ungültiger Dateiname.")
        path = STUDIO_DIR / name
        if not path.is_file():
            raise StudioError("Datei nicht gefunden.")
        return path

    def _store(
        self,
        data: bytes,
        mime: str,
        prompt: str,
        provider: str,
        model: str,
        kind: str,
        seconds: float,
        source: str = "",
    ) -> dict:
        STUDIO_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        name = f"{stamp}-{uuid.uuid4().hex[:6]}.{_extension(mime, source)}"
        atomic_write_bytes((STUDIO_DIR / name), data)
        entry = {
            "id": uuid.uuid4().hex,
            "datei": name,
            "art": kind,
            "prompt": prompt,
            "anbieter": provider,
            "anbieter_label": PROVIDERS[provider]["label"],
            "modell": model,
            "mime": mime.split(";")[0].strip() or "image/png",
            "groesse_bytes": len(data),
            "dauer_s": round(seconds, 1),
            "erstellt": time.time(),
        }
        with self._lock:
            self._gallery.insert(0, entry)
            dropped = self._gallery[MAX_GALLERY:]
            self._gallery = self._gallery[:MAX_GALLERY]
            self._save()
        for old in dropped:
            try:
                (STUDIO_DIR / str(old.get("datei"))).unlink(missing_ok=True)
            except Exception:
                pass
        return entry

    async def generate(
        self,
        prompt: str,
        kind: str = "bild",
        model: str = "",
        size: str = "",
        negative: str = "",
        provider: str = "",
        image: str = "",
    ) -> dict:
        prompt = prompt.strip()
        if not prompt:
            raise StudioError("Beschreibe zuerst, was Jon erstellen soll.")
        name = (provider or self.active()).strip().lower()
        meta = PROVIDERS.get(name)
        if meta is None:
            raise StudioError("Richte zuerst einen Anbieter ein.")
        kind = "video" if kind == "video" else "bild"
        if kind == "video" and not meta["video_modelle"]:
            raise StudioError(f"{meta['label']} erzeugt nur Bilder, keine Videos.")
        if not self.ready(name):
            raise StudioError(f"Für {meta['label']} fehlt noch der Zugang.")
        vorlage = self._vorlage(image)
        if vorlage and not meta["bearbeiten"]:
            raise StudioError(
                f"{meta['label']} kann keine Vorlage bearbeiten — wähle einen "
                "Anbieter, der Bilder bearbeitet."
            )
        if vorlage and kind == "video":
            raise StudioError("Eine Vorlage gibt es nur für Bilder.")
        chosen = model.strip() or self.model(name, kind)
        width, height = self._dimensions(size or self.size())
        started = time.time()
        handler = getattr(self, f"_{name}")
        data, mime, source = await handler(
            prompt, kind, chosen, width, height, negative.strip(), self.key(name), vorlage
        )
        if not data:
            raise StudioError("Der Anbieter hat keine Datei zurückgegeben.")
        return self._store(
            data, mime, prompt, name, chosen, kind, time.time() - started, source
        )

    def _vorlage(self, image: str) -> tuple[bytes, str] | None:
        raw = (image or "").strip()
        if not raw:
            return None
        if raw.startswith("data:"):
            head, _, payload = raw.partition(",")
            mime = head[5:].split(";")[0].strip() or "image/png"
            try:
                return base64.b64decode(payload), mime
            except Exception as exc:
                raise StudioError(f"Die Vorlage ist unlesbar: {exc}") from exc
        entry = next((e for e in self._gallery if e.get("id") == raw), None)
        if entry is None:
            raise StudioError("Diese Vorlage gibt es nicht mehr.")
        path = STUDIO_DIR / str(entry.get("datei"))
        if not path.is_file():
            raise StudioError("Die Datei der Vorlage fehlt.")
        return path.read_bytes(), str(entry.get("mime") or "image/png")

    @staticmethod
    def _nvidia_side(value: int) -> int:
        return min(NVIDIA_SIDES, key=lambda side: abs(side - value))

    @staticmethod
    def _nvidia_aspect(width: int, height: int) -> str:
        ratio = width / max(1, height)
        return min(NVIDIA_RATIOS, key=lambda item: abs(item[1] - ratio))[0]

    @staticmethod
    def _dimensions(size: str) -> tuple[int, int]:
        try:
            width, height = size.lower().split("x")
            return max(256, int(width)), max(256, int(height))
        except Exception:
            return 1024, 1024

    @staticmethod
    def _client(timeout: float = 180.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=15.0), follow_redirects=True
        )

    @staticmethod
    def _fail(response: httpx.Response, label: str) -> None:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                if isinstance(body.get("error"), dict):
                    detail = str(body["error"].get("message") or "")
                else:
                    detail = str(
                        body.get("error")
                        or body.get("detail")
                        or body.get("message")
                        or body.get("errors")
                        or ""
                    )
        except Exception:
            detail = response.text[:300]
        raise StudioError(
            f"{label} meldet {response.status_code}: {detail or 'unbekannter Fehler'}"
        )

    @staticmethod
    async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[bytes, str, str]:
        response = await client.get(url)
        if response.status_code >= 400:
            StudioService._fail(response, "Der Download")
        return (
            response.content,
            response.headers.get("content-type", "application/octet-stream"),
            url,
        )

    async def _pollinations(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        params = {
            "width": str(width),
            "height": str(height),
            "nologo": "true",
            "seed": str(int(time.time()) % 100000),
        }
        if model:
            params["model"] = model
        if negative:
            params["negative"] = negative
        url = f"https://image.pollinations.ai/prompt/{quote(prompt[:900], safe='')}"
        async with self._client(240.0) as client:
            response = await client.get(url, params=params)
            if response.status_code >= 400:
                self._fail(response, "Pollinations")
            mime = response.headers.get("content-type", "image/jpeg")
            return response.content, mime, url

    async def _together(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "width": width,
            "height": height,
            "n": 1,
            "response_format": "b64_json",
        }
        if "schnell" in model.lower():
            payload["steps"] = 4
        if negative:
            payload["negative_prompt"] = negative
        async with self._client() as client:
            response = await client.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
            if response.status_code >= 400:
                self._fail(response, "Together AI")
            item = (response.json().get("data") or [{}])[0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"]), "image/png", ""
            if item.get("url"):
                return await self._fetch(client, str(item["url"]))
        raise StudioError("Together AI hat kein Bild geliefert.")

    async def _openai(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        text = prompt if not negative else f"{prompt}\n\nVermeide: {negative}"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": text,
            "n": 1,
            "size": self._openai_size(width, height, model),
        }
        if not model.startswith("gpt-image"):
            payload["response_format"] = "b64_json"
        async with self._client() as client:
            if vorlage:
                data, mime = vorlage
                form = {
                    "model": str(payload["model"]),
                    "prompt": str(payload["prompt"]),
                    "size": str(payload["size"]),
                }
                response = await client.post(
                    "https://api.openai.com/v1/images/edits",
                    headers={"Authorization": f"Bearer {key}"},
                    data=form,
                    files={"image": (f"vorlage.{_extension(mime)}", data, mime)},
                )
            else:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={"Authorization": f"Bearer {key}"},
                    json=payload,
                )
            if response.status_code >= 400:
                self._fail(response, "OpenAI")
            item = (response.json().get("data") or [{}])[0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"]), "image/png", ""
            if item.get("url"):
                return await self._fetch(client, str(item["url"]))
        raise StudioError("OpenAI hat kein Bild geliefert.")

    @staticmethod
    def _openai_size(width: int, height: int, model: str) -> str:
        wide = width > height
        tall = height > width
        if model.startswith("dall-e-3"):
            return "1792x1024" if wide else "1024x1792" if tall else "1024x1024"
        return "1536x1024" if wide else "1024x1536" if tall else "1024x1024"

    async def _gemini(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        base = "https://generativelanguage.googleapis.com/v1beta/models"
        text = prompt if not negative else f"{prompt}\n\nVermeide: {negative}"
        async with self._client() as client:
            if model.startswith("imagen"):
                if vorlage:
                    raise StudioError(
                        "Imagen bearbeitet keine Vorlagen — nimm gemini-2.5-flash-image."
                    )
                response = await client.post(
                    f"{base}/{model}:predict",
                    headers={"x-goog-api-key": key},
                    json={
                        "instances": [{"prompt": text}],
                        "parameters": {
                            "sampleCount": 1,
                            "aspectRatio": self._aspect(width, height),
                        },
                    },
                )
                if response.status_code >= 400:
                    self._fail(response, "Google Imagen")
                for item in response.json().get("predictions") or []:
                    raw = item.get("bytesBase64Encoded")
                    if raw:
                        mime = str(item.get("mimeType") or "image/png")
                        return base64.b64decode(raw), mime, ""
                raise StudioError("Google Imagen hat kein Bild geliefert.")
            teile: list[dict[str, Any]] = []
            if vorlage:
                data, mime = vorlage
                teile.append(
                    {
                        "inlineData": {
                            "mimeType": mime,
                            "data": base64.b64encode(data).decode(),
                        }
                    }
                )
            teile.append({"text": text})
            response = await client.post(
                f"{base}/{model}:generateContent",
                headers={"x-goog-api-key": key},
                json={
                    "contents": [{"parts": teile}],
                    "generationConfig": {"responseModalities": ["IMAGE"]},
                },
            )
            if response.status_code >= 400:
                self._fail(response, "Google Gemini")
            for candidate in response.json().get("candidates") or []:
                parts = (candidate.get("content") or {}).get("parts") or []
                for part in parts:
                    inline = part.get("inlineData") or part.get("inline_data") or {}
                    if inline.get("data"):
                        mime = str(
                            inline.get("mimeType")
                            or inline.get("mime_type")
                            or "image/png"
                        )
                        return base64.b64decode(inline["data"]), mime, ""
        raise StudioError("Google Gemini hat kein Bild geliefert.")

    @staticmethod
    def _aspect(width: int, height: int) -> str:
        ratio = width / max(1, height)
        if ratio > 1.55:
            return "16:9"
        if ratio > 1.15:
            return "4:3"
        if ratio < 0.65:
            return "9:16"
        if ratio < 0.87:
            return "3:4"
        return "1:1"

    async def _stability(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        endpoint = "core"
        form: dict[str, str] = {
            "prompt": prompt,
            "output_format": "png",
            "aspect_ratio": self._aspect(width, height),
        }
        if model.startswith("ultra"):
            endpoint = "ultra"
        elif model.startswith("sd3"):
            endpoint = "sd3"
            form["model"] = model
        if negative:
            form["negative_prompt"] = negative
        url = f"https://api.stability.ai/v2beta/stable-image/generate/{endpoint}"
        async with self._client() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Accept": "image/*"},
                data=form,
                files={"none": ("", b"")},
            )
            if response.status_code >= 400:
                self._fail(response, "Stability AI")
            mime = response.headers.get("content-type", "image/png")
            return response.content, mime, ""

    async def _replicate(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        payload: dict[str, Any] = {"prompt": prompt}
        if kind == "bild":
            payload["aspect_ratio"] = self._aspect(width, height)
            payload["output_format"] = "png"
        if negative:
            payload["negative_prompt"] = negative
        if vorlage:
            data, mime = vorlage
            payload["image"] = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            payload["input_image"] = payload["image"]
            payload.pop("aspect_ratio", None)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }
        slug = model.strip().strip("/")
        async with self._client(600.0) as client:
            response = await client.post(
                f"https://api.replicate.com/v1/models/{slug}/predictions",
                headers=headers,
                json={"input": payload},
            )
            if response.status_code >= 400:
                self._fail(response, "Replicate")
            data = response.json()
            for _ in range(150):
                status = str(data.get("status") or "")
                if status == "succeeded":
                    break
                if status in ("failed", "canceled"):
                    reason = data.get("error") or status
                    raise StudioError(f"Replicate hat abgebrochen: {reason}")
                poll_url = str((data.get("urls") or {}).get("get") or "")
                if not poll_url:
                    break
                await asyncio.sleep(2.0)
                poll = await client.get(
                    poll_url, headers={"Authorization": f"Bearer {key}"}
                )
                if poll.status_code >= 400:
                    self._fail(poll, "Replicate")
                data = poll.json()
            output = data.get("output")
            url = ""
            if isinstance(output, str):
                url = output
            elif isinstance(output, list) and output:
                url = str(output[0])
            elif isinstance(output, dict):
                url = str(output.get("video") or output.get("image") or "")
            if not url:
                raise StudioError("Replicate war zu langsam oder hat nichts geliefert.")
            return await self._fetch(client, url)

    async def _fal(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        payload: dict[str, Any] = {"prompt": prompt}
        if kind == "bild":
            payload["image_size"] = {"width": width, "height": height}
        if negative:
            payload["negative_prompt"] = negative
        if vorlage:
            data, mime = vorlage
            roh = base64.b64encode(data).decode()
            payload["image_url"] = f"data:{mime};base64,{roh}"
            payload.pop("image_size", None)
        async with self._client(600.0) as client:
            response = await client.post(
                f"https://fal.run/{model.strip().strip('/')}",
                headers={
                    "Authorization": f"Key {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code >= 400:
                self._fail(response, "fal.ai")
            data = response.json()
            url = ""
            images = data.get("images")
            if isinstance(images, list) and images:
                first = images[0]
                url = str(first.get("url") if isinstance(first, dict) else first)
            video = data.get("video")
            if isinstance(video, dict) and video.get("url"):
                url = str(video["url"])
            elif isinstance(video, str) and video:
                url = video
            if not url:
                raise StudioError("fal.ai hat keine Datei geliefert.")
            return await self._fetch(client, url)

    async def _nvidia(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        slug = model.strip().strip("/")
        payload: dict[str, Any] = {"prompt": prompt}
        if negative:
            payload["negative_prompt"] = negative
        klassisch = "flux.1-schnell" in slug or "flux.1-dev" in slug
        if klassisch and not vorlage:
            payload["width"] = self._nvidia_side(width)
            payload["height"] = self._nvidia_side(height)
            payload["steps"] = 4 if "schnell" in slug else 30
            payload["seed"] = int(time.time()) % 1000000
        else:
            payload["aspect_ratio"] = (
                "match_input_image" if vorlage else self._nvidia_aspect(width, height)
            )
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "NVCF-POLL-SECONDS": "60",
        }
        async with self._client(420.0) as client:
            if vorlage:
                data, mime = vorlage
                asset = await self._nvidia_asset(client, key, data, mime)
                payload["image"] = f"data:{mime};example_id,{asset}"
                headers["NVCF-INPUT-ASSET-REFERENCES"] = asset
            response = await client.post(
                f"https://ai.api.nvidia.com/v1/genai/{slug}",
                headers=headers,
                json=payload,
            )
            response = await self._nvidia_wait(client, response, key)
            if response.status_code >= 400:
                if vorlage and response.status_code in (422, 500):
                    raise StudioError(
                        "NVIDIA nimmt für dieses Modell gerade keine eigenen Bilder "
                        f"an (Antwort {response.status_code}). Text zu Bild geht, für "
                        "das Bearbeiten nimm so lange einen anderen Anbieter."
                    )
                if response.status_code in (502, 503, 504):
                    raise StudioError(
                        f"NVIDIA bedient {slug} gerade nicht (Antwort "
                        f"{response.status_code}). Probier ein anderes Modell, "
                        "z.B. black-forest-labs/flux.2-klein-4b."
                    )
                self._fail(response, "NVIDIA")
            return self._nvidia_bytes(response)

    async def _nvidia_asset(
        self, client: httpx.AsyncClient, key: str, data: bytes, mime: str
    ) -> str:
        response = await client.post(
            "https://api.nvcf.nvidia.com/v2/nvcf/assets",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"contentType": mime, "description": "jon-studio"},
        )
        if response.status_code >= 400:
            self._fail(response, "NVIDIA")
        info = response.json()
        upload = await client.put(
            str(info["uploadUrl"]),
            headers={
                "Content-Type": mime,
                "x-amz-meta-nvcf-asset-description": "jon-studio",
            },
            content=data,
        )
        if upload.status_code >= 400:
            self._fail(upload, "Der Upload zu NVIDIA")
        return str(info["assetId"])

    async def _nvidia_wait(
        self, client: httpx.AsyncClient, response: httpx.Response, key: str
    ) -> httpx.Response:
        request_id = response.headers.get("nvcf-reqid", "")
        for _ in range(90):
            if response.status_code != 202 or not request_id:
                return response
            await asyncio.sleep(3.0)
            response = await client.get(
                f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{request_id}",
                headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            )
        return response

    @staticmethod
    def _nvidia_bytes(response: httpx.Response) -> tuple[bytes, str, str]:
        data = response.json()
        raw = ""
        artifacts = data.get("artifacts")
        if isinstance(artifacts, list) and artifacts:
            first = artifacts[0]
            raw = str(first.get("base64") or first.get("b64_json") or "")
        if not raw:
            raw = str(data.get("image") or data.get("b64_json") or "")
        if not raw:
            raise StudioError("NVIDIA hat kein Bild geliefert.")
        if raw.startswith("data:"):
            raw = raw.partition(",")[2]
        blob = base64.b64decode(raw)
        mime = "image/png" if blob[:4] == PNG_MAGIC else "image/jpeg"
        return blob, mime, ""

    async def _lokal(
        self, prompt, kind, model, width, height, negative, key, vorlage
    ) -> tuple[bytes, str, str]:
        base = self.base("lokal")
        payload: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative,
            "width": width,
            "height": height,
            "steps": 28,
            "cfg_scale": 6.5,
        }
        if model:
            payload["override_settings"] = {"sd_model_checkpoint": model}
        weg = "txt2img"
        if vorlage:
            data, mime = vorlage
            payload["init_images"] = [base64.b64encode(data).decode()]
            payload["denoising_strength"] = 0.62
            weg = "img2img"
        async with self._client(600.0) as client:
            try:
                response = await client.post(f"{base}/sdapi/v1/{weg}", json=payload)
            except httpx.HTTPError as exc:
                raise StudioError(
                    f"Kein Bilder-Server unter {base} erreichbar: {exc}"
                ) from exc
            if response.status_code >= 400:
                self._fail(response, "Dein lokaler Bilder-Server")
            images = response.json().get("images") or []
            if not images:
                raise StudioError("Dein lokaler Bilder-Server hat nichts geliefert.")
            raw = str(images[0]).split(",")[-1]
            return base64.b64decode(raw), "image/png", ""


_service: StudioService | None = None


def get_studio_service() -> StudioService:
    global _service
    if _service is None:
        _service = StudioService()
    return _service
