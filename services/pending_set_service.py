"""Pending-set lifecycle authority for IronCycle 1.91.

The service owns draft creation, mutation, normalization, atomic persistence,
and restart restoration without importing Flet. UI controls remain in main.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from services.target_ownership_service import normalize_reps_source, normalize_weight_source


@dataclass(frozen=True)
class PendingSetContext:
    session_id: int
    targets: tuple
    normal_targets: tuple


def _text(value):
    return "" if value is None else str(value).strip()


def create_pending_set(target):
    return {
        "w": _text(target.get("w", "")),
        "r": _text(target.get("r", "")),
        "rpe": "",
        "rest": None,
        "completed_at": None,
        "done": False,
        "w_source": "target",
        "r_source": "target",
    }


def add_set(drafts, target):
    return [dict(row) for row in (drafts or [])] + [create_pending_set(target)]


def remove_last_set(drafts, minimum=1):
    rows = [dict(row) for row in (drafts or [])]
    return rows[:-1] if len(rows) > minimum else rows


def copy_previous_set(drafts):
    rows = [dict(row) for row in (drafts or [])]
    destination = next((i for i, row in enumerate(rows) if not row.get("done")), None)
    if destination is None or destination == 0:
        return rows, None
    source = rows[destination - 1]
    rows[destination].update({
        "w": _text(source.get("w", "")),
        "r": _text(source.get("r", "")),
        "rpe": "",
        "done": False,
        "completed_at": None,
        "w_source": normalize_weight_source(source.get("w_source", "manual")),
        "r_source": normalize_reps_source(source.get("r_source", "manual")),
    })
    return rows, destination


def is_empty_draft(row):
    return not any((_text(row.get("w")), _text(row.get("r")), _text(row.get("rpe")))) and not row.get("done")


def restore_drafts(saved_rows):
    restored = []
    for row in saved_rows or ():
        weight, reps, rpe, rest, completed_at, complete, weight_source, reps_source = row
        restored.append({
            "w": _text(weight), "r": _text(reps), "rpe": _text(rpe), "rest": rest,
            "completed_at": completed_at, "done": bool(complete),
            "w_source": normalize_weight_source(weight_source),
            "r_source": normalize_reps_source(reps_source),
        })
    return restored


def save_pending_sets_atomic(
    conn,
    context: PendingSetContext,
    drafts,
    *,
    normalize_rpe: Callable,
    rest_seconds_for: Callable,
):
    """Replace one session's draft rows in one transaction.

    Invalid partial numeric input stays in memory and is not allowed to destroy
    the last durable draft. Completely empty trailing drafts are omitted.
    """
    prepared = []
    rows = [dict(row) for row in (drafts or [])]
    for index, row in enumerate(rows, start=1):
        if is_empty_draft(row) and index == len(rows):
            continue
        w_raw, r_raw, rpe_raw = _text(row.get("w")), _text(row.get("r")), _text(row.get("rpe"))
        try:
            weight = float(w_raw) if w_raw else None
            reps = int(r_raw) if r_raw else None
        except (TypeError, ValueError):
            return False
        normalized_rpe = normalize_rpe(rpe_raw)
        if rpe_raw and normalized_rpe is None:
            return False
        rpe = float(normalized_rpe) if normalized_rpe is not None else None
        target = context.targets[index - 1] if index <= len(context.targets) else context.targets[-1]
        normal_target = context.normal_targets[index - 1] if index <= len(context.normal_targets) else context.normal_targets[-1]
        completed_at = row.get("completed_at")
        done = bool(row.get("done"))
        rest = rest_seconds_for(completed_at, context.session_id, index) if done and completed_at else None
        prepared.append((
            context.session_id, index, weight, reps, rpe, rest,
            float(target["w"]), int(target["r"]),
            float(normal_target["w"]), int(normal_target["r"]),
            completed_at, int(done),
            normalize_weight_source(row.get("w_source", "target")),
            normalize_reps_source(row.get("r_source", "target")),
        ))
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM workout_sets WHERE session_id = ?", (context.session_id,))
        conn.executemany("""
            INSERT INTO workout_sets
                (session_id, set_number, weight, reps, rpe, rest_seconds,
                 target_weight, target_reps, normal_target_weight, normal_target_reps,
                 completed_at, is_complete, weight_source, reps_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, prepared)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
