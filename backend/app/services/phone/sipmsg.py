from __future__ import annotations

import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field

BRANCH_MAGIC = "z9hG4bK"
_ANGLE_RE = re.compile(r"<([^>]+)>")
_BARE_RE = re.compile(r"(sips?:[^;,\s<>]+)")
_PARAM_RE = re.compile(r'(\w+)\s*=\s*"?([^",]+)"?')


def new_tag() -> str:
    return secrets.token_hex(6)


def new_branch() -> str:
    return BRANCH_MAGIC + secrets.token_hex(8)


def new_call_id(host: str) -> str:
    return f"{secrets.token_hex(10)}@{host}"


@dataclass
class SipUri:
    user: str = ""
    host: str = ""
    port: int = 5060
    transport: str = "udp"

    def __str__(self) -> str:
        base = f"sip:{self.user}@{self.host}" if self.user else f"sip:{self.host}"
        if self.port and self.port != 5060:
            base += f":{self.port}"
        if self.transport and self.transport != "udp":
            base += f";transport={self.transport}"
        return base

    @property
    def address(self) -> tuple[str, int]:
        return self.host, self.port or 5060


def parse_uri(value: str) -> SipUri:
    text = str(value or "").strip()
    angle = _ANGLE_RE.search(text)
    if angle:
        text = angle.group(1)
    else:
        bare = _BARE_RE.search(text)
        if bare:
            text = bare.group(1)
        else:
            text = text.split(";")[0].split(",")[0]
    text = text.strip()
    for prefix in ("sip:", "sips:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    transport = "udp"
    if ";" in text:
        text, _, params = text.partition(";")
        for part in params.split(";"):
            if part.lower().startswith("transport="):
                transport = part.split("=", 1)[1].strip().lower()
    user = ""
    if "@" in text:
        user, _, text = text.partition("@")
    host = text
    port = 5060
    if host.startswith("["):
        host, _, rest = host.partition("]")
        host = host[1:]
        if rest.startswith(":"):
            port = int(rest[1:] or 5060)
    elif ":" in host:
        host, _, raw = host.partition(":")
        try:
            port = int(raw)
        except ValueError:
            port = 5060
    return SipUri(user=user, host=host, port=port, transport=transport)


@dataclass
class SipMessage:
    method: str = ""
    uri: str = ""
    status: int = 0
    reason: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    raw_headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""

    @property
    def is_request(self) -> bool:
        return bool(self.method)

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)

    def cseq_number(self) -> int:
        try:
            return int(self.header("cseq").split()[0])
        except (ValueError, IndexError):
            return 0

    def cseq_method(self) -> str:
        parts = self.header("cseq").split()
        return parts[1].upper() if len(parts) > 1 else ""

    def from_tag(self) -> str:
        return _param(self.header("from"), "tag")

    def to_tag(self) -> str:
        return _param(self.header("to"), "tag")

    def encode(self) -> bytes:
        if self.is_request:
            start = f"{self.method} {self.uri} SIP/2.0"
        else:
            start = f"SIP/2.0 {self.status} {self.reason}"
        lines = [start]
        for name, value in self.raw_headers:
            lines.append(f"{name}: {value}")
        head = "\r\n".join(lines) + "\r\n\r\n"
        return head.encode("utf-8") + self.body


def _param(value: str, name: str) -> str:
    for part in str(value or "").split(";")[1:]:
        key, _, raw = part.partition("=")
        if key.strip().lower() == name:
            return raw.strip().strip('"')
    return ""


def parse(data: bytes) -> SipMessage | None:
    try:
        head, _, body = data.partition(b"\r\n\r\n")
        lines = head.decode("utf-8", "replace").split("\r\n")
    except Exception:
        return None
    if not lines or not lines[0].strip():
        return None
    message = SipMessage(body=body)
    start = lines[0].split()
    if lines[0].upper().startswith("SIP/2.0"):
        if len(start) < 2:
            return None
        try:
            message.status = int(start[1])
        except ValueError:
            return None
        message.reason = " ".join(start[2:])
    else:
        if len(start) < 3:
            return None
        message.method = start[0].upper()
        message.uri = start[1]
    for line in lines[1:]:
        if not line.strip():
            continue
        if line[0] in " \t" and message.raw_headers:
            name, value = message.raw_headers[-1]
            merged = f"{value} {line.strip()}"
            message.raw_headers[-1] = (name, merged)
            message.headers[name.lower()] = merged
            continue
        name, _, value = line.partition(":")
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        message.raw_headers.append((name, value))
        key = name.lower()
        if key in message.headers and key in ("via", "route", "record-route"):
            message.headers[key] = message.headers[key] + "," + value
        else:
            message.headers[key] = value
    length = message.header("content-length")
    if length.isdigit():
        message.body = message.body[: int(length)]
    return message


