from __future__ import annotations

import threading
import time
from contextlib import suppress

from app.core.config import DATA_DIR
from app.services.settings_service import get_settings_service

WAKEWORD_DIR = DATA_DIR / "wakeword"
THRESHOLDS = {"niedrig": 0.75, "mittel": 0.55, "hoch": 0.4}
IDLE_STOP_SECONDS = 8
COOLDOWN_SECONDS = 2.0


class WakeService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counter = 0
        self._listening = False
        self._stream = None
        self._model = None
        self._error = ""
        self._last_poll = 0.0
        self._last_hit = 0.0
        self._watchdog_started = False
        self._available: bool | None = None

    def _threshold(self) -> float:
        level = str(
            get_settings_service().get().get("wake_sensitivity", "mittel")
        ).lower()
        return THRESHOLDS.get(level, 0.55)

    def available(self) -> bool:
        if self._available is None:
            try:
                import openwakeword  # noqa: F401
                import sounddevice  # noqa: F401

                self._available = True
            except Exception as exc:
                self._available = False
                self._error = f"openWakeWord nicht verfuegbar: {exc}"
        return self._available

    def start(self) -> dict:
        with self._lock:
            self._last_poll = time.time()
            if self._listening:
                return self._status_locked()
            if not self.available():
                return self._status_locked()
            try:
                import numpy as np
                import sounddevice as sd
                from openwakeword.model import Model

                custom = (
                    sorted(str(p) for p in WAKEWORD_DIR.glob("*.onnx"))
                    if WAKEWORD_DIR.is_dir()
                    else []
                )
                if custom:
                    self._model = Model(
                        wakeword_models=custom, inference_framework="onnx"
                    )
                else:
                    with suppress(Exception):
                        from openwakeword.utils import download_models

                        download_models(["hey_jarvis"])
                    self._model = Model(
                        wakeword_models=["hey_jarvis"], inference_framework="onnx"
                    )

                def callback(indata, frames, time_info, status) -> None:
                    try:
                        audio = np.frombuffer(bytes(indata), dtype=np.int16)
                        scores = self._model.predict(audio)
                        best = max(scores.values(), default=0.0)
                        if best >= self._threshold():
                            now = time.time()
                            if now - self._last_hit > COOLDOWN_SECONDS:
                                self._last_hit = now
                                self._counter += 1
                                with suppress(Exception):
                                    self._model.reset()
                    except Exception:
                        pass

                self._stream = sd.RawInputStream(
                    samplerate=16000,
                    blocksize=1280,
                    channels=1,
                    dtype="int16",
                    callback=callback,
                )
                self._stream.start()
                self._listening = True
                self._error = ""
                if not self._watchdog_started:
                    self._watchdog_started = True
                    threading.Thread(target=self._watch, daemon=True).start()
            except Exception as exc:
                self._error = f"Wake-Word-Start fehlgeschlagen: {exc}"
                self._listening = False
                self._stream = None
                self._model = None
            return self._status_locked()

    def _stop_locked(self) -> None:
        if self._stream is not None:
            with suppress(Exception):
                self._stream.stop()
                self._stream.close()
        self._stream = None
        self._model = None
        self._listening = False

    def stop(self) -> dict:
        with self._lock:
            self._stop_locked()
            return self._status_locked()

    def _watch(self) -> None:
        while True:
            time.sleep(2)
            with self._lock:
                if (
                    self._listening
                    and time.time() - self._last_poll > IDLE_STOP_SECONDS
                ):
                    self._stop_locked()

    def _status_locked(self) -> dict:
        return {
            "available": bool(self._available),
            "listening": self._listening,
            "counter": self._counter,
            "error": self._error,
        }

    def poll(self) -> dict:
        with self._lock:
            self._last_poll = time.time()
            if self._available is None:
                self.available()
            return self._status_locked()


_service: WakeService | None = None


def get_wake_service() -> WakeService:
    global _service
    if _service is None:
        _service = WakeService()
    return _service
