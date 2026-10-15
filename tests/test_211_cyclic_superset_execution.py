import sqlite3

from services.superset_execution_service import (
    SupersetExecutionAction,
    resolve_post_set_action,
    select_cyclic_target,
)


def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE workout_sessions(
            id INTEGER PRIMARY KEY,
            exercise_group_id TEXT,
            group_position INTEGER,
            status TEXT,
            exercise TEXT,
            category TEXT,
            meso_number INTEGER,
            week TEXT,
            day_of_week TEXT,
            workout_order INTEGER
        );
        CREATE TABLE workout_sets(
            session_id INTEGER,
            set_number INTEGER,
            is_complete INTEGER
        );
        """
    )
    return conn


def add(conn, session_id, position, completed=(), total=3, status="Pending"):
    conn.execute(
        "INSERT INTO workout_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",
        (session_id, "G", position, status, f"A{position}", "Group", 1, "1", "Monday", position),
    )
    for set_number in range(1, total + 1):
        conn.execute(
            "INSERT INTO workout_sets VALUES(?,?,?)",
            (session_id, set_number, int(set_number in completed)),
        )


def test_pure_selector_cycles_from_a2_then_a3_then_a1():
    candidates = [
        (1, "A1", "Group", 1, 1),
        (2, "A2", "Group", 2, 2),
        (3, "A3", "Group", 3, 1),
    ]
    assert select_cyclic_target(candidates, source_position=2, completed_set_number=1)[0] == 3
    assert select_cyclic_target(candidates, source_position=3, completed_set_number=1)[0] == 1


def test_starting_at_a2_routes_a2_to_a3():
    conn = db()
    add(conn, 1, 1)
    add(conn, 2, 2, completed=(1,))
    add(conn, 3, 3)
    instruction = resolve_post_set_action(conn, session_id=2, completed_set_number=1)
    assert instruction.action == SupersetExecutionAction.ADVANCE_GROUP
    assert (instruction.target_session_id, instruction.target_set_number) == (3, 1)


def test_a3_wraps_to_a1_before_advancing_round():
    conn = db()
    add(conn, 1, 1)
    add(conn, 2, 2, completed=(1,))
    add(conn, 3, 3, completed=(1,))
    instruction = resolve_post_set_action(conn, session_id=3, completed_set_number=1)
    assert (instruction.target_session_id, instruction.target_set_number) == (1, 1)
    assert instruction.round_complete


def test_a1_then_continues_to_a2_next_round():
    conn = db()
    add(conn, 1, 1, completed=(1,))
    add(conn, 2, 2, completed=(1,))
    add(conn, 3, 3, completed=(1,))
    instruction = resolve_post_set_action(conn, session_id=1, completed_set_number=1)
    assert (instruction.target_session_id, instruction.target_set_number) == (2, 2)


def test_starting_at_a3_wraps_to_a1():
    conn = db()
    add(conn, 1, 1)
    add(conn, 2, 2)
    add(conn, 3, 3, completed=(1,))
    instruction = resolve_post_set_action(conn, session_id=3, completed_set_number=1)
    assert (instruction.target_session_id, instruction.target_set_number) == (1, 1)


def test_unequal_counts_skip_exhausted_member():
    conn = db()
    add(conn, 1, 1, completed=(1, 2), total=3)
    add(conn, 2, 2, completed=(1, 2), total=2)
    add(conn, 3, 3, completed=(1, 2), total=4)
    instruction = resolve_post_set_action(conn, session_id=1, completed_set_number=2)
    assert (instruction.target_session_id, instruction.target_set_number) == (3, 3)
    assert instruction.remaining_member_count == 2


def test_skipped_and_completed_members_are_bypassed():
    conn = db()
    add(conn, 1, 1, completed=(1,))
    add(conn, 2, 2, status="Skipped")
    add(conn, 3, 3, completed=(1, 2, 3), total=3, status="Completed")
    instruction = resolve_post_set_action(conn, session_id=1, completed_set_number=1)
    assert instruction.target_session_id == 1
    assert instruction.target_set_number == 2
    assert instruction.single_member_remaining


def test_all_members_complete_returns_group_log_instruction():
    conn = db()
    add(conn, 1, 1, completed=(1,), total=1)
    add(conn, 2, 2, completed=(1,), total=1)
    instruction = resolve_post_set_action(conn, session_id=2, completed_set_number=1)
    assert instruction.action == SupersetExecutionAction.READY_TO_LOG_GROUP
    assert instruction.group_complete


def test_reason_code_identifies_cyclic_router():
    conn = db()
    add(conn, 1, 1, completed=(1,))
    add(conn, 2, 2)
    instruction = resolve_post_set_action(conn, session_id=1, completed_set_number=1)
    assert instruction.reason_code == "GROUP_NEXT_CYCLIC"
