from __future__ import annotations

import logging
import sys

VORUEBERGEHEND = {64, 121, 1236, 10053, 10054}
_log = logging.getLogger("jon.netz")


def voruebergehend(fehler: BaseException) -> bool:
    return isinstance(fehler, OSError) and getattr(fehler, "winerror", None) in VORUEBERGEHEND


def anwenden() -> bool:
    if sys.platform != "win32":
        return False
    from asyncio import exceptions, proactor_events, trsock

    klasse = proactor_events.BaseProactorEventLoop
    if getattr(klasse, "_jon_annahme_fest", False):
        return True

    def _start_serving(self, protocol_factory, sock, sslcontext=None, server=None, backlog=100, ssl_handshake_timeout=None, ssl_shutdown_timeout=None):
        def loop(f=None):
            try:
                if f is not None:
                    conn, addr = f.result()
                    protocol = protocol_factory()
                    if sslcontext is not None:
                        self._make_ssl_transport(
                            conn, protocol, sslcontext, server_side=True,
                            extra={"peername": addr}, server=server,
                            ssl_handshake_timeout=ssl_handshake_timeout,
                            ssl_shutdown_timeout=ssl_shutdown_timeout,
                        )
                    else:
                        self._make_socket_transport(conn, protocol, extra={"peername": addr}, server=server)
                if self.is_closed():
                    return
                f = self._proactor.accept(sock)
            except OSError as exc:
                if sock.fileno() != -1 and voruebergehend(exc) and not self.is_closed():
                    _log.warning("Verbindung beim Annehmen abgebrochen (%s), der Port bleibt offen", exc)
                    self.call_later(0.05, loop)
                    return
                if sock.fileno() != -1:
                    self.call_exception_handler({
                        "message": "Accept failed on a socket",
                        "exception": exc,
                        "socket": trsock.TransportSocket(sock),
                    })
                    sock.close()
            except exceptions.CancelledError:
                sock.close()
            else:
                self._accept_futures[sock.fileno()] = f
                f.add_done_callback(loop)

        self.call_soon(loop)

    klasse._start_serving = _start_serving
    klasse._jon_annahme_fest = True
    return True
