from __future__ import annotations

import numpy as np

PAYLOAD_ULAW = 0
PAYLOAD_ALAW = 8

_SEG_ULAW = np.array([0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF, 0x1FFF], dtype=np.int32)
_SEG_ALAW = np.array([0x1F, 0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF], dtype=np.int32)


def _build_ulaw_decode() -> np.ndarray:
    codes = np.arange(256, dtype=np.int32)
    inv = (~codes) & 0xFF
    t = ((inv & 0x0F) << 3) + 0x84
    t = t << ((inv & 0x70) >> 4)
    out = np.where(inv & 0x80, 0x84 - t, t - 0x84)
    return out.astype(np.int16)


def _build_alaw_decode() -> np.ndarray:
    codes = np.arange(256, dtype=np.int32)
    val = codes ^ 0x55
    t = (val & 0x0F) << 4
    seg = (val & 0x70) >> 4
    t = np.where(seg == 0, t + 8, t + 0x108)
    shift = np.maximum(seg - 1, 0)
    t = np.where(seg >= 2, t << shift, t)
    out = np.where(val & 0x80, t, -t)
    return out.astype(np.int16)


_ULAW_DECODE = _build_ulaw_decode()
_ALAW_DECODE = _build_alaw_decode()


def _segment(values: np.ndarray, table: np.ndarray) -> np.ndarray:
    return np.searchsorted(table, values, side="left").astype(np.int32)


def ulaw_encode(pcm: np.ndarray) -> bytes:
    samples = np.asarray(pcm, dtype=np.int16).astype(np.int32) >> 2
    mask = np.where(samples < 0, 0x7F, 0xFF).astype(np.int32)
    magnitude = np.abs(samples)
    magnitude = np.minimum(magnitude, 8159) + 33
    seg = _segment(magnitude, _SEG_ULAW)
    safe = np.minimum(seg, 7)
    value = (safe << 4) | ((magnitude >> (safe + 1)) & 0x0F)
    value = np.where(seg >= 8, 0x7F, value)
    return (value ^ mask).astype(np.uint8).tobytes()


def ulaw_decode(payload: bytes) -> np.ndarray:
    return _ULAW_DECODE[np.frombuffer(payload, dtype=np.uint8)]


def alaw_encode(pcm: np.ndarray) -> bytes:
    samples = np.asarray(pcm, dtype=np.int16).astype(np.int32) >> 3
    negative = samples < 0
    mask = np.where(negative, 0x55, 0xD5).astype(np.int32)
    magnitude = np.where(negative, -samples - 1, samples)
    seg = _segment(magnitude, _SEG_ALAW)
    safe = np.minimum(seg, 7)
    shift = np.where(safe < 2, 1, safe)
    value = (safe << 4) | ((magnitude >> shift) & 0x0F)
    value = np.where(seg >= 8, 0x7F, value)
    return (value ^ mask).astype(np.uint8).tobytes()


def alaw_decode(payload: bytes) -> np.ndarray:
    return _ALAW_DECODE[np.frombuffer(payload, dtype=np.uint8)]


def encode(pcm: np.ndarray, payload_type: int) -> bytes:
    if payload_type == PAYLOAD_ALAW:
        return alaw_encode(pcm)
    return ulaw_encode(pcm)


def decode(payload: bytes, payload_type: int) -> np.ndarray:
    if payload_type == PAYLOAD_ALAW:
        return alaw_decode(payload)
    return ulaw_decode(payload)
