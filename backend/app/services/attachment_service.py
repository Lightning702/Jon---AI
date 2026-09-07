from __future__ import annotations

import base64
import io
import time

from app.core.config import DATA_DIR, get_settings
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.registry import get_registry
from app.services.screen_service import VISION_DEFAULTS
from app.services.settings_service import get_settings_service

MAX_BYTES = 15_000_000
MAX_TEXT = 20_000
ANHANG_ORDNER = DATA_DIR / "anhaenge"

IMAGE_PROMPT = (
    "Der Nutzer hat dieses Bild in den Chat gezogen. Beschreibe praezise und "
    "detailliert auf Deutsch, was darauf zu sehen ist: Inhalt, Text (woertlich "
    "zitieren, falls lesbar), Zahlen, Diagramme, Fehlermeldungen, Layout. "
    "Keine Einleitung, direkt die Beschreibung."
)


class AttachmentService:
    async def extract(
        self,
        name: str,
        mime: str,
        data_b64: str,
        provider_name: str | None = None,
    ) -> dict:
        try:
            raw = base64.b64decode(data_b64)
        except Exception:
            return {"error": "Ungueltige Daten"}
        if len(raw) > MAX_BYTES:
            return {"error": "Datei zu gross (max 15 MB)"}
        lower = name.lower()
        pfad = self._sichern(name, raw)
        if mime == "application/pdf" or lower.endswith(".pdf"):
            ergebnis = self._extract_pdf(name, raw)
        elif mime.startswith("image/"):
            ergebnis = await self._describe_image(name, mime, raw, provider_name)
        else:
            ergebnis = self._extract_text(name, raw)
        if pfad and "error" not in ergebnis:
            ergebnis["pfad"] = pfad
        return ergebnis

    def _sichern(self, name: str, raw: bytes) -> str:
        sauber = "".join(
            zeichen if zeichen.isalnum() or zeichen in "._- " else "_"
            for zeichen in name.strip()
        ).strip(" .")[:80] or "anhang"
        try:
            ANHANG_ORDNER.mkdir(parents=True, exist_ok=True)
            ziel = ANHANG_ORDNER / f"{time.strftime('%Y%m%d-%H%M%S')}-{sauber}"
            zaehler = 1
            while ziel.exists():
                ziel = ANHANG_ORDNER / f"{time.strftime('%Y%m%d-%H%M%S')}-{zaehler}-{sauber}"
                zaehler += 1
            ziel.write_bytes(raw)
            self._aufraeumen()
            return str(ziel)
        except OSError:
            return ""

    def _aufraeumen(self) -> None:
        try:
            dateien = sorted(
                (datei for datei in ANHANG_ORDNER.glob("*") if datei.is_file()),
                key=lambda datei: datei.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return
        for alt in dateien[60:]:
            try:
                alt.unlink()
            except OSError:
                continue

    def _extract_pdf(self, name: str, raw: bytes) -> dict:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            total = len(reader.pages)
            text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages[:60]
            )
        except Exception as exc:
            return {"error": f"PDF konnte nicht gelesen werden: {exc}"}
        return {
            "kind": "pdf",
            "name": name,
            "pages": total,
            "content": text[:MAX_TEXT],
        }

    def _extract_text(self, name: str, raw: bytes) -> dict:
        sample = raw[:2000]
        if b"\x00" in sample:
            return {"error": f"Dateityp von {name} wird nicht unterstuetzt"}
        text = raw[:500_000].decode("utf-8", errors="replace")
        return {"kind": "text", "name": name, "content": text[:MAX_TEXT]}

    async def _describe_image(
        self, name: str, mime: str, raw: bytes, provider_name: str | None
    ) -> dict:
        settings = get_settings()
        user = get_settings_service()
        saved_provider, saved_model = user.selection()
        provider_name = provider_name or saved_provider or settings.default_provider
        vision_model = (
            user.get().get("vision_model")
            or VISION_DEFAULTS.get(provider_name)
            or saved_model
            or settings.jon_model
        )
        provider = get_registry().all().get(provider_name)
        if not isinstance(provider, OpenAICompatibleProvider):
            return {
                "error": "Bildanalyse braucht einen OpenAI-kompatiblen Anbieter "
                "mit Vision-Modell (z.B. NVIDIA, OpenAI, OpenRouter)."
            }
        if not provider.available():
            return {"error": f"Kein API-Key fuer {provider_name}."}
        encoded = base64.b64encode(raw).decode("ascii")
        data_url = f"data:{mime};base64,{encoded}"
        try:
            text = await provider.describe_image(
                vision_model, data_url, IMAGE_PROMPT, max_tokens=800
            )
        except Exception as exc:
            return {"error": f"Bildanalyse fehlgeschlagen: {exc}"}
        return {"kind": "image", "name": name, "content": text.strip()[:MAX_TEXT]}


_service: AttachmentService | None = None


def get_attachment_service() -> AttachmentService:
    global _service
    if _service is None:
        _service = AttachmentService()
    return _service
