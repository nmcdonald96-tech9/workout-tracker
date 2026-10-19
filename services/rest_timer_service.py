"""Framework-neutral state helpers for the sticky workout rest timer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RestTimerSnapshot:
    elapsed_seconds: int
    text: str
    phase: str


def parse_completed_at(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def elapsed_rest_seconds(started_at, now=None):
    start = parse_completed_at(started_at)
    current = parse_completed_at(now) if now is not None else datetime.now()
    if start is None or current is None:
        return None
    return max(0, int((current - start).total_seconds()))


def format_rest_elapsed(seconds):
    seconds = max(0, int(seconds or 0))
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}:{remainder:02d}"


def rest_timer_phase(seconds):
    seconds = max(0, int(seconds or 0))
    if seconds < 60:
        return "early"
    if seconds < 120:
        return "middle"
    return "extended"


def rest_timer_snapshot(started_at, now=None):
    elapsed = elapsed_rest_seconds(started_at, now)
    if elapsed is None:
        return None
    return RestTimerSnapshot(
        elapsed_seconds=elapsed,
        text=f"REST {format_rest_elapsed(elapsed)}",
        phase=rest_timer_phase(elapsed),
    )


def latest_completed_timestamp(sets_by_session):
    candidates = []
    for rows in (sets_by_session or {}).values():
        for row in rows or []:
            if row.get("done"):
                parsed = parse_completed_at(row.get("completed_at"))
                if parsed is not None:
                    candidates.append((parsed, row.get("completed_at")))
    return max(candidates, default=(None, None), key=lambda item: item[0])[1]
