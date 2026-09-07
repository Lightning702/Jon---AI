from __future__ import annotations

from app.services.browser.manager import get_manager
from app.services.browser.werkzeuge import ausfuehren_json


class BrowserService:
    def call(self, op: str, args: dict) -> str:
        return ausfuehren_json(op, dict(args or {}))

    def schliessen(self) -> str:
        return ausfuehren_json("close", {})

    @property
    def offen(self) -> bool:
        return get_manager().offen


_service: BrowserService | None = None


def get_browser_service() -> BrowserService:
    global _service
    if _service is None:
        _service = BrowserService()
    return _service
