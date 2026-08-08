from __future__ import annotations

import asyncio
import logging
import re
import time

import numpy as np

from app.services.phone.audio import (
    RATE_NET,
    RATE_STT,
    SAMPLES_PER_FRAME,
    VoiceGate,
    decode_to_pcm,
    resample,
    to_float,
)
from app.services.phone.rtp import RtpSession
from app.services.phone.stack import CallHandle

log = logging.getLogger("jon.phone")

BARGE_IN_WORDS = (
    "warte",
    "stopp",
    "stop",
    "moment",
    "halt",
    "sekunde",
    "kurz",
    "hoer auf",
    "höre auf",
    "hör auf",
)
GOODBYE_WORDS = (
    "tschüss",
    "tschuess",
    "auf wiederhören",
    "auf wiederhoeren",
    "bis dann",
    "leg auf",
    "beende den anruf",
    "wir hören uns",
    "ciao",
    "bye",
    "danke das wars",
    "das war's",
)
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
DEAF_NOTICE = (
    "Ich hoere dich gerade nicht. Bei mir kommt kein Ton an. "
    "Wahrscheinlich fehlt die Firewallregel fuer die Sprachpakete."
)
_whisper_model = None
_whisper_error = ""


def load_recognizer(size: str = "base") -> object | None:
    global _whisper_model, _whisper_error
    if _whisper_model is not None:
        return _whisper_model
    if _whisper_error:
        return None
    try:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
        _whisper_error = ""
    except ImportError:
        _whisper_error = (
            "faster-whisper ist nicht installiert. Ohne das Paket kann Jon am "
            "Telefon nicht zuhoeren: pip install faster-whisper"
        )
    except Exception as exc:
        _whisper_error = f"Spracherkennung konnte nicht geladen werden: {exc}"
    return _whisper_model


def recognizer_error() -> str:
    return _whisper_error


def transcribe(pcm8k: np.ndarray, language: str = "de") -> str:
    model = load_recognizer()
    if model is None:
        return ""
    if pcm8k.size < SAMPLES_PER_FRAME * 4:
        return ""
    audio = to_float(resample(pcm8k, RATE_NET, RATE_STT))
    try:
        segments, _info = model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:
        log.warning("Spracherkennung fehlgeschlagen: %s", exc)
        return ""


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENTENCE_END.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def wants_goodbye(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in GOODBYE_WORDS)


def wants_pause(text: str) -> bool:
    lowered = text.lower().strip()
    return any(lowered.startswith(word) or word in lowered for word in BARGE_IN_WORDS)


class Speaker:
    def __init__(self, rtp: RtpSession, voice: str, rate: str = "+10%") -> None:
        self._rtp = rtp
        self._voice = voice
        self._rate = rate
        self._stop = asyncio.Event()
        self._speaking = False

    @property
    def speaking(self) -> bool:
        return self._speaking

    def interrupt(self) -> None:
        self._stop.set()

    async def say(self, text: str) -> bool:
        from app.services.voice_service import synthesize_speech

        clean = text.strip()
        if not clean:
            return True
        self._stop.clear()
        self._speaking = True
        finished = True
        try:
            for sentence in split_sentences(clean):
                if self._stop.is_set():
                    finished = False
                    break
                try:
                    mp3 = await synthesize_speech(
                        sentence, voice=self._voice, rate=self._rate, volume="+0%"
                    )
                except Exception as exc:
                    log.warning("Sprachausgabe fehlgeschlagen: %s", exc)
                    return False
                if not mp3:
                    continue
                pcm = await asyncio.to_thread(decode_to_pcm, mp3, RATE_NET)
                if not await self._rtp.play(pcm, self._stop):
                    finished = False
                    break
        finally:
            self._speaking = False
        return finished


