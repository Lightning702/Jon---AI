from __future__ import annotations

import io

import speech_recognition as sr


class VoiceService:
    def __init__(self) -> None:
        self._recognizer = sr.Recognizer()

    def transcribe_wav(self, data: bytes, language: str = "de-DE") -> str:
        with sr.AudioFile(io.BytesIO(data)) as source:
            audio = self._recognizer.record(source)
        try:
            return str(self._recognizer.recognize_google(audio, language=language))
        except sr.UnknownValueError:
            return ""
