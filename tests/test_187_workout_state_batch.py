import sqlite3
from pathlib import Path

from services.workout_state_service import SAVED_SET_WIDTH, load_workout_state

ROOT = Path(__file__).resolve().parents[1]


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
    CREATE TABLE workout_sessions (
      id INTEGER PRIMARY KEY, exercise TEXT, target_weight REAL, target_reps INTEGER,
      status TEXT, movement_type TEXT, category TEXT, workout_order INTEGER,
      day_of_week TEXT, week TEXT, meso_number INTEGER, bodyweight_snapshot REAL, date TEXT
    );
    CREATE TABLE workout_sets (
      session_id INTEGER, set_number INTEGER, weight REAL, reps INTEGER, rpe REAL,
      rest_seconds INTEGER, target_weight REAL, target_reps INTEGER,
      normal_target_weight REAL, normal_target_reps INTEGER, completed_at TEXT,
      is_complete INTEGER, weight_source TEXT, reps_source TEXT
    );
    CREATE TABLE readiness_logs (
      meso_number INTEGER, week TEXT, day_of_week TEXT, sleep REAL, joints REAL, drive REAL
    );
    CREATE TABLE exercise_dict (name TEXT PRIMARY KEY, setup_notes TEXT);
    """)
    return conn


def test_release_contract():
    constants = (ROOT / "constants.py").read_text()
    assert 'APP_VERSION = "1.87.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert (ROOT / "docs/releases/RELEASE_1.87.0.md").exists()


def test_populated_snapshot_preserves_ownership_and_uses_bounded_queries():
    conn = make_conn()
    conn.execute("INSERT INTO workout_sessions VALUES (1,'Calf Machine',195,26,'Pending','Isolation','Calves',1,'Monday','1',1,180,'2026-09-23')")
    conn.execute("INSERT INTO workout_sets VALUES (1,1,205,22,NULL,NULL,195,26,195,30,NULL,0,'user','weight_derived')")
    conn.execute("INSERT INTO readiness_logs VALUES (1,'1','Monday',4,3,4)")
    conn.execute("INSERT INTO exercise_dict VALUES ('Calf Machine','Seat position 4')")
    snapshot = load_workout_state(conn, meso_number=1, week='1', day_of_week='Monday')
    assert snapshot.query_count == 6
    assert len(snapshot.current_rows) == 1
    saved = snapshot.saved_sets[1][0]
    assert len(saved) == SAVED_SET_WIDTH
    assert saved[-2:] == ('user', 'weight_derived')
    context = snapshot.card_context(1, 'Calf Machine', 'Calves')
    assert context['saved_sets'][0][-2:] == ('user', 'weight_derived')
    assert context['readiness_logged'] is True
    assert context['r_score'] == 11
    assert context['saved_note'] == 'Seat position 4'


def test_null_ownership_defaults_to_target():
    conn = make_conn()
    conn.execute("INSERT INTO workout_sessions VALUES (2,'Row',100,10,'Pending','Pull','Back',1,'Monday','1',1,NULL,'2026-09-23')")
    conn.execute("INSERT INTO workout_sets VALUES (2,1,100,10,NULL,NULL,100,10,100,10,NULL,0,NULL,NULL)")
    snapshot = load_workout_state(conn, meso_number=1, week='1', day_of_week='Monday')
    assert snapshot.saved_sets[2][0][-2:] == ('target', 'target')


def test_empty_day_has_stable_empty_contract():
    conn = make_conn()
    snapshot = load_workout_state(conn, meso_number=1, week='1', day_of_week='Sunday')
    assert snapshot.current_rows == ()
    assert snapshot.saved_sets == {}
    assert snapshot.query_count == 2
    assert snapshot.readiness_logged is False


def test_main_consumes_snapshot_service_and_keeps_atomic_drafts():
    main = (ROOT / "main.py").read_text()
    assert 'from services.workout_state_service import load_workout_state' in main
    assert 'workout_snapshot.card_context(' in main
    assert 'self.last_workout_batch_ms = workout_snapshot.load_ms' in main
    assert 'loaded_drafts = []' in main
    assert 'self.app.sets[self.db_id] = loaded_drafts' in main