class PhoneConversation:
    def __init__(
        self,
        call: CallHandle,
        opening: str,
        persona: str,
        voice: str,
        language: str = "de",
        max_seconds: int = 600,
        on_turn=None,
    ) -> None:
        self.call = call
        self.opening = opening
        self.persona = persona
        self.language = language
        self.max_seconds = max_seconds
        self.transcript: list[dict] = []
        self._speaker = Speaker(call.rtp, voice)
        self._gate = VoiceGate()
        self._on_turn = on_turn
        self._history: list[tuple[str, str]] = []

    def _log(self, who: str, text: str) -> None:
        entry = {
            "who": who,
            "text": text,
            "at": time.strftime("%H:%M:%S"),
        }
        self.transcript.append(entry)
        if self._on_turn:
            try:
                self._on_turn(entry)
            except Exception:
                pass

    async def run(self) -> list[dict]:
        started = time.monotonic()
        await self.call.rtp.play_silence(0.35)
        self.call.rtp.drain()
        self._gate.reset()
        if self.opening:
            self._log("jon", self.opening)
            await self._speaker.say(self.opening)
        idle_since = time.monotonic()
        deaf_warned = False
        while self.call.active:
            if time.monotonic() - started > self.max_seconds:
                await self._speaker.say("Ich lass dich weitermachen. Bis später!")
                break
            frame = await self.call.rtp.read_frame(timeout=0.5)
            if frame is None:
                if self.call.rtp.last_packet_at and (
                    time.monotonic() - self.call.rtp.last_packet_at > 12.0
                ):
                    self.call.reason = "Verbindung abgebrochen"
                    break
                if (
                    not deaf_warned
                    and self.call.rtp.packets_received == 0
                    and time.monotonic() - started > 6.0
                ):
                    deaf_warned = True
                    self._log("jon", DEAF_NOTICE)
                    await self._speaker.say(DEAF_NOTICE)
                    idle_since = time.monotonic()
                    continue
                if time.monotonic() - idle_since > 25.0:
                    await self._speaker.say("Bist du noch dran?")
                    idle_since = time.monotonic()
                continue
            speech = self._gate.feed(frame)
            if speech is None:
                continue
            idle_since = time.monotonic()
            text = await asyncio.to_thread(transcribe, speech, self.language)
            if not text or len(text.strip()) < 2:
                continue
            self._log("user", text)
            if wants_goodbye(text):
                await self._speaker.say("Alles klar, bis später!")
                break
            answer = await self._answer(text)
            if not answer:
                continue
            self._log("jon", answer)
            await self._speak_with_barge_in(answer)
        return self.transcript

    async def _speak_with_barge_in(self, text: str) -> None:
        speaking = asyncio.create_task(self._speaker.say(text))
        listener = asyncio.create_task(self._listen_for_interrupt())
        done, pending = await asyncio.wait(
            {speaking, listener}, return_when=asyncio.FIRST_COMPLETED
        )
        if listener in done and not speaking.done():
            self._speaker.interrupt()
        for task in pending:
            task.cancel()
        for task in pending:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        if listener in done:
            try:
                interrupted = listener.result()
            except Exception:
                interrupted = ""
            if interrupted:
                self._log("user", interrupted)
                if wants_pause(interrupted):
                    self._log("jon", "Klar.")
                    await self._speaker.say("Klar.")
                    return
                answer = await self._answer(interrupted)
                if answer:
                    self._log("jon", answer)
                    await self._speaker.say(answer)
        self._gate.reset()
        self.call.rtp.drain()

    async def _listen_for_interrupt(self) -> str:
        gate = VoiceGate(start_frames=6, end_frames=24)
        gate._noise = max(self._gate.noise_floor, 260.0)
        while self.call.active and self._speaker.speaking:
            frame = await self.call.rtp.read_frame(timeout=0.4)
            if frame is None:
                continue
            speech = gate.feed(frame)
            if speech is None:
                continue
            text = await asyncio.to_thread(transcribe, speech, self.language)
            if text and len(text.strip()) > 2:
                return text
        return ""

    async def _answer(self, text: str) -> str:
        from app.services import llm
        from app.services.settings_service import get_settings_service

        provider, model = get_settings_service().selection()
        history = "\n".join(f"{who}: {said}" for who, said in self._history[-8:])
        prompt = (
            f"{history}\nFelix sagt am Telefon: {text}" if history else
            f"Felix sagt am Telefon: {text}"
        )
        try:
            answer = await llm.complete(
                self.persona,
                prompt,
                provider=provider or None,
                model=model or None,
                max_tokens=220,
                temperature=0.8,
            )
        except Exception as exc:
            log.warning("LLM am Telefon nicht erreichbar: %s", exc)
            return "Ich komme gerade nicht an mein Sprachmodell. Ich melde mich nochmal."
        answer = _phone_style(answer)
        self._history.append(("Felix", text))
        self._history.append(("Jon", answer))
        return answer


def _phone_style(text: str) -> str:
    clean = str(text or "").strip()
    clean = re.sub(r"```.*?```", " ", clean, flags=re.S)
    clean = re.sub(r"[*_#`>|]+", "", clean)
    clean = re.sub(r"^\s*[-•]\s*", "", clean, flags=re.M)
    clean = re.sub(r"\s*\n\s*", " ", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    sentences = split_sentences(clean)
    if len(sentences) > 4:
        clean = " ".join(sentences[:4])
    return clean[:600]
