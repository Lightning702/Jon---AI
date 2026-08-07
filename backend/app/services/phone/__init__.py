from __future__ import annotations

from app.services.phone.audio import (
    RATE_NET,
    RATE_STT,
    SAMPLES_PER_FRAME,
    VoiceGate,
    decode_to_pcm,
    resample,
)
from app.services.phone.g711 import (
    PAYLOAD_ALAW,
    PAYLOAD_ULAW,
    alaw_decode,
    alaw_encode,
    ulaw_decode,
    ulaw_encode,
)
from app.services.phone.rtp import RtpSession
from app.services.phone.sipmsg import SipMessage, digest_response, parse_uri
from app.services.phone.stack import CallHandle, SipStack

__all__ = [
    "RATE_NET",
    "RATE_STT",
    "SAMPLES_PER_FRAME",
    "VoiceGate",
    "decode_to_pcm",
    "resample",
    "PAYLOAD_ALAW",
    "PAYLOAD_ULAW",
    "alaw_decode",
    "alaw_encode",
    "ulaw_decode",
    "ulaw_encode",
    "RtpSession",
    "SipMessage",
    "digest_response",
    "parse_uri",
    "CallHandle",
    "SipStack",
]
