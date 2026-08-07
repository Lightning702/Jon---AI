from __future__ import annotations

import shutil
import subprocess

import numpy as np

RATE_NET = 8000
RATE_STT = 16000
FRAME_MS = 20
SAMPLES_PER_FRAME = RATE_NET * FRAME_MS // 1000


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def decode_to_pcm(data: bytes, rate: int = RATE_NET) -> np.ndarray:
    if not data:
        return np.zeros(0, dtype=np.int16)
    if not have_ffmpeg():
        raise RuntimeError(
            "ffmpeg wird gebraucht, um Jons Stimme fuer das Telefon umzuwandeln, "
            "ist aber nicht installiert."
        )
    process = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            str(rate),
            "pipe:1",
        ],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if process.returncode != 0 or not process.stdout:
        detail = process.stderr.decode("utf-8", "replace").strip()[:200]
        raise RuntimeError(f"Audio liess sich nicht umwandeln: {detail}")
    return np.frombuffer(process.stdout, dtype=np.int16)


def resample(pcm: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or pcm.size == 0:
        return np.asarray(pcm, dtype=np.int16)
    samples = np.asarray(pcm, dtype=np.int16).astype(np.float32)
    if target_rate < source_rate:
        samples = _lowpass(samples, target_rate / source_rate)
    count = int(round(samples.size * target_rate / source_rate))
    if count <= 0:
        return np.zeros(0, dtype=np.int16)
    source_points = np.arange(samples.size, dtype=np.float64)
    target_points = np.linspace(0.0, samples.size - 1, count, dtype=np.float64)
    out = np.interp(target_points, source_points, samples)
    return np.clip(out, -32768, 32767).astype(np.int16)


def _lowpass(samples: np.ndarray, ratio: float) -> np.ndarray:
    cutoff = max(min(ratio * 0.45, 0.49), 0.01)
    taps = 31
    n = np.arange(taps, dtype=np.float64) - (taps - 1) / 2.0
    kernel = np.sinc(2 * cutoff * n) * np.hamming(taps)
    kernel /= np.sum(kernel)
    return np.convolve(samples, kernel, mode="same").astype(np.float32)


def to_float(pcm: np.ndarray) -> np.ndarray:
    return np.asarray(pcm, dtype=np.int16).astype(np.float32) / 32768.0


def rms(pcm: np.ndarray) -> float:
    if pcm.size == 0:
        return 0.0
    values = np.asarray(pcm, dtype=np.int16).astype(np.float64)
    return float(np.sqrt(np.mean(values * values)))


class VoiceGate:
    def __init__(
        self,
        start_frames: int = 3,
        end_frames: int = 32,
        max_frames: int = 750,
        floor: float = 180.0,
    ) -> None:
        self._start_frames = start_frames
        self._end_frames = end_frames
        self._max_frames = max_frames
        self._floor = floor
        self._noise = floor
        self._loud = 0
        self._quiet = 0
        self._buffer: list[np.ndarray] = []
        self._talking = False

    @property
    def talking(self) -> bool:
        return self._talking

    @property
    def noise_floor(self) -> float:
        return self._noise

    def reset(self) -> None:
        self._loud = 0
        self._quiet = 0
        self._buffer = []
        self._talking = False

    def threshold(self) -> float:
        return max(self._noise * 2.5, self._floor)

    def feed(self, frame: np.ndarray) -> np.ndarray | None:
        level = rms(frame)
        limit = self.threshold()
        if level > limit:
            self._loud += 1
            self._quiet = 0
        else:
            self._quiet += 1
            self._loud = 0
            if not self._talking:
                self._noise = self._noise * 0.95 + level * 0.05
        if not self._talking:
            self._buffer.append(frame)
            if len(self._buffer) > self._start_frames * 2:
                self._buffer.pop(0)
            if self._loud >= self._start_frames:
                self._talking = True
            return None
        self._buffer.append(frame)
        if self._quiet >= self._end_frames or len(self._buffer) >= self._max_frames:
            speech = np.concatenate(self._buffer) if self._buffer else np.zeros(0, np.int16)
            self.reset()
            return speech
        return None

    def flush(self) -> np.ndarray | None:
        if not self._talking or not self._buffer:
            self.reset()
            return None
        speech = np.concatenate(self._buffer)
        self.reset()
        return speech
