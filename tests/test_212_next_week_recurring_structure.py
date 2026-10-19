import json
import sqlite3
from pathlib import Path

import database


def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE exercise_dict(
          name TEXT PRIMARY KEY,category TEXT,movement_type TEXT,catalog_id TEXT,
          is_custom INTEGER DEFAULT 0,identity_status TEXT
        );
        CREATE TABLE exercise_aliases(
          alias TEXT PRIMARY KEY,catalog_id TEXT,exercise_name TEXT,source TEXT,
          confirmed INTEGER DEFAULT 0
        );
        CREATE TABLE meso_configs(meso_number INTEGER PRIMARY KEY,blueprint_json TEXT);
        CREATE TABLE workout_sessions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,date TEXT,exercise TEXT,category TEXT,
          day_of_week TEXT,week TEXT,target_weight REAL,target_reps INTEGER,status TEXT,
          movement_type TEXT,meso_number INTEGER,schedule_origin_day TEXT,
          schedule_exception INTEGER DEFAULT 0,skip_reason TEXT,workout_order INTEGER,
          exercise_group_id TEXT,group_position INTEGER
        );
        """
    )
    return conn


def test_structured_blueprint_preserves_order_and_superset(tmp_path, monkeypatch):
    path = tmp_path / "ironcycle.db"; conn = make_db(path)
    exercises = [
        ("Dumbbell Lateral Raise", "Shoulders", "Isolation", "lateral-raise", 0, "canonical"),
        ("High Incline Dumbbell Shoulder Press", "Shoulders", "Compound", "high-incline-press", 0, "canonical"),
    ]
    conn.executemany("INSERT INTO exercise_dict VALUES(?,?,?,?,?,?)", exercises)
    blueprint = {"Monday": [
        {"exercise": exercises[0][0], "identity_key": "catalog:lateral-raise", "order": 4, "group": "PS1", "group_position": 1},
        {"exercise": exercises[1][0], "identity_key": "catalog:high-incline-press", "order": 5, "group": "PS1", "group_position": 2},
    ]}
    conn.execute("INSERT INTO meso_configs VALUES(1,?)", (json.dumps(blueprint),))
    conn.executemany(
        "INSERT INTO workout_sessions(exercise,category,day_of_week,week,target_weight,target_reps,status,movement_type,meso_number,schedule_origin_day,workout_order) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        [(exercises[0][0], "Shoulders", "Monday", "1", 25, 12, "Completed", "Isolation", 1, "Monday", 4),
         (exercises[1][0], "Shoulders", "Monday", "1", 55, 10, "Completed", "Compound", 1, "Monday", 5)],
    )
    conn.commit(); conn.close(); monkeypatch.setattr(database, "DB_PATH", str(path))
    template = database.get_recurring_week_template(1, "1")
    assert [(x["workout_order"], x["exercise_group_id"], x["group_position"]) for x in template] == [
        (4, "PS1", 1), (5, "PS1", 2)
    ]
    assert [(x["target_weight"], x["target_reps"]) for x in template] == [(25, 12), (55, 10)]


def test_legacy_string_blueprint_and_alias_use_canonical_identity(tmp_path, monkeypatch):
    path = tmp_path / "ironcycle.db"; conn = make_db(path)
    conn.execute("INSERT INTO exercise_dict VALUES(?,?,?,?,?,?)", ("Canonical Press", "Chest", "Compound", "press-1", 0, "canonical"))
    conn.execute("INSERT INTO exercise_aliases VALUES(?,?,?,?,?)", ("Old Custom Press", "press-1", "Canonical Press", "migration", 1))
    conn.execute("INSERT INTO meso_configs VALUES(1,?)", (json.dumps({"Monday": ["Old Custom Press"]}),))
    conn.execute(
        "INSERT INTO workout_sessions(exercise,category,day_of_week,week,target_weight,target_reps,status,movement_type,meso_number,schedule_origin_day,workout_order) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        ("Canonical Press", "Chest", "Monday", "1", 100, 8, "Completed", "Compound", 1, "Monday", 1),
    )
    conn.commit(); conn.close(); monkeypatch.setattr(database, "DB_PATH", str(path))
    template = database.get_recurring_week_template(1, "1")
    assert len(template) == 1
    assert template[0]["identity_key"] == "catalog:press-1"
    assert template[0]["exercise"] == "Canonical Press"
    assert template[0]["target_weight"] == 100


def test_same_identity_on_two_origin_days_is_not_deduplicated(tmp_path, monkeypatch):
    path = tmp_path / "ironcycle.db"; conn = make_db(path)
    conn.execute("INSERT INTO exercise_dict VALUES(?,?,?,?,?,?)", ("Cable Raise", "Shoulders", "Isolation", "raise-1", 0, "canonical"))
    conn.execute("INSERT INTO meso_configs VALUES(1,?)", (json.dumps({"Monday": ["Cable Raise"], "Thursday": ["Cable Raise"]}),))
    conn.commit(); conn.close(); monkeypatch.setattr(database, "DB_PATH", str(path))
    template = database.get_recurring_week_template(1, "1")
    assert [(x["identity_key"], x["day"]) for x in template] == [
        ("catalog:raise-1", "Monday"), ("catalog:raise-1", "Thursday")
    ]


def test_quick_add_can_persist_and_is_idempotent(tmp_path):
    path = tmp_path / "ironcycle.db"; conn = make_db(path)
    conn.execute("INSERT INTO exercise_dict VALUES(?,?,?,?,?,?)", ("Rear Delt Fly", "Shoulders", "Isolation", "rear-delt-fly", 0, "canonical"))
    conn.execute("INSERT INTO meso_configs VALUES(1,?)", (json.dumps({"Monday": []}),))
    assert database.add_exercise_to_recurring_blueprint(conn, 1, "Monday", "Rear Delt Fly")
    assert not database.add_exercise_to_recurring_blueprint(conn, 1, "Monday", "Rear Delt Fly")
    blueprint = json.loads(conn.execute("SELECT blueprint_json FROM meso_configs").fetchone()[0])
    assert blueprint["Monday"] == [{
        "exercise": "Rear Delt Fly", "identity_key": "catalog:rear-delt-fly",
        "order": 1, "group": None, "group_position": None,
    }]


def test_next_week_ui_and_insert_contracts_are_present():
    source = Path("main.py").read_text()
    assert 'self.wizard_add_scope' in source
    assert 'text="This workout only"' in source
    assert 'text="This and future workouts"' in source
    assert 'add_exercise_to_recurring_blueprint(' in source
    assert 'item.get("exercise_group_id")' in source
    assert 'item.get("group_position")' in source
    assert 'item.get("workout_order")' in source
    assert 'recurrence_key=(item["identity_key"],item["day"])' in source
    assert "Saved to the recurring plan; no future workout has been generated yet." in source
