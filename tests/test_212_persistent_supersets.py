import json
import sqlite3
from pathlib import Path

import pytest

from services.persistent_superset_service import (
    SupersetScope,
    apply_persistent_superset,
)


DAY = "Monday"
EXERCISES = ("Dumbbell Lateral Raise", "High Incline Dumbbell Shoulder Press")


def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE exercise_dict(
            name TEXT PRIMARY KEY,catalog_id TEXT,is_custom INTEGER DEFAULT 0,
            identity_status TEXT
        );
        CREATE TABLE meso_configs(meso_number INTEGER PRIMARY KEY,blueprint_json TEXT);
        CREATE TABLE workout_sessions(
            id INTEGER PRIMARY KEY,exercise TEXT,status TEXT,workout_order INTEGER,
            exercise_group_id TEXT,group_position INTEGER,meso_number INTEGER,
            week TEXT,day_of_week TEXT,schedule_exception INTEGER DEFAULT 0
        );
        CREATE TABLE workout_sets(
            id INTEGER PRIMARY KEY,session_id INTEGER,set_number INTEGER,is_complete INTEGER DEFAULT 0
        );
        """
    )
    conn.executemany(
        "INSERT INTO exercise_dict VALUES(?,?,0,'canonical')",
        [(EXERCISES[0], "lateral-raise"), (EXERCISES[1], "high-incline-press")],
    )
    blueprint = {DAY: [
        {"exercise": EXERCISES[0], "order": 1, "group": None, "group_position": None},
        {"exercise": EXERCISES[1], "order": 2, "group": None, "group_position": None},
    ]}
    conn.execute("INSERT INTO meso_configs VALUES(1,?)", (json.dumps(blueprint),))
    return conn


def add_week(conn, week, *, omit_second=False, exception=False, group=None, status="Pending"):
    base = int(week) * 10
    conn.execute(
        "INSERT INTO workout_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",
        (base + 1, EXERCISES[0], status, 1, group, 1 if group else None, 1, str(week), DAY, int(exception)),
    )
    if not omit_second:
        conn.execute(
            "INSERT INTO workout_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",
            (base + 2, EXERCISES[1], status, 2, group, 2 if group else None, 1, str(week), DAY, int(exception)),
        )
    conn.commit()
    return [base + 1, base + 2]


def group_values(conn, week):
    return conn.execute(
        "SELECT exercise_group_id,group_position FROM workout_sessions "
        "WHERE week=? ORDER BY workout_order", (str(week),)
    ).fetchall()


def test_current_and_future_persists_blueprint_and_propagates():
    conn = db(); source = add_week(conn, 1); add_week(conn, 2); add_week(conn, 3)
    result = apply_persistent_superset(
        conn, meso=1, source_week="1", day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT_AND_FUTURE,
    )
    assert result.current_updated and result.blueprint_updated
    assert result.future_updated == 2
    assert group_values(conn, 1) == [(result.group_id, 1), (result.group_id, 2)]
    assert group_values(conn, 2) == [(result.group_id, 1), (result.group_id, 2)]
    blueprint = json.loads(conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0])
    assert [item["identity_key"] for item in blueprint[DAY]] == [
        "catalog:lateral-raise", "catalog:high-incline-press"
    ]
    assert [item["group_position"] for item in blueprint[DAY]] == [1, 2]


def test_current_only_does_not_change_blueprint_or_future():
    conn = db(); source = add_week(conn, 1); add_week(conn, 2)
    before = conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0]
    result = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT,
    )
    assert result.current_updated and not result.blueprint_updated
    assert conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0] == before
    assert group_values(conn, 2) == [(None, None), (None, None)]


def test_future_only_leaves_current_unchanged():
    conn = db(); source = add_week(conn, 1); add_week(conn, 2)
    result = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.FUTURE,
    )
    assert not result.current_updated and result.blueprint_updated
    assert group_values(conn, 1) == [(None, None), (None, None)]
    assert group_values(conn, 2) == [(result.group_id, 1), (result.group_id, 2)]


def test_missing_exception_and_conflict_are_skipped_safely():
    conn = db(); source = add_week(conn, 1)
    add_week(conn, 2, omit_second=True)
    add_week(conn, 3, exception=True)
    add_week(conn, 4, group="LOCAL")
    result = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT_AND_FUTURE,
    )
    assert result.skipped_missing == 1
    assert result.skipped_exception == 1
    assert result.skipped_conflict == 1
    assert group_values(conn, 4) == [("LOCAL", 1), ("LOCAL", 2)]


def test_completed_sets_block_current_and_started_future_is_skipped():
    conn = db(); source = add_week(conn, 1); future = add_week(conn, 2)
    conn.execute("INSERT INTO workout_sets(session_id,set_number,is_complete) VALUES(?,?,1)", (future[0], 1))
    conn.commit()
    result = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT_AND_FUTURE,
    )
    assert result.skipped_started == 1
    assert group_values(conn, 2) == [(None, None), (None, None)]
    conn.execute("INSERT INTO workout_sets(session_id,set_number,is_complete) VALUES(?,?,1)", (source[0], 1))
    conn.commit()
    with pytest.raises(ValueError, match="completed sets"):
        apply_persistent_superset(
            conn, meso=1, source_week=1, day=DAY, session_ids=source,
            scope=SupersetScope.CURRENT,
        )


def test_repeated_application_is_idempotent_and_removal_propagates():
    conn = db(); source = add_week(conn, 1); add_week(conn, 2)
    first = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT_AND_FUTURE,
    )
    second = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT_AND_FUTURE,
    )
    assert second.group_id == first.group_id
    assert not second.current_updated and second.future_updated == 0
    assert second.already_equivalent == 2
    removed = apply_persistent_superset(
        conn, meso=1, source_week=1, day=DAY, session_ids=source,
        scope=SupersetScope.CURRENT_AND_FUTURE, remove=True,
    )
    assert removed.current_updated and removed.future_updated == 1
    assert group_values(conn, 1) == [(None, None), (None, None)]
    assert group_values(conn, 2) == [(None, None), (None, None)]
    blueprint = json.loads(conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0])
    assert all(item["group"] is None for item in blueprint[DAY])


def test_failure_rolls_back_blueprint_and_current_group():
    conn = db(); source = add_week(conn, 1); add_week(conn, 2)
    before = conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0]
    conn.execute(
        "CREATE TRIGGER fail_future BEFORE UPDATE OF exercise_group_id ON workout_sessions "
        "WHEN OLD.week='2' BEGIN SELECT RAISE(ABORT,'injected failure'); END"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        apply_persistent_superset(
            conn, meso=1, source_week=1, day=DAY, session_ids=source,
            scope=SupersetScope.CURRENT_AND_FUTURE,
        )
    assert group_values(conn, 1) == [(None, None), (None, None)]
    assert conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0] == before


def test_ui_exposes_explicit_scope_choices_and_service_boundary():
    source = Path("main.py").read_text()
    assert "This workout only" in source
    assert "This and future workouts" in source
    assert "Future workouts only" in source
    assert "apply_persistent_superset(" in source
    assert 'APP_VERSION = "2.1.0"' in Path("constants.py").read_text()
    assert "DATABASE_SCHEMA_VERSION = 20" in Path("constants.py").read_text()
