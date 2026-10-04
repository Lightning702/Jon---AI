from __future__ import annotations

import io
import json
import tempfile
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import speech_recognition as sr
from app.core.fehler import leise

_whisper_model = None
_whisper_failed = False


def _get_whisper():
    global _whisper_model, _whisper_failed
    if _whisper_model is not None or _whisper_failed:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel

        bundled = Path(__file__).resolve().parents[2] / "assets" / "models" / "whisper-base"
        _whisper_model = WhisperModel(str(bundled) if (bundled / "model.bin").is_file() else "base", device="cpu", compute_type="int8")
    except Exception:
        _whisper_failed = True
    return _whisper_model


GOOGLE_SPRACHE = "http://www.google.com/speech-api/v2/recognize"
GOOGLE_SCHLUESSEL = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"


def _google_rohdaten(data: bytes, language: str) -> str:
    with wave.open(io.BytesIO(data), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            return ""
        rate = wav.getframerate()
        pcm = wav.readframes(wav.getnframes())
    if not pcm:
        return ""
    query = urllib.parse.urlencode(
        {"client": "chromium", "lang": language, "key": GOOGLE_SCHLUESSEL, "pFilter": 0}
    )
    anfrage = urllib.request.Request(
        f"{GOOGLE_SPRACHE}?{query}",
        data=pcm,
        headers={"Content-Type": f"audio/l16; rate={rate};"},
    )
    with urllib.request.urlopen(anfrage, timeout=20) as antwort:
        text = antwort.read().decode("utf-8", errors="replace")
    for zeile in text.splitlines():
        if not zeile.strip():
            continue
        try:
            ergebnis = json.loads(zeile).get("result") or []
        except ValueError:
            continue
        for eintrag in ergebnis:
            for alternative in eintrag.get("alternative") or []:
                satz = str(alternative.get("transcript", "")).strip()
                if satz:
                    return satz[:1].upper() + satz[1:]
    return ""


class VoiceService:
    def __init__(self) -> None:
        self._recognizer = sr.Recognizer()

    def transcribe_wav(self, data: bytes, language: str = "de-DE") -> str:
        model = _get_whisper()
        if model is not None:
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as handle:
                    handle.write(data)
                    temp_path = handle.name
                try:
                    segments, _info = model.transcribe(
                        temp_path, language=language.split("-")[0], beam_size=2, initial_prompt=NAMEN
                    )
                    text = " ".join(s.text.strip() for s in segments).strip()
                    if text:
                        return text
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            except Exception as _fehler:
                leise(_fehler, "services/voice_service")
        try:
            return _google_rohdaten(data, language)
        except Exception as _fehler:
            leise(_fehler, "services/voice_service")
        with sr.AudioFile(io.BytesIO(data)) as source:
            audio = self._recognizer.record(source)
        try:
            return str(self._recognizer.recognize_google(audio, language=language))
        except Exception:
            return ""


NAMEN = "Jon, MiniJon, FelWorks."
JON_VOICE = "de-DE-ConradNeural"
EMIL_VOICE = "de-DE-KillianNeural"


async def synthesize_speech(
    text: str,
    voice: str = JON_VOICE,
    rate: str = "+8%",
    volume: str = "+45%",
    pitch: str = "+0Hz",
) -> bytes:
    import edge_tts

    clean = text.strip()
    if len(clean) > 80000:
        raise ValueError("Die Sprachausgabe unterstützt höchstens 80.000 Zeichen pro Auftrag.")
    if not clean:
        return b""
    communicate = edge_tts.Communicate(
        clean, voice, rate=rate, volume=volume, pitch=pitch
    )
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio" and chunk.get("data"):
            chunks.append(chunk["data"])
    return b"".join(chunks)
