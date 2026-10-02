from __future__ import annotations

import json


def succeeded(value: str | dict) -> bool:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return bool(value.strip()) and not value.lstrip().lower().startswith(("fehler:", "error:"))
    if not isinstance(value, dict):
        return True
    if value.get("error") or value.get("fehler"):
        return False
    if value.get("ok") is False or value.get("success") is False or value.get("timed_out"):
        return False
    if str(value.get("status")) in {"failed", "error", "cancelled", "denied"}:
        return False
    for key in ("exit_code", "returncode"):
        if key in value and value[key] not in (0, "0"):
            return False
    return True
