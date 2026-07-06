from __future__ import annotations

import asyncio
import uuid

APPROVAL_TIMEOUT = 300.0


class ToolDeniedError(RuntimeError):
    pass


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
