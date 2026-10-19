"""Persistent superset definitions and safe pending-workout propagation.

This service owns definition persistence and propagation only. Live cyclic
execution remains in superset_execution_service.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json


class SupersetScope(str, Enum):
    CURRENT = "current"
    CURRENT_AND_FUTURE = "current_and_future"
    FUTURE = "future"


@dataclass(frozen=True)
class SupersetPropagationResult:
    action: str
    scope: SupersetScope
    group_id: str | None
    current_updated: bool
    blueprint_updated: bool
    future_updated: int
    already_equivalent: int
    skipped_started: int
    skipped_missing: int
    skipped_conflict: int
    skipped_exception: int


def _identity_key(conn, exercise):
    rows = conn.execute(
        "SELECT catalog_id,COALESCE(is_custom,0),identity_status "
        "FROM exercise_dict WHERE name=?",
        (exercise,),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(f"Exercise identity is missing or ambiguous: {exercise}")
    catalog_id, is_custom, identity_status = rows[0]
    if catalog_id:
        return f"catalog:{catalog_id}"
    if is_custom or identity_status == "intentional_custom":
        return f"custom:{exercise.strip().casefold()}"
    raise ValueError(f"Exercise identity is not confirmed: {exercise}")


def _stable_group_id(identity_keys):
    material = "|".join(identity_keys).encode("utf-8")
    return "PS" + hashlib.sha256(material).hexdigest()[:14].upper()


def _selected_members(conn, meso, week, day, session_ids):
    ids = [int(value) for value in session_ids]
    if len(ids) not in (2, 3) or len(set(ids)) != len(ids):
        raise ValueError("Select 2 exercises for a superset or 3 for a circuit.")
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        "SELECT id,exercise,status,COALESCE(workout_order,id),exercise_group_id,group_position "
        f"FROM workout_sessions WHERE id IN ({placeholders}) AND meso_number=? "
        "AND week=? AND day_of_week=?",
        (*ids, int(meso), str(week), day),
    ).fetchall()
    if len(rows) != len(ids):
        raise ValueError("Every selected exercise must belong to the chosen workout.")
    by_id = {int(row[0]): row for row in rows}
    ordered = [by_id[sid] for sid in ids]
    if any(row[2] != "Pending" for row in ordered):
        raise ValueError("Only pending exercises can be grouped.")
    if any(conn.execute(
        "SELECT 1 FROM workout_sets WHERE session_id=? AND COALESCE(is_complete,0)=1 LIMIT 1",
        (row[0],),
    ).fetchone() for row in ordered):
        raise ValueError("A workout with completed sets cannot be regrouped.")
    exercises = [row[1] for row in ordered]
    identity_keys = [_identity_key(conn, exercise) for exercise in exercises]
    if len(set(identity_keys)) != len(identity_keys):
        raise ValueError("A persistent group cannot contain duplicate exercise identities.")
    return ordered, exercises, identity_keys


def _blueprint(conn, meso):
    row = conn.execute(
        "SELECT blueprint_json FROM meso_configs WHERE meso_number=?", (int(meso),)
    ).fetchone()
    if not row:
        raise ValueError("The active mesocycle has no recurring blueprint.")
    try:
        value = json.loads(row[0]) if row[0] else {}
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("The recurring blueprint is invalid.") from exc
    if not isinstance(value, dict):
        raise ValueError("The recurring blueprint is invalid.")
    return value


def _blueprint_members(conn, items, identity_keys):
    matches = {}
    for index, item in enumerate(items):
        exercise = item if isinstance(item, str) else item.get("exercise") if isinstance(item, dict) else None
        if not exercise:
            continue
        key = _identity_key(conn, exercise)
        if key in identity_keys:
            if key in matches:
                raise ValueError("The recurring blueprint contains a duplicate selected exercise.")
            matches[key] = (index, exercise, item)
    if set(matches) != set(identity_keys):
        raise ValueError("Every selected exercise must exist once in the recurring blueprint day.")
    return matches


def _update_blueprint(conn, meso, day, identity_keys, group_id, remove):
    blueprint = _blueprint(conn, meso)
    items = blueprint.get(day)
    if not isinstance(items, list):
        raise ValueError("The selected day is not present in the recurring blueprint.")
    matches = _blueprint_members(conn, items, identity_keys)
    for position, key in enumerate(identity_keys, 1):
        index, exercise, item = matches[key]
        normalized = {"exercise": exercise, "order": index + 1} if isinstance(item, str) else dict(item)
        normalized["identity_key"] = key
        normalized["group"] = None if remove else group_id
        normalized["group_position"] = None if remove else position
        items[index] = normalized
    conn.execute(
        "UPDATE meso_configs SET blueprint_json=? WHERE meso_number=?",
        (json.dumps(blueprint, separators=(",", ":")), int(meso)),
    )


def _slot_rows(conn, meso, week, day):
    return conn.execute(
        "SELECT id,exercise,status,exercise_group_id,group_position,COALESCE(schedule_exception,0) "
        "FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? "
        "ORDER BY COALESCE(workout_order,id),id",
        (int(meso), str(week), day),
    ).fetchall()


def _slot_candidates(conn, rows, identity_keys):
    matches = {}
    for row in rows:
        try:
            key = _identity_key(conn, row[1])
        except ValueError:
            continue
        if key in identity_keys:
            if key in matches:
                return None
            matches[key] = row
    return [matches[key] for key in identity_keys] if set(matches) == set(identity_keys) else []


def _has_completed_sets(conn, rows):
    return any(conn.execute(
        "SELECT 1 FROM workout_sets WHERE session_id=? AND COALESCE(is_complete,0)=1 LIMIT 1",
        (row[0],),
    ).fetchone() for row in rows)


def _apply_rows(conn, rows, group_id, remove):
    for position, row in enumerate(rows, 1):
        conn.execute(
            "UPDATE workout_sessions SET exercise_group_id=?,group_position=? WHERE id=?",
            (None if remove else group_id, None if remove else position, row[0]),
        )


def apply_persistent_superset(
    conn, *, meso, source_week, day, session_ids, scope, remove=False
):
    """Create/remove a group and optionally persist it to compatible future workouts."""
    scope = SupersetScope(scope)
    started_transaction = not conn.in_transaction
    if started_transaction:
        conn.execute("BEGIN IMMEDIATE")
    try:
        selected, exercises, identity_keys = _selected_members(
            conn, meso, source_week, day, session_ids
        )
        group_id = None if remove else _stable_group_id(identity_keys)
        current_updated = False
        blueprint_updated = False
        future_updated = already_equivalent = 0
        skipped_started = skipped_missing = skipped_conflict = skipped_exception = 0

        if scope in (SupersetScope.CURRENT, SupersetScope.CURRENT_AND_FUTURE):
            existing = [(row[4], row[5]) for row in selected]
            desired = [(None, None)] * len(selected) if remove else [
                (group_id, position) for position in range(1, len(selected) + 1)
            ]
            if existing != desired:
                _apply_rows(conn, selected, group_id, remove)
                current_updated = True
            else:
                already_equivalent += 1

        if scope in (SupersetScope.CURRENT_AND_FUTURE, SupersetScope.FUTURE):
            _update_blueprint(conn, meso, day, identity_keys, group_id, remove)
            blueprint_updated = True
            weeks = [row[0] for row in conn.execute(
                "SELECT DISTINCT week FROM workout_sessions WHERE meso_number=? "
                "AND day_of_week=? AND status='Pending' AND CAST(week AS INTEGER)>? "
                "ORDER BY CAST(week AS INTEGER)",
                (int(meso), day, int(source_week)),
            ).fetchall()]
            for week in weeks:
                rows = _slot_rows(conn, meso, week, day)
                candidates = _slot_candidates(conn, rows, identity_keys)
                if candidates is None:
                    skipped_conflict += 1
                    continue
                if not candidates:
                    skipped_missing += 1
                    continue
                if any(row[5] for row in candidates):
                    skipped_exception += 1
                    continue
                if any(row[2] != "Pending" for row in candidates) or _has_completed_sets(conn, candidates):
                    skipped_started += 1
                    continue
                existing = [(row[3], row[4]) for row in candidates]
                desired = [(None, None)] * len(candidates) if remove else [
                    (group_id, position) for position in range(1, len(candidates) + 1)
                ]
                if existing == desired:
                    already_equivalent += 1
                    continue
                if not remove and any(row[3] not in (None, group_id) for row in candidates):
                    skipped_conflict += 1
                    continue
                _apply_rows(conn, candidates, group_id, remove)
                future_updated += 1

        if started_transaction:
            conn.commit()
        return SupersetPropagationResult(
            action="remove" if remove else "create",
            scope=scope,
            group_id=group_id,
            current_updated=current_updated,
            blueprint_updated=blueprint_updated,
            future_updated=future_updated,
            already_equivalent=already_equivalent,
            skipped_started=skipped_started,
            skipped_missing=skipped_missing,
            skipped_conflict=skipped_conflict,
            skipped_exception=skipped_exception,
        )
    except Exception:
        if started_transaction:
            conn.rollback()
        raise
