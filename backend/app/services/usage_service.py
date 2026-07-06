from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

from app.core.config import DATA_DIR

USAGE_FILE = DATA_DIR / "usage.json"


def _empty() -> dict:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "requests": 0,
        "total_latency": 0.0,
        "last_request": None,
        "last_model": None,
    }


class UsageService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if USAGE_FILE.exists():
            try:
                return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        try:
            USAGE_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency: float = 0.0,
    ) -> None:
        with self._lock:
            bucket = self._data.setdefault(provider, _empty())
            bucket["prompt_tokens"] += int(prompt_tokens or 0)
            bucket["completion_tokens"] += int(completion_tokens or 0)
            bucket["total_tokens"] += int((prompt_tokens or 0) + (completion_tokens or 0))
            bucket["requests"] += 1
            bucket["total_latency"] += float(latency or 0.0)
            bucket["last_request"] = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
            bucket["last_model"] = model
            self._save()

    def summary(self, provider: str | None = None) -> dict:
        with self._lock:
            names = [provider] if provider else list(self._data.keys())
            out: dict[str, dict] = {}
            for name in names:
                bucket = self._data.get(name)
                if not bucket:
                    continue
                requests = bucket["requests"] or 1
                out[name] = {
                    **bucket,
                    "avg_latency": round(bucket["total_latency"] / requests, 2),
                }
            return out

    def reset(self, provider: str | None = None) -> None:
        with self._lock:
            if provider:
                self._data.pop(provider, None)
            else:
                self._data = {}
            self._save()


_service: UsageService | None = None


def get_usage_service() -> UsageService:
    global _service
    if _service is None:
        _service = UsageService()
    return _service
