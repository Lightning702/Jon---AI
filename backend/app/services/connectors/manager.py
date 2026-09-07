from __future__ import annotations

from typing import Any

from app.core.logbook import logger as logbook_logger
from app.services.connectors.basis import Connector, Werkzeug

_log = logbook_logger("connectors")


class ConnectorManager:
    def __init__(self) -> None:
        self._connectoren: dict[str, Connector] = {}

    def registrieren(self, connector: Connector) -> None:
        if not connector.id:
            raise ValueError("Ein Connector braucht eine id.")
        self._connectoren[connector.id] = connector

    def entfernen(self, kennung: str) -> bool:
        return self._connectoren.pop(kennung, None) is not None

    def alle(self) -> list[Connector]:
        return list(self._connectoren.values())

    def connector(self, kennung: str) -> Connector | None:
        return self._connectoren.get(kennung)

    def werkzeuge(self) -> list[Werkzeug]:
        gesammelt: list[Werkzeug] = []
        for connector in self._connectoren.values():
            try:
                if not connector.bereit():
                    continue
                gesammelt.extend(connector.werkzeuge())
            except Exception as exc:
                _log.warning("Connector %s meldet keine Werkzeuge: %s", connector.id, exc)
        return gesammelt

    def namen(self) -> set[str]:
        return {werkzeug.name for werkzeug in self.werkzeuge()}

    def schema(self) -> list[dict]:
        return [werkzeug.schema() for werkzeug in self.werkzeuge()]

    def kennt(self, name: str) -> bool:
        return self._finden(name) is not None

    def uebersicht(self) -> list[dict]:
        daten = []
        for connector in self._connectoren.values():
            try:
                daten.append(connector.uebersicht())
            except Exception as exc:
                daten.append({"id": connector.id, "name": connector.name, "fehler": str(exc)})
        return daten

    def _finden(self, name: str) -> Connector | None:
        for connector in self._connectoren.values():
            try:
                if connector.kann(name):
                    return connector
            except Exception:
                continue
        return None

    async def ausfuehren(self, name: str, args: dict[str, Any]) -> dict:
        connector = self._finden(name)
        if connector is None:
            return {"error": f"Kein Connector kann {name}."}
        try:
            return await connector.ausfuehren(name, args)
        except Exception as exc:
            _log.warning("Connector %s scheiterte an %s: %s", connector.id, name, exc)
            return {"error": str(exc)}


_manager: ConnectorManager | None = None


def get_connector_manager() -> ConnectorManager:
    global _manager
    if _manager is None:
        from app.services.connectors.android import AndroidConnector

        _manager = ConnectorManager()
        _manager.registrieren(AndroidConnector())
    return _manager
