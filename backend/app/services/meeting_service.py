from __future__ import annotations

import json
import struct
import threading
import time
from datetime import datetime

SAMPLE_RATE = 16000
SEGMENT_SECONDS = 18
MIC_KEYWORDS = ("fifine",)


def _encode_wav(samples: bytes, rate: int = SAMPLE_RATE) -> bytes:
    data_len = len(samples)
    header = b"RIFF"
    header += struct.pack("<I", 36 + data_len)
    header += b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", data_len)
    return header + samples


def _float_to_pcm16(arr) -> bytes:
    import numpy as np

    clipped = np.clip(arr, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


class MeetingService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._threads: list[threading.Thread] = []
        self._buffers: dict[str, list] = {"sys": [], "mic": []}
        self._buf_lock = threading.Lock()
        self._transcript: list[str] = []
        self._started_at = 0.0
        self._mic_name = ""
        self._error = ""

    def _pick_mic(self):
        import soundcard as sc

        mics = sc.all_microphones(include_loopback=False)
        for mic in mics:
            if any(k in mic.name.lower() for k in MIC_KEYWORDS):
                return mic
        try:
            return sc.default_microphone()
        except Exception:
            return mics[0] if mics else None

    def _record(self, key: str, mic) -> None:
        try:
            with mic.recorder(samplerate=SAMPLE_RATE, channels=1) as rec:
                while self._running:
                    chunk = rec.record(numframes=SAMPLE_RATE // 2)
                    with self._buf_lock:
                        self._buffers[key].append(chunk)
        except Exception as exc:
            self._error = f"{key}: {exc}"

    def _mix_and_take(self):
        import numpy as np

        with self._buf_lock:
            sys_chunks = self._buffers["sys"]
            mic_chunks = self._buffers["mic"]
            self._buffers["sys"] = []
            self._buffers["mic"] = []
        sys_arr = (
            np.concatenate(sys_chunks).flatten()
            if sys_chunks
            else np.zeros(0, dtype="float32")
        )
        mic_arr = (
            np.concatenate(mic_chunks).flatten()
            if mic_chunks
            else np.zeros(0, dtype="float32")
        )
        if sys_arr.size == 0 and mic_arr.size == 0:
            return None
        length = max(sys_arr.size, mic_arr.size)
        if sys_arr.size < length:
            sys_arr = np.pad(sys_arr, (0, length - sys_arr.size))
        if mic_arr.size < length:
            mic_arr = np.pad(mic_arr, (0, length - mic_arr.size))
        mixed = np.clip(sys_arr + mic_arr, -1.0, 1.0)
        return mixed

    def _transcribe(self, mixed) -> None:
        import numpy as np

        if mixed is None or mixed.size < SAMPLE_RATE // 2:
            return
        if float(np.abs(mixed).max()) < 0.004:
            return
        wav = _encode_wav(_float_to_pcm16(mixed))
        try:
            from app.services.voice_service import VoiceService

            text = VoiceService().transcribe_wav(wav, "de-DE").strip()
        except Exception:
            text = ""
        if text:
            with self._lock:
                self._transcript.append(text)

    def _cutter(self) -> None:
        next_cut = time.time() + SEGMENT_SECONDS
        while self._running:
            time.sleep(0.5)
            if time.time() >= next_cut:
                next_cut = time.time() + SEGMENT_SECONDS
                self._transcribe(self._mix_and_take())

    def start(self) -> dict:
        with self._lock:
            if self._running:
                return {"error": "Es läuft schon eine Mitschrift."}
            try:
                import numpy  # noqa: F401
                import soundcard as sc
            except Exception as exc:
                return {
                    "error": "Für die Meeting-Mitschrift fehlt eine Bibliothek "
                    f"(pip install soundcard): {exc}"
                }
            try:
                speaker = sc.default_speaker()
                loop = sc.get_microphone(speaker.name, include_loopback=True)
            except Exception as exc:
                return {"error": f"System-Audio nicht verfügbar: {exc}"}
            mic = self._pick_mic()
            self._mic_name = mic.name if mic else "keins"
            self._buffers = {"sys": [], "mic": []}
            self._transcript = []
            self._error = ""
            self._running = True
            self._started_at = time.time()
            self._threads = [
                threading.Thread(target=self._record, args=("sys", loop), daemon=True),
                threading.Thread(target=self._cutter, daemon=True),
            ]
            if mic is not None:
                self._threads.insert(
                    1,
                    threading.Thread(
                        target=self._record, args=("mic", mic), daemon=True
                    ),
                )
            for t in self._threads:
                t.start()
            return {"running": True, "mikrofon": self._mic_name}

    def status(self) -> dict:
        with self._lock:
            if not self._running:
                return {"running": False}
            return {
                "running": True,
                "mikrofon": self._mic_name,
                "sekunden": int(time.time() - self._started_at),
                "segmente": len(self._transcript),
                "fehler": self._error,
            }

    async def stop(self, provider: str = "", model: str = "") -> dict:
        with self._lock:
            if not self._running:
                return {"error": "Es läuft gerade keine Mitschrift."}
            self._running = False
        for t in self._threads:
            t.join(timeout=2)
        self._transcribe(self._mix_and_take())
        with self._lock:
            transcript = "\n".join(self._transcript).strip()
        if not transcript:
            return {
                "error": "Ich habe nichts verstanden. Lief Ton über die Lautsprecher "
                "und war das richtige Mikrofon aktiv?"
            }
        return await self._summarize(transcript, provider, model)

    async def _summarize(self, transcript: str, provider: str, model: str) -> dict:
        from app.core.config import get_settings
        from app.services.llm import complete

        settings = get_settings()
        provider = provider or settings.default_provider
        model = model or settings.jon_model
        prompt = (
            "Du bekommst die Roh-Transkription eines Meetings. Erstelle daraus ein "
            "sauberes JSON-Objekt mit den Feldern: \"zusammenfassung\" (5-8 knappe "
            "Sätze zu Themen und Entscheidungen) und \"todos\" (Liste von Objekten "
            "mit \"titel\" und optional \"datum\" im Format YYYY-MM-DD, nur wenn im "
            "Text ein konkreter Termin genannt wurde). Nur echte Aufgaben aus dem "
            "Text, nichts erfinden. Antworte NUR mit dem JSON."
        )
        try:
            raw = await complete(
                prompt,
                transcript[:12000],
                provider=provider,
                model=model,
                max_tokens=1200,
                temperature=0.3,
            )
        except Exception as exc:
            return {
                "zusammenfassung": "",
                "todos": [],
                "transkript": transcript,
                "error": f"Zusammenfassung fehlgeschlagen: {exc}",
            }
        summary, todos = self._parse(raw)
        added = []
        if todos:
            from app.services.calendar_service import get_calendar_service

            service = get_calendar_service()
            for todo in todos:
                title = str(todo.get("titel", "")).strip()
                if not title:
                    continue
                try:
                    service.add(
                        title=title,
                        day=str(todo.get("datum") or "heute"),
                        kind="task",
                        note="Aus Meeting-Mitschrift",
                    )
                    added.append(title)
                except Exception:
                    continue
        return {
            "zusammenfassung": summary,
            "todos": added,
            "transkript": transcript,
        }

    def _parse(self, raw: str) -> tuple[str, list]:
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(text[start : end + 1])
                return str(obj.get("zusammenfassung", "")).strip(), obj.get(
                    "todos", []
                ) or []
            except Exception:
                pass
        return text, []


_service: MeetingService | None = None


def get_meeting_service() -> MeetingService:
    global _service
    if _service is None:
        _service = MeetingService()
    return _service
