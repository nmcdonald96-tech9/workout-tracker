"""One-snapshot workout-state batch loading.

The renderer consumes a stable, named contract instead of coordinating several
queries and positional row shapes inside ``main.py``.
"""
from dataclasses import dataclass
from time import perf_counter

SESSION_COLUMNS = (
    "id", "exercise", "target_weight", "target_reps", "status",
    "movement_type", "category", "workout_order",
)
SAVED_SET_WIDTH = 12

@dataclass(frozen=True)
class WorkoutStateSnapshot:
    current_rows: tuple
    saved_sets: dict
    past_records: dict
    notes: dict
    bodyweight_snapshots: dict
    readiness_logged: bool
    joint_score: float
    readiness_score: float
    query_count: int
    load_ms: float

    def card_context(self, session_id, exercise, category, previous_week_order=None):
        return {
            "readiness_logged": self.readiness_logged,
            "j_score": self.joint_score,
            "r_score": self.readiness_score,
            "saved_sets": list(self.saved_sets.get(session_id, ())),
            "past_records": list(self.past_records.get(exercise, ())),
            "saved_note": self.notes.get(exercise, ""),
            "snap_bw": self.bodyweight_snapshots.get(session_id),
            "category": category,
            "previous_week_order": previous_week_order,
        }

def _placeholders(values):
    return ",".join("?" for _ in values)

def load_workout_state(conn, *, meso_number, week, day_of_week):
    """Load all state needed to render one workout using one DB snapshot."""
    started = perf_counter()
    cursor = conn.cursor()
    query_count = 0
    # Hold one SQLite read transaction across all SELECTs so a concurrent
    # autosave cannot produce a mix of pre-change and post-change card data.
    if not conn.in_transaction:
        cursor.execute("BEGIN")

    cursor.execute(
        "SELECT id, exercise, target_weight, target_reps, status, movement_type, category, COALESCE(workout_order,id) "
        "FROM workout_sessions WHERE day_of_week=? AND week=? AND meso_number=? "
        "ORDER BY category, CASE WHEN status='Pending' THEN 0 ELSE 1 END, COALESCE(workout_order,id), id",
        (day_of_week, week, meso_number),
    )
    query_count += 1
    current_rows = tuple(cursor.fetchall())
    session_ids = tuple(row[0] for row in current_rows)
    exercises = tuple(dict.fromkeys(row[1] for row in current_rows))

    saved_sets = {sid: [] for sid in session_ids}
    past_records = {exercise: [] for exercise in exercises}
    notes = {exercise: "" for exercise in exercises}
    bodyweights = {sid: None for sid in session_ids}

    cursor.execute(
        "SELECT sleep, joints, drive FROM readiness_logs "
        "WHERE meso_number=? AND week=? AND day_of_week=?",
        (meso_number, week, day_of_week),
    )
    query_count += 1
    readiness_row = cursor.fetchone()
    readiness_logged = readiness_row is not None
    joint_score = readiness_row[1] if readiness_logged and readiness_row[1] is not None else 5
    readiness_score = sum(v if v is not None else 5 for v in readiness_row[:3]) if readiness_logged else 15

    if session_ids:
        marks = _placeholders(session_ids)
        cursor.execute(
            f"SELECT session_id, weight, reps, rpe, rest_seconds, target_weight, target_reps, "
            f"normal_target_weight, normal_target_reps, completed_at, is_complete, "
            f"COALESCE(weight_source,'target'), COALESCE(reps_source,'target') "
            f"FROM workout_sets WHERE session_id IN ({marks}) ORDER BY session_id, set_number ASC",
            session_ids,
        )
        query_count += 1
        for row in cursor.fetchall():
            sid, values = row[0], tuple(row[1:])
            if len(values) != SAVED_SET_WIDTH:
                raise ValueError(f"Unexpected saved-set contract width: {len(values)}")
            saved_sets[sid].append(values)

        cursor.execute(
            f"SELECT id, bodyweight_snapshot FROM workout_sessions WHERE id IN ({marks})",
            session_ids,
        )
        query_count += 1
        for sid, snapshot in cursor.fetchall():
            bodyweights[sid] = snapshot

    if exercises:
        marks = _placeholders(exercises)
        cursor.execute(
            f"SELECT name, setup_notes FROM exercise_dict WHERE name IN ({marks})",
            exercises,
        )
        query_count += 1
        for name, note in cursor.fetchall():
            notes[name] = note or ""

        cursor.execute(
            f"SELECT ws.exercise, ws.id, s.set_number, s.weight, s.reps, s.rpe, "
            f"s.target_weight, s.target_reps, s.normal_target_weight, s.normal_target_reps "
            f"FROM workout_sets s JOIN workout_sessions ws ON s.session_id=ws.id "
            f"WHERE ws.exercise IN ({marks}) AND ws.meso_number=? AND ws.status='Completed' "
            f"ORDER BY ws.date DESC, ws.id DESC, s.set_number ASC",
            (*exercises, meso_number),
        )
        query_count += 1
        for row in cursor.fetchall():
            past_records[row[0]].append(tuple(row[1:]))

    return WorkoutStateSnapshot(
        current_rows=current_rows,
        saved_sets={key: tuple(value) for key, value in saved_sets.items()},
        past_records={key: tuple(value) for key, value in past_records.items()},
        notes=notes,
        bodyweight_snapshots=bodyweights,
        readiness_logged=readiness_logged,
        joint_score=joint_score,
        readiness_score=readiness_score,
        query_count=query_count,
        load_ms=round((perf_counter() - started) * 1000, 1),
    )
