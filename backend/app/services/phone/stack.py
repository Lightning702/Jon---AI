from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field

from app.services.phone import sipmsg
from app.services.phone.rtp import RtpSession, open_port
from app.services.phone.sipmsg import (
    SipMessage,
    SipUri,
    authorization_header,
    build_request,
    build_response,
    build_sdp,
    make_nonce,
    new_branch,
    new_call_id,
    new_tag,
    parse_auth,
    parse_sdp,
    parse_uri,
)

log = logging.getLogger("jon.phone")

USER_AGENT = "Jon"
DEFAULT_PORT = 5060
REGISTER_MIN = 60
NONCE_LIFETIME = 300.0


@dataclass
class Binding:
    contact: SipUri
    source: tuple[str, int]
    expires_at: float
    user_agent: str = ""
    registered_at: float = field(default_factory=time.time)

    @property
    def alive(self) -> bool:
        return time.time() < self.expires_at


@dataclass
class CallHandle:
    call_id: str
    stack: "SipStack"
    remote: SipUri
    local_tag: str
    rtp: RtpSession
    state: str = "calling"
    remote_tag: str = ""
    remote_target: SipUri | None = None
    cseq: int = 1
    from_uri: str = ""
    to_uri: str = ""
    answered_at: float = 0.0
    ended_at: float = 0.0
    reason: str = ""
    answered: asyncio.Event = field(default_factory=asyncio.Event)
    finished: asyncio.Event = field(default_factory=asyncio.Event)
    invite_headers: list[tuple[str, str]] = field(default_factory=list)
    invite_branch: str = ""

    @property
    def active(self) -> bool:
        return self.state in ("calling", "ringing", "active")

    @property
    def duration(self) -> float:
        if not self.answered_at:
            return 0.0
        end = self.ended_at or time.time()
        return max(end - self.answered_at, 0.0)

    async def hangup(self, reason: str = "") -> None:
        await self.stack.hangup(self, reason)


