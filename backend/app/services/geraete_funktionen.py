from __future__ import annotations

import asyncio
import base64
import contextvars
import io
import wave

HANDY_KONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar("jon_handy_id", default="")


async def audio_ausfuehren(anfrage: dict) -> dict:
    from app.services.voice_service import VoiceService, synthesize_speech

    try:
        if anfrage.get("op") == "audio-stt":
            text = str(anfrage.get("audio", ""))
            if not text or len(text) > 1_400_000:
                return {"ok": False, "fehler": "Aufnahme fehlt oder ist zu lang."}
            daten = base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)
            if len(daten) > 1_000_044:
                return {"ok": False, "fehler": "Aufnahme ist zu groß."}
            with wave.open(io.BytesIO(daten), "rb") as wav:
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 16000 or wav.getnframes() > 480000:
                    return {"ok": False, "fehler": "Erwartet wird höchstens 30 Sekunden WAV, mono, 16 kHz, 16 Bit."}
                if len(wav.readframes(wav.getnframes())) != wav.getnframes() * 2:
                    return {"ok": False, "fehler": "Aufnahme ist unvollständig."}
            erkannt = await asyncio.wait_for(asyncio.to_thread(VoiceService().transcribe_wav, daten, "de-DE"), 90)
            return {"ok": True, "text": erkannt}
        text = str(anfrage.get("text", "")).strip()
        if not text or len(text) > 1200:
            return {"ok": False, "fehler": "Sprachausgabe erwartet 1 bis 1200 Zeichen."}
        daten = await asyncio.wait_for(synthesize_speech(text), 60)
        if not daten or len(daten) > 2_000_000:
            return {"ok": False, "fehler": "Sprachausgabe ist nicht verfügbar."}
        return {"ok": True, "audio": base64.urlsafe_b64encode(daten).decode().rstrip("="), "mime": "audio/mpeg"}
    except (ValueError, wave.Error, EOFError):
        return {"ok": False, "fehler": "Ungültige Audiodaten."}
    except asyncio.TimeoutError:
        return {"ok": False, "fehler": "Der Sprachdienst antwortet nicht rechtzeitig."}
    except Exception:
        return {"ok": False, "fehler": "Sprachdienst auf dem Pi ist nicht verfügbar. Verbindung und Sprachkonfiguration prüfen."}
