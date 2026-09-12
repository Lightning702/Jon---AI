from __future__ import annotations

import asyncio
import contextvars
import uuid

APPROVAL_TIMEOUT = 300.0

_unbeaufsichtigt: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "jon_unbeaufsichtigt", default=False
)


class ToolDeniedError(RuntimeError):
    pass


class FreigabeNoetig(RuntimeError):
    def __init__(self, werkzeug: str, args: dict | None = None, grund: str = "") -> None:
        super().__init__(grund or f"{werkzeug} braucht eine Freigabe.")
        self.werkzeug = werkzeug
        self.args = args or {}
        self.grund = grund


def unbeaufsichtigt(an: bool = True):
    return _unbeaufsichtigt.set(an)


def laeuft_unbeaufsichtigt() -> bool:
    return bool(_unbeaufsichtigt.get())


def zuruecksetzen(marke) -> None:
    try:
        _unbeaufsichtigt.reset(marke)
    except (ValueError, LookupError):
        _unbeaufsichtigt.set(False)


class ApprovalService:
    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[bool]] = {}

    def create(self) -> str:
        approval_id = uuid.uuid4().hex
        self._pending[approval_id] = asyncio.get_running_loop().create_future()
        return approval_id

    def resolve(self, approval_id: str, approved: bool) -> bool:
        future = self._pending.get(approval_id)
        if future is None or future.done():
            return False
        future.set_result(approved)
        return True

    def vergessen(self, approval_id: str) -> None:
        self._pending.pop(approval_id, None)

    def offen(self) -> list[str]:
        return [k for k, f in self._pending.items() if not f.done()]

    async def wait(self, approval_id: str, timeout: float = APPROVAL_TIMEOUT) -> bool:
        future = self._pending.get(approval_id)
        if future is None:
            return False
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending.pop(approval_id, None)


_service: ApprovalService | None = None


def get_approval_service() -> ApprovalService:
    global _service
    if _service is None:
        _service = ApprovalService()
    return _service
