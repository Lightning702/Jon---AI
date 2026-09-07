from __future__ import annotations

import asyncio
import json
import threading
import time

from app.core.logbook import logger as logbook_logger
from app.services.handy_service import get_handy_service
from app.core.fehler import leise

_log = logbook_logger("handy-relay")

BASIS = "jon/handy/v1"


class HandyRelay:
    def __init__(self) -> None:
        self._client = None
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._topic = ""
        self._codethema = ""
        self._seit = 0.0
        self._startet = False

    def status(self) -> dict:
        return {
            "verbunden": self._connected,
            "thema": self._topic,
            "verbindet": self._startet and not self._connected,
            "seit": round(time.time() - self._seit, 1) if self._seit else 0.0,
        }

    def _aktiv(self) -> bool:
        from app.services.settings_service import get_settings_service

        if not get_settings_service().get().get("handy_relay", True):
            return False
        dienst = get_handy_service()
        if dienst.geraete():
            return True
        return dienst.kopplung_status().get("status") in ("offen", "wartet")

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        while True:
            try:
                get_handy_service().kopplung_aufraeumen()
                if self._aktiv():
                    if self._client is None:
                        self._starten()
                    else:
                        self._codethema_pflegen()
                elif self._client is not None:
                    await self._trennen()
            except Exception as exc:
                _log.warning("Relay-Schleife: %s", exc)
            await asyncio.sleep(3)

    def sofort(self) -> dict:
        if self._client is None and not self._startet:
            try:
                if self._aktiv():
                    self._starten()
            except Exception as exc:
                _log.warning("Relay-Sofortstart: %s", exc)
        return self.status()

    def _starten(self) -> None:
        with self._lock:
            if self._startet or self._client is not None:
                return
            self._startet = True
            self._seit = time.time()
        threading.Thread(target=self._verbinden, daemon=True).start()

    def _verbinden(self) -> None:
        try:
            import paho.mqtt.client as mqtt
        except Exception:
            with self._lock:
                self._startet = False
            return
        dienst = get_handy_service()
        kennung = dienst.kennung()
        makler = dienst._makler()
        self._topic = f"{BASIS}/pc/{kennung['id']}"
        client_id = f"jon-handy-{kennung['id']}"
        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                clean_session=True,
            )
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=client_id, clean_session=True)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        try:
            client.reconnect_delay_set(min_delay=1, max_delay=8)
        except Exception as _fehler:
            leise(_fehler, "services/handy_relay")
        try:
            client.connect(makler["host"], int(makler["port"]), keepalive=30)
            client.loop_start()
            with self._lock:
                self._client = client
        except Exception as exc:
            self._connected = False
            self._client = None
            _log.warning("Relay nicht erreichbar: %s", exc)
        finally:
            with self._lock:
                self._startet = False

    async def _trennen(self) -> None:
        with self._lock:
            client = self._client
            self._client = None
        self._connected = False
        if client is not None:
            try:
                await asyncio.to_thread(client.loop_stop)
                await asyncio.to_thread(client.disconnect)
            except Exception as _fehler:
                leise(_fehler, "services/handy_relay")

    def _codethema_pflegen(self) -> None:
        gewuenscht = get_handy_service().offenes_thema()
        if gewuenscht == self._codethema:
            return
        with self._lock:
            client = self._client
        if client is None or not self._connected:
            return
        if self._codethema:
            try:
                client.unsubscribe(f"{BASIS}/code/{self._codethema}")
            except Exception as _fehler:
                leise(_fehler, "services/handy_relay")
        if gewuenscht:
            try:
                client.subscribe(f"{BASIS}/code/{gewuenscht}", qos=1)
                _log.info("Relay hoert auf Kopplungscode")
            except Exception:
                return
        self._codethema = gewuenscht

    def _on_connect(self, client, _userdata, _flags, _rc, *_args) -> None:
        self._connected = True
        _log.info("Relay bereit nach %.1f s", time.time() - self._seit if self._seit else 0.0)
        try:
            client.subscribe(self._topic, qos=1)
        except Exception as _fehler:
            leise(_fehler, "services/handy_relay")
        self._codethema = ""
        self._codethema_pflegen()

    def _on_disconnect(self, *_args) -> None:
        self._connected = False

    def _on_message(self, _client, _userdata, message) -> None:
        if self._loop is None:
            return
        try:
            umschlag = json.loads(message.payload.decode("utf-8", errors="replace"))
        except Exception:
            return
        if not isinstance(umschlag, dict):
            return
        asyncio.run_coroutine_threadsafe(self._bearbeiten(umschlag), self._loop)

    async def _bearbeiten(self, umschlag: dict) -> None:
        antwort_thema = str(umschlag.get("r", "")).strip()
        if not antwort_thema:
            return
        ziel = f"{BASIS}/r/{antwort_thema}"
        dienst = get_handy_service()
        try:
            if umschlag.get("s"):
                gesendet = 0
                async for stueck in dienst.umschlag_strom(umschlag):
                    if not self._senden(ziel, stueck):
                        _log.warning(
                            "Strom abgebrochen nach %s Stuecken, Relay nicht verbunden",
                            gesendet,
                        )
                        return
                    gesendet += 1
                _log.info("Strom fertig: %s Stuecke nach %s", gesendet, ziel)
                return
            self._senden(ziel, await dienst.umschlag(umschlag))
        except Exception as exc:
            self._senden(ziel, {"v": 1, "fehler": str(exc)})

    def _senden(self, ziel: str, nutzlast: dict) -> bool:
        with self._lock:
            client = self._client
        if client is None or not self._connected:
            return False
        try:
            client.publish(
                ziel,
                json.dumps(nutzlast, ensure_ascii=False),
                qos=1,
                retain=False,
            )
            return True
        except Exception:
            return False


_relay: HandyRelay | None = None


def get_handy_relay() -> HandyRelay:
    global _relay
    if _relay is None:
        _relay = HandyRelay()
    return _relay
