"""Framework-neutral state helpers for the sticky workout rest timer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

EARLY_REST_END_SECONDS = 60
TARGET_REST_END_SECONDS = 330
RESTORE_HORIZON_SECONDS = 1800


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
    if seconds < EARLY_REST_END_SECONDS:
        return "early"
    if seconds < TARGET_REST_END_SECONDS:
        return "target"
    return "long"


def rest_timer_label(phase):
    return {
        "early": "🟡 EARLY",
        "target": "🟢 TARGET",
        "long": "🔴 LONG",
    }.get(phase, "REST")


def rest_timer_snapshot(started_at, now=None):
    elapsed = elapsed_rest_seconds(started_at, now)
    if elapsed is None:
        return None
    phase = rest_timer_phase(elapsed)
    return RestTimerSnapshot(
        elapsed_seconds=elapsed,
        text=f"{rest_timer_label(phase)} {format_rest_elapsed(elapsed)}",
        phase=phase,
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


def latest_active_workout_completion(
    conn, *, meso_number, week, day_of_week, now=None,
    restore_horizon_seconds=RESTORE_HORIZON_SECONDS,
):
    """Restore the latest valid completion for only the active workout."""
    rows = conn.execute(
        "SELECT s.completed_at FROM workout_sets s "
        "JOIN workout_sessions ws ON ws.id=s.session_id "
        "WHERE ws.meso_number=? AND ws.week=? AND ws.day_of_week=? "
        "AND COALESCE(s.is_complete,0)=1 AND s.completed_at IS NOT NULL "
        "ORDER BY s.completed_at DESC, s.id DESC",
        (int(meso_number), str(week), day_of_week),
    ).fetchall()
    current = parse_completed_at(now) if now is not None else datetime.now()
    for (raw_value,) in rows:
        completed = parse_completed_at(raw_value)
        if completed is None or current is None:
            continue
        age = max(0, int((current - completed).total_seconds()))
        return raw_value if age <= int(restore_horizon_seconds) else None
    return None
