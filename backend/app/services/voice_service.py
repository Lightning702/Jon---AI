from __future__ import annotations

import io
import tempfile
from pathlib import Path

import speech_recognition as sr

_whisper_model = None
_whisper_failed = False


def _get_whisper():
    global _whisper_model, _whisper_failed
    if _whisper_model is not None or _whisper_failed:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    except Exception:
        _whisper_failed = True
    return _whisper_model


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
                        temp_path, language=language.split("-")[0], beam_size=2
                    )
                    text = " ".join(s.text.strip() for s in segments).strip()
                    if text:
                        return text
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
        with sr.AudioFile(io.BytesIO(data)) as source:
            audio = self._recognizer.record(source)
        try:
            return str(self._recognizer.recognize_google(audio, language=language))
        except sr.UnknownValueError:
            return ""


async def synthesize_speech(text: str, voice: str = "de-DE-ConradNeural") -> bytes:
    import edge_tts

    clean = text.strip()[:1200]
    if not clean:
        return b""
    communicate = edge_tts.Communicate(clean, voice, rate="+8%")
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio" and chunk.get("data"):
            chunks.append(chunk["data"])
    return b"".join(chunks)