def build_request(
    method: str,
    uri: str,
    headers: list[tuple[str, str]],
    body: bytes = b"",
    content_type: str = "",
) -> SipMessage:
    items = list(headers)
    if body and content_type:
        items.append(("Content-Type", content_type))
    items.append(("Content-Length", str(len(body))))
    message = SipMessage(method=method.upper(), uri=uri, raw_headers=items, body=body)
    message.headers = {name.lower(): value for name, value in items}
    return message


def build_response(
    request: SipMessage,
    status: int,
    reason: str,
    extra: list[tuple[str, str]] | None = None,
    body: bytes = b"",
    content_type: str = "",
    to_tag: str = "",
) -> SipMessage:
    items: list[tuple[str, str]] = []
    for name, value in request.raw_headers:
        if name.lower() in ("via", "from", "call-id", "cseq"):
            items.append((name, value))
        elif name.lower() == "to":
            if to_tag and "tag=" not in value:
                value = f"{value};tag={to_tag}"
            items.append((name, value))
        elif name.lower() == "record-route":
            items.append((name, value))
    items.extend(extra or [])
    if body and content_type:
        items.append(("Content-Type", content_type))
    items.append(("Content-Length", str(len(body))))
    message = SipMessage(status=status, reason=reason, raw_headers=items, body=body)
    message.headers = {name.lower(): value for name, value in items}
    return message


def parse_auth(value: str) -> dict[str, str]:
    return {k.lower(): v for k, v in _PARAM_RE.findall(str(value or ""))}


def digest_response(
    username: str,
    password: str,
    realm: str,
    nonce: str,
    method: str,
    uri: str,
    algorithm: str = "MD5",
    qop: str = "",
    cnonce: str = "",
    nc: str = "00000001",
) -> str:
    def md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    ha1 = md5(f"{username}:{realm}:{password}")
    if algorithm.upper() == "MD5-SESS":
        ha1 = md5(f"{ha1}:{nonce}:{cnonce}")
    ha2 = md5(f"{method.upper()}:{uri}")
    if qop:
        return md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    return md5(f"{ha1}:{nonce}:{ha2}")


def make_nonce() -> str:
    return hashlib.md5(f"{time.time()}{secrets.token_hex(8)}".encode()).hexdigest()


def authorization_header(
    username: str,
    password: str,
    challenge: dict[str, str],
    method: str,
    uri: str,
) -> str:
    realm = challenge.get("realm", "")
    nonce = challenge.get("nonce", "")
    opaque = challenge.get("opaque", "")
    algorithm = challenge.get("algorithm", "MD5")
    qop_options = [q.strip() for q in challenge.get("qop", "").split(",") if q.strip()]
    qop = "auth" if "auth" in qop_options else ""
    cnonce = secrets.token_hex(8) if qop or algorithm.upper() == "MD5-SESS" else ""
    nc = "00000001"
    response = digest_response(
        username, password, realm, nonce, method, uri, algorithm, qop, cnonce, nc
    )
    parts = [
        f'username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        f"algorithm={algorithm}",
    ]
    if qop:
        parts.extend([f"qop={qop}", f"nc={nc}", f'cnonce="{cnonce}"'])
    if opaque:
        parts.append(f'opaque="{opaque}"')
    return "Digest " + ", ".join(parts)


def build_sdp(host: str, port: int, payload_types: list[int], session_id: int) -> bytes:
    names = {0: "PCMU/8000", 8: "PCMA/8000"}
    formats = " ".join(str(p) for p in payload_types)
    lines = [
        "v=0",
        f"o=jon {session_id} {session_id} IN IP4 {host}",
        "s=Jon",
        f"c=IN IP4 {host}",
        "t=0 0",
        f"m=audio {port} RTP/AVP {formats} 101",
        *[f"a=rtpmap:{p} {names.get(p, 'PCMU/8000')}" for p in payload_types],
        "a=rtpmap:101 telephone-event/8000",
        "a=fmtp:101 0-15",
        "a=ptime:20",
        "a=sendrecv",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def parse_sdp(body: bytes) -> dict:
    host = ""
    port = 0
    payloads: list[int] = []
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        return {"host": "", "port": 0, "payloads": []}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("c=IN IP4 "):
            host = line[9:].strip().split("/")[0]
        elif line.startswith("m=audio "):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    port = int(parts[1])
                except ValueError:
                    port = 0
                for raw in parts[3:]:
                    try:
                        payloads.append(int(raw))
                    except ValueError:
                        continue
    return {"host": host, "port": port, "payloads": payloads}
