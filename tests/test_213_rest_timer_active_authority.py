import sqlite3
from pathlib import Path

from services.rest_timer_service import (
    RESTORE_HORIZON_SECONDS,
    latest_active_workout_completion,
)


def database():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE workout_sessions(
          id INTEGER PRIMARY KEY, meso_number INTEGER, week TEXT, day_of_week TEXT
        );
        CREATE TABLE workout_sets(
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER,
          is_complete INTEGER, completed_at TEXT
        );
        """
    )
    return conn


def add(conn, sid, meso, week, day, stamp, complete=1):
    conn.execute(
        "INSERT OR IGNORE INTO workout_sessions VALUES(?,?,?,?)",
        (sid, meso, str(week), day),
    )
    conn.execute(
        "INSERT INTO workout_sets(session_id,is_complete,completed_at) VALUES(?,?,?)",
        (sid, complete, stamp),
    )
    conn.commit()


def test_authority_filters_day_week_and_meso():
    conn = database()
    add(conn, 1, 1, 1, "Monday", "2026-10-19T10:00:00")
    add(conn, 2, 1, 1, "Tuesday", "2026-10-19T10:20:00")
    add(conn, 3, 1, 2, "Monday", "2026-10-19T10:25:00")
    add(conn, 4, 2, 1, "Monday", "2026-10-19T10:26:00")
    assert latest_active_workout_completion(
        conn, meso_number=1, week=1, day_of_week="Monday",
        now="2026-10-19T10:29:00",
    ) == "2026-10-19T10:00:00"


def test_final_set_restore_uses_database_not_card_cache():
    conn = database()
    add(conn, 9, 1, 1, "Monday", "2026-10-19T10:10:00")
    assert latest_active_workout_completion(
        conn, meso_number=1, week=1, day_of_week="Monday",
        now="2026-10-19T10:10:01",
    ) == "2026-10-19T10:10:00"


def test_restore_horizon_preserves_raw_timestamp():
    conn = database()
    add(conn, 1, 1, 1, "Monday", "2026-10-19T10:00:00")
    assert RESTORE_HORIZON_SECONDS == 1800
    assert latest_active_workout_completion(
        conn, meso_number=1, week=1, day_of_week="Monday",
        now="2026-10-19T10:30:00",
    ) == "2026-10-19T10:00:00"
    assert latest_active_workout_completion(
        conn, meso_number=1, week=1, day_of_week="Monday",
        now="2026-10-19T10:30:01",
    ) is None
    assert conn.execute(
        "SELECT completed_at FROM workout_sets"
    ).fetchone()[0] == "2026-10-19T10:00:00"


def test_invalid_latest_timestamp_falls_back_to_next_valid_row():
    conn = database()
    add(conn, 1, 1, 1, "Monday", "2026-10-19T10:00:00")
    add(conn, 1, 1, 1, "Monday", "invalid")
    assert latest_active_workout_completion(
        conn, meso_number=1, week=1, day_of_week="Monday",
        now="2026-10-19T10:05:00",
    ) == "2026-10-19T10:00:00"


def test_main_uses_active_database_context_only():
    source = Path("main.py").read_text()
    block = source[
        source.index("    def sync_active_rest_from_sets("):
        source.index("    def refresh_rest_timer_pill(")
    ]
    for marker in (
        "latest_active_workout_completion(",
        "meso_number=self.current_meso",
        "week=self.current_week",
        "day_of_week=self.current_day",
    ):
        assert marker in block
    assert "latest_completed_timestamp(self.sets)" not in source
    assert "_rest_timer_colors" not in source
    assert "_rest_timer_rendered_phase" not in source
