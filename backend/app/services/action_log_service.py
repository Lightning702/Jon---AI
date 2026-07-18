from __future__ import annotations

import json
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Any

from app.db.database import session_scope
from app.db.models import ActionLog

ABSENCE_SOURCES = ("telegram", "automation", "watcher")


def _shorten(value: Any, limit: int) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def log_action(
    source: str, tool: str, args: Any, result: Any, ok: bool = True
) -> None:
    try:
        with session_scope() as session:
            session.add(
                ActionLog(
                    source=(source or "app")[:24],
                    tool=str(tool)[:64],
                    args=_shorten(args, 500),
                    result=_shorten(result, 400),
                    ok=1 if ok else 0,
                )
            )
    except Exception:
        pass


def _row(entry: ActionLog) -> dict:
    return {
        "id": entry.id,
        "source": entry.source,
        "tool": entry.tool,
        "args": entry.args,
        "result": entry.result,
        "ok": bool(entry.ok),
        "created_at": entry.created_at.replace(tzinfo=timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds")
        if entry.created_at
        else "",
    }


def _day_range(day: str) -> tuple[datetime, datetime] | None:
    day = day.strip().lower()
    today = datetime.now().date()
    target = None
    if day in ("heute", "today"):
        target = today
    elif day in ("gestern", "yesterday"):
        target = today - timedelta(days=1)
    else:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m."):
            try:
                parsed = datetime.strptime(day, fmt)
                target = parsed.date()
                if fmt == "%d.%m.":
                    target = target.replace(year=today.year)
                break
            except ValueError:
                continue
    if target is None:
        return None
    start = datetime.combine(target, dtime.min).astimezone(timezone.utc)
    return start, start + timedelta(days=1)


def list_actions(limit: int = 30, source: str = "", day: str = "") -> list[dict]:
    limit = max(1, min(int(limit or 30), 200))
    with session_scope() as session:
        query = session.query(ActionLog).order_by(ActionLog.created_at.desc())
        if source:
            query = query.filter(ActionLog.source == source.strip().lower())
        if day:
            rng = _day_range(day)
            if rng:
                query = query.filter(
                    ActionLog.created_at >= rng[0].replace(tzinfo=None),
                    ActionLog.created_at < rng[1].replace(tzinfo=None),
                )
        return [_row(e) for e in query.limit(limit).all()]


def absence_actions(hours: int = 24, limit: int = 15) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    with session_scope() as session:
        rows = (
            session.query(ActionLog)
            .filter(
                ActionLog.source.in_(ABSENCE_SOURCES),
                ActionLog.created_at >= since.replace(tzinfo=None),
            )
            .order_by(ActionLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "quelle": e.source,
                "aktion": e.tool,
                "details": _shorten(e.args, 120),
                "ok": bool(e.ok),
                "zeit": _row(e)["created_at"],
            }
            for e in rows
        ]
