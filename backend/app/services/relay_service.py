from __future__ import annotations

import asyncio
import json
import threading

from app.services.settings_service import get_settings_service

DEFAULT_BROKER = "broker.hivemq.com"
DEFAULT_PORT = 1883
TOPIC = "jon-chat/v1"


class RelayService:
    def __init__(self) -> None:
        self._client = None
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def connected(self) -> bool:
        return self._connected

    def status(self) -> dict:
        cfg = get_settings_service().get()
        return {
            "enabled": bool(cfg.get("relay_enabled", False)),
            "connected": self._connected,
            "broker": str(cfg.get("relay_broker", "") or DEFAULT_BROKER),
        }

    def _my_topic(self) -> str:
        from app.services.p2p_service import get_p2p_service

        return f"{TOPIC}/{get_p2p_service().identity()['id']}"

    def _on_message(self, _client, _userdata, message) -> None:
        from app.services.p2p_service import get_p2p_service

        try:
            payload = json.loads(message.payload.decode("utf-8", errors="replace"))
        except Exception:
            return
        kind = str(payload.get("kind", ""))
        body = payload.get("body")
        if not isinstance(body, dict):
            return
        service = get_p2p_service()
        try:
            if kind == "typing":
                peer_id = str(body.get("from_id", ""))
                if peer_id:
                    service.note_typing(peer_id)
            elif kind == "request":
                service.receive_request(body, "")
            elif kind == "event":
                service.receive_event(body, "")
            elif kind == "inbox":
                service.receive(body, "")
        except Exception:
            return

    def _on_connect(self, client, _userdata, _flags, _rc, *_args) -> None:
        self._connected = True
        try:
            client.subscribe(self._my_topic(), qos=1)
        except Exception:
            pass

    def _on_disconnect(self, *_args) -> None:
        self._connected = False

    async def start(self) -> None:
        while True:
            cfg = get_settings_service().get()
            if not cfg.get("relay_enabled", False):
                await self._stop_client()
                await asyncio.sleep(5)
                continue
            if self._client is None:
                await asyncio.to_thread(self._connect)
            await asyncio.sleep(10)

    def _connect(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except Exception:
            return
        cfg = get_settings_service().get()
        broker = str(cfg.get("relay_broker", "") or DEFAULT_BROKER)
        try:
            port = int(cfg.get("relay_port", DEFAULT_PORT) or DEFAULT_PORT)
        except Exception:
            port = DEFAULT_PORT
        from app.services.p2p_service import get_p2p_service

        client_id = f"jon-{get_p2p_service().identity()['id']}"
        try:
            client = mqtt.Client(client_id=client_id, clean_session=True)
        except Exception:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1, client_id=client_id
            )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        try:
            client.connect(broker, port, keepalive=45)
            client.loop_start()
            with self._lock:
                self._client = client
        except Exception:
            self._connected = False
            self._client = None

    async def _stop_client(self) -> None:
        with self._lock:
            client = self._client
            self._client = None
        if client is not None:
            self._connected = False
            try:
                await asyncio.to_thread(client.loop_stop)
                await asyncio.to_thread(client.disconnect)
            except Exception:
                pass

    async def publish(self, peer_id: str, kind: str, body: dict) -> bool:
        if not self._connected or self._client is None:
            return False
        packet = json.dumps({"kind": kind, "body": body}, ensure_ascii=False)
        if len(packet) > 8_000_000:
            return False
        try:
            info = self._client.publish(
                f"{TOPIC}/{peer_id}", packet, qos=1, retain=False
            )
            await asyncio.to_thread(info.wait_for_publish, 20)
            return bool(info.is_published())
        except Exception:
            return False


_service: RelayService | None = None


def get_relay_service() -> RelayService:
    global _service
    if _service is None:
        _service = RelayService()
    return _service