class SipStack(asyncio.DatagramProtocol):
    def __init__(
        self,
        username: str,
        password: str,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        realm: str = "jon",
        advertise: str = "",
        display_name: str = "Jon",
    ) -> None:
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.realm = realm or "jon"
        self.display_name = display_name
        self._advertise = advertise
        self._transport: asyncio.DatagramTransport | None = None
        self._binding: Binding | None = None
        self._calls: dict[str, CallHandle] = {}
        self._pending: dict[str, asyncio.Future] = {}
        self._nonces: dict[str, float] = {}
        self._running = False
        self._last_error = ""
        self._registrations = 0

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def registrations(self) -> int:
        return self._registrations

    @property
    def binding(self) -> Binding | None:
        if self._binding and self._binding.alive:
            return self._binding
        return None

    def local_ip(self) -> str:
        if self._advertise:
            return self._advertise
        if self.host not in ("0.0.0.0", "", "::"):
            return self.host
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            probe.close()

    async def start(self) -> None:
        if self._running:
            return
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: self, local_addr=(self.host, self.port), reuse_port=False
        )
        self._transport = transport
        self._running = True
        self._last_error = ""
        log.info("SIP laeuft auf %s:%s", self.host, self.port)

    async def stop(self) -> None:
        self._running = False
        for call in list(self._calls.values()):
            try:
                await self.hangup(call, "Jon wurde beendet")
            except Exception:
                pass
        if self._transport:
            self._transport.close()
            self._transport = None

    def connection_made(self, transport) -> None:
        self._transport = transport

    def error_received(self, exc: Exception) -> None:
        self._last_error = str(exc)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        message = sipmsg.parse(data)
        if message is None:
            return
        try:
            if message.is_request:
                self._on_request(message, addr)
            else:
                self._on_response(message, addr)
        except Exception as exc:
            self._last_error = str(exc)
            log.exception("SIP-Nachricht fehlgeschlagen")

    def _send(self, message: SipMessage, addr: tuple[str, int]) -> None:
        if self._transport is None:
            return
        try:
            self._transport.sendto(message.encode(), addr)
        except OSError as exc:
            self._last_error = str(exc)

    def _via(self, branch: str) -> str:
        return f"SIP/2.0/UDP {self.local_ip()}:{self.port};branch={branch};rport"

    def _contact(self) -> str:
        return f"<sip:{self.username}@{self.local_ip()}:{self.port}>"

    def _fresh_nonce(self) -> str:
        now = time.time()
        for value, created in list(self._nonces.items()):
            if now - created > NONCE_LIFETIME:
                self._nonces.pop(value, None)
        nonce = make_nonce()
        self._nonces[nonce] = now
        return nonce

    def _check_auth(self, message: SipMessage) -> bool:
        header = message.header("authorization") or message.header(
            "proxy-authorization"
        )
        if not header:
            return False
        challenge = parse_auth(header)
        nonce = challenge.get("nonce", "")
        if nonce not in self._nonces:
            return False
        if time.time() - self._nonces[nonce] > NONCE_LIFETIME:
            self._nonces.pop(nonce, None)
            return False
        if challenge.get("username", "") != self.username:
            return False
        expected = sipmsg.digest_response(
            self.username,
            self.password,
            challenge.get("realm", self.realm),
            nonce,
            message.method,
            challenge.get("uri", message.uri),
            challenge.get("algorithm", "MD5"),
            challenge.get("qop", ""),
            challenge.get("cnonce", ""),
            challenge.get("nc", "00000001"),
        )
        return expected == challenge.get("response", "")

    def _challenge(self, message: SipMessage, addr: tuple[str, int]) -> None:
        nonce = self._fresh_nonce()
        header = (
            f'Digest realm="{self.realm}", nonce="{nonce}", '
            'algorithm=MD5, qop="auth"'
        )
        response = build_response(
            message,
            401,
            "Unauthorized",
            extra=[("WWW-Authenticate", header), ("Server", USER_AGENT)],
            to_tag=new_tag(),
        )
        self._send(response, addr)

    def _on_request(self, message: SipMessage, addr: tuple[str, int]) -> None:
        method = message.method
        if method == "REGISTER":
            self._on_register(message, addr)
        elif method == "OPTIONS":
            self._send(
                build_response(
                    message, 200, "OK", extra=[("Server", USER_AGENT)], to_tag=new_tag()
                ),
                addr,
            )
        elif method in ("BYE", "CANCEL"):
            self._on_bye(message, addr)
        elif method == "ACK":
            return
        elif method == "INVITE":
            self._send(
                build_response(
                    message,
                    486,
                    "Busy Here",
                    extra=[("Server", USER_AGENT)],
                    to_tag=new_tag(),
                ),
                addr,
            )
        else:
            self._send(
                build_response(
                    message,
                    405,
                    "Method Not Allowed",
                    extra=[("Allow", "INVITE, ACK, BYE, CANCEL, OPTIONS, REGISTER")],
                    to_tag=new_tag(),
                ),
                addr,
            )

    def _on_register(self, message: SipMessage, addr: tuple[str, int]) -> None:
        target = parse_uri(message.header("to"))
        if target.user and target.user != self.username:
            self._send(
                build_response(message, 404, "Not Found", to_tag=new_tag()), addr
            )
            return
        if not self._check_auth(message):
            self._challenge(message, addr)
            return
        contact_raw = message.header("contact")
        expires = message.header("expires")
        seconds = 3600
        if expires.isdigit():
            seconds = int(expires)
        param = sipmsg._param(contact_raw, "expires")
        if param.isdigit():
            seconds = int(param)
        if contact_raw.strip() == "*" or seconds == 0:
            self._binding = None
            self._send(
                build_response(
                    message,
                    200,
                    "OK",
                    extra=[("Expires", "0"), ("Server", USER_AGENT)],
                    to_tag=new_tag(),
                ),
                addr,
            )
            return
        seconds = max(seconds, REGISTER_MIN)
        contact = parse_uri(contact_raw)
        if not contact.host:
            contact = SipUri(user=self.username, host=addr[0], port=addr[1])
        self._binding = Binding(
            contact=contact,
            source=addr,
            expires_at=time.time() + seconds,
            user_agent=message.header("user-agent"),
        )
        self._registrations += 1
        response = build_response(
            message,
            200,
            "OK",
            extra=[
                ("Contact", f"{contact_raw};expires={seconds}"),
                ("Expires", str(seconds)),
                ("Date", time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())),
                ("Server", USER_AGENT),
            ],
            to_tag=new_tag(),
        )
        self._send(response, addr)

    def _on_bye(self, message: SipMessage, addr: tuple[str, int]) -> None:
        call_id = message.header("call-id")
        call = self._calls.get(call_id)
        self._send(
            build_response(message, 200, "OK", extra=[("Server", USER_AGENT)]), addr
        )
        if call is None:
            return
        if message.method == "CANCEL":
            call.state = "missed"
            call.reason = "Anruf abgebrochen"
        else:
            call.state = "completed" if call.answered_at else "missed"
            call.reason = "Aufgelegt"
        call.ended_at = time.time()
        call.answered.set()
        call.finished.set()

    def _on_response(self, message: SipMessage, addr: tuple[str, int]) -> None:
        call_id = message.header("call-id")
        call = self._calls.get(call_id)
        method = message.cseq_method()
        future = self._pending.get(f"{call_id}:{message.cseq_number()}")
        if method == "REGISTER" and future and not future.done():
            future.set_result(message)
            return
        if call is None:
            return
        if method != "INVITE":
            return
        status = message.status
        if 100 <= status < 180:
            return
        if 180 <= status < 200:
            if call.state == "calling":
                call.state = "ringing"
            return
        if 200 <= status < 300:
            call.remote_tag = message.to_tag()
            contact = message.header("contact")
            call.remote_target = parse_uri(contact) if contact else call.remote
            sdp = parse_sdp(message.body)
            if sdp["host"] and sdp["port"]:
                chosen = 0
                for payload in sdp["payloads"]:
                    if payload in (0, 8):
                        chosen = payload
                        break
                call.rtp.payload_type = chosen
                call.rtp.set_remote(sdp["host"], sdp["port"])
            self._send_ack(call, message)
            if call.state != "active":
                call.state = "active"
                call.answered_at = time.time()
            call.answered.set()
            return
        if status in (401, 407) and not call.invite_headers:
            return
        call.state = "rejected" if status in (486, 603, 600) else "failed"
        call.reason = _reason_text(status, message.reason)
        call.ended_at = time.time()
        call.answered.set()
        call.finished.set()

    def _send_ack(self, call: CallHandle, response: SipMessage) -> None:
        target = call.remote_target or call.remote
        to_header = response.header("to")
        headers = [
            ("Via", self._via(new_branch())),
            ("Max-Forwards", "70"),
            ("From", call.from_uri),
            ("To", to_header),
            ("Call-ID", call.call_id),
            ("CSeq", f"{call.cseq} ACK"),
            ("Contact", self._contact()),
            ("User-Agent", USER_AGENT),
        ]
        ack = build_request("ACK", str(target), headers)
        self._send(ack, target.address)

    async def call(
        self,
        display: str = "",
        timeout: float = 45.0,
    ) -> CallHandle:
        binding = self.binding
        if binding is None:
            raise RuntimeError(
                "Dein Telefon ist gerade nicht bei Jon angemeldet. "
                "Oeffne die SIP-App und pruefe die Verbindung."
            )
        local_ip = self.local_ip()
        sock, rtp_port = open_port(self.host if self.host != "0.0.0.0" else "0.0.0.0")
        rtp = RtpSession(sock, rtp_port, payload_type=0)
        call_id = new_call_id(local_ip)
        local_tag = new_tag()
        caller = display or self.display_name
        from_uri = f'"{caller}" <sip:{self.username}@{local_ip}>;tag={local_tag}'
        to_uri = f"<{binding.contact}>"
        branch = new_branch()
        session_id = int(time.time())
        sdp = build_sdp(local_ip, rtp_port, [0, 8], session_id)
        handle = CallHandle(
            call_id=call_id,
            stack=self,
            remote=binding.contact,
            local_tag=local_tag,
            rtp=rtp,
            from_uri=from_uri,
            to_uri=to_uri,
            invite_branch=branch,
        )
        self._calls[call_id] = handle
        rtp.start()
        headers = [
            ("Via", self._via(branch)),
            ("Max-Forwards", "70"),
            ("From", from_uri),
            ("To", to_uri),
            ("Call-ID", call_id),
            ("CSeq", "1 INVITE"),
            ("Contact", self._contact()),
            ("User-Agent", USER_AGENT),
            ("Allow", "INVITE, ACK, BYE, CANCEL, OPTIONS"),
            ("Supported", "replaces"),
        ]
        invite = build_request(
            "INVITE", str(binding.contact), headers, sdp, "application/sdp"
        )
        destination = binding.source or binding.contact.address
        self._send(invite, destination)
        asyncio.create_task(self._retransmit(invite, destination, handle))
        try:
            await asyncio.wait_for(handle.answered.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            handle.state = "missed"
            handle.reason = "Es wurde nicht abgenommen"
            handle.ended_at = time.time()
            await self._cancel(handle, invite, destination)
            handle.finished.set()
        return handle

    async def _retransmit(
        self, invite: SipMessage, addr: tuple[str, int], call: CallHandle
    ) -> None:
        delay = 0.5
        for _ in range(6):
            await asyncio.sleep(delay)
            if call.state not in ("calling",):
                return
            self._send(invite, addr)
            delay = min(delay * 2, 4.0)

    async def _cancel(
        self, call: CallHandle, invite: SipMessage, addr: tuple[str, int]
    ) -> None:
        headers = [
            ("Via", self._via(call.invite_branch)),
            ("Max-Forwards", "70"),
            ("From", call.from_uri),
            ("To", call.to_uri),
            ("Call-ID", call.call_id),
            ("CSeq", f"{call.cseq} CANCEL"),
            ("User-Agent", USER_AGENT),
        ]
        cancel = build_request("CANCEL", str(call.remote), headers)
        self._send(cancel, addr)
        await call.rtp.stop()
        self._calls.pop(call.call_id, None)

    async def hangup(self, call: CallHandle, reason: str = "") -> None:
        if call.call_id not in self._calls:
            return
        if call.state == "active":
            call.cseq += 1
            target = call.remote_target or call.remote
            to_header = call.to_uri
            if call.remote_tag and "tag=" not in to_header:
                to_header = f"{to_header};tag={call.remote_tag}"
            headers = [
                ("Via", self._via(new_branch())),
                ("Max-Forwards", "70"),
                ("From", call.from_uri),
                ("To", to_header),
                ("Call-ID", call.call_id),
                ("CSeq", f"{call.cseq} BYE"),
                ("User-Agent", USER_AGENT),
            ]
            bye = build_request("BYE", str(target), headers)
            self._send(bye, target.address)
            call.state = "completed"
        elif call.state in ("calling", "ringing"):
            call.state = "missed"
        call.reason = reason or call.reason or "Aufgelegt"
        call.ended_at = time.time()
        call.answered.set()
        call.finished.set()
        await call.rtp.stop()
        self._calls.pop(call.call_id, None)

    def active_calls(self) -> list[CallHandle]:
        return [c for c in self._calls.values() if c.active]


def _reason_text(status: int, reason: str) -> str:
    if status == 486:
        return "Besetzt"
    if status == 603:
        return "Anruf abgelehnt"
    if status == 480:
        return "Telefon nicht erreichbar"
    if status == 408:
        return "Zeitueberschreitung"
    if status == 404:
        return "SIP-Konto unbekannt"
    if status in (401, 407):
        return "Anmeldedaten stimmen nicht"
    return f"{status} {reason}".strip()
