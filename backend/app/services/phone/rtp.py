from __future__ import annotations

import asyncio
import secrets
import socket
import struct
import time

import numpy as np

from app.services.phone import g711
from app.services.phone.audio import FRAME_MS, RATE_NET, SAMPLES_PER_FRAME

RTP_VERSION = 2
SILENCE = np.zeros(SAMPLES_PER_FRAME, dtype=np.int16)


def open_port(host: str, low: int = 16384, high: int = 32768) -> tuple[socket.socket, int]:
    for _ in range(60):
        port = secrets.randbelow((high - low) // 2) * 2 + low
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((host, port))
            sock.setblocking(False)
            return sock, port
        except OSError:
            sock.close()
    raise RuntimeError("Kein freier RTP-Port gefunden.")


class RtpSession:
    def __init__(self, sock: socket.socket, port: int, payload_type: int = 0) -> None:
        self._sock = sock
        self.port = port
        self.payload_type = payload_type
        self._remote: tuple[str, int] | None = None
        self._ssrc = secrets.randbits(32)
        self._sequence = secrets.randbits(15)
        self._timestamp = secrets.randbits(31)
        self._incoming: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=200)
        self._reader: asyncio.Task | None = None
        self._running = False
        self._sent = 0
        self._received = 0
        self._last_packet = 0.0

    @property
    def packets_received(self) -> int:
        return self._received

    @property
    def packets_sent(self) -> int:
        return self._sent

    @property
    def last_packet_at(self) -> float:
        return self._last_packet

    def set_remote(self, host: str, port: int) -> None:
        self._remote = (host, port)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._reader = asyncio.create_task(self._read_loop())

    async def stop(self) -> None:
        self._running = False
        if self._reader:
            self._reader.cancel()
            try:
                await self._reader
            except (asyncio.CancelledError, Exception):
                pass
            self._reader = None
        try:
            self._sock.close()
        except OSError:
            pass

    async def _read_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(self._sock, 2048)
            except (asyncio.CancelledError, OSError):
                return
            if len(data) < 12:
                continue
            header = struct.unpack("!BBHII", data[:12])
            version = header[0] >> 6
            if version != RTP_VERSION:
                continue
            csrc_count = header[0] & 0x0F
            has_extension = bool(header[0] & 0x10)
            payload_type = header[1] & 0x7F
            offset = 12 + csrc_count * 4
            if has_extension and len(data) >= offset + 4:
                ext_words = struct.unpack("!H", data[offset + 2 : offset + 4])[0]
                offset += 4 + ext_words * 4
            payload = data[offset:]
            if not payload:
                continue
            if self._remote is None:
                self._remote = addr
            if payload_type not in (g711.PAYLOAD_ULAW, g711.PAYLOAD_ALAW):
                continue
            self._received += 1
            self._last_packet = time.monotonic()
            samples = g711.decode(payload, payload_type)
            if self._incoming.full():
                try:
                    self._incoming.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                self._incoming.put_nowait(samples)
            except asyncio.QueueFull:
                pass

    async def read_frame(self, timeout: float = 1.0) -> np.ndarray | None:
        try:
            return await asyncio.wait_for(self._incoming.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def drain(self) -> None:
        while True:
            try:
                self._incoming.get_nowait()
            except asyncio.QueueEmpty:
                return

    def _packet(self, payload: bytes, marker: bool = False) -> bytes:
        first = RTP_VERSION << 6
        second = (0x80 if marker else 0) | (self.payload_type & 0x7F)
        header = struct.pack(
            "!BBHII",
            first,
            second,
            self._sequence & 0xFFFF,
            self._timestamp & 0xFFFFFFFF,
            self._ssrc,
        )
        self._sequence = (self._sequence + 1) & 0xFFFF
        self._timestamp = (self._timestamp + SAMPLES_PER_FRAME) & 0xFFFFFFFF
        return header + payload

    def send_frame(self, pcm: np.ndarray, marker: bool = False) -> None:
        if self._remote is None:
            return
        frame = np.asarray(pcm, dtype=np.int16)
        if frame.size < SAMPLES_PER_FRAME:
            frame = np.pad(frame, (0, SAMPLES_PER_FRAME - frame.size))
        payload = g711.encode(frame[:SAMPLES_PER_FRAME], self.payload_type)
        try:
            self._sock.sendto(self._packet(payload, marker), self._remote)
            self._sent += 1
        except OSError:
            pass

    async def play(self, pcm: np.ndarray, stop: asyncio.Event | None = None) -> bool:
        samples = np.asarray(pcm, dtype=np.int16)
        total = int(np.ceil(samples.size / SAMPLES_PER_FRAME))
        started = time.monotonic()
        for index in range(total):
            if stop is not None and stop.is_set():
                return False
            chunk = samples[index * SAMPLES_PER_FRAME : (index + 1) * SAMPLES_PER_FRAME]
            self.send_frame(chunk, marker=index == 0)
            target = started + (index + 1) * FRAME_MS / 1000.0
            delay = target - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
        return True

    async def play_silence(self, seconds: float) -> None:
        frames = max(int(seconds * 1000 / FRAME_MS), 1)
        started = time.monotonic()
        for index in range(frames):
            self.send_frame(SILENCE)
            target = started + (index + 1) * FRAME_MS / 1000.0
            delay = target - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)


def frames_of(pcm: np.ndarray) -> list[np.ndarray]:
    samples = np.asarray(pcm, dtype=np.int16)
    count = int(np.ceil(samples.size / SAMPLES_PER_FRAME))
    return [
        samples[i * SAMPLES_PER_FRAME : (i + 1) * SAMPLES_PER_FRAME] for i in range(count)
    ]


def tone(frequency: float, seconds: float, amplitude: float = 0.25) -> np.ndarray:
    count = int(RATE_NET * seconds)
    t = np.arange(count, dtype=np.float64) / RATE_NET
    wave = np.sin(2 * np.pi * frequency * t) * amplitude * 32767
    return wave.astype(np.int16)
