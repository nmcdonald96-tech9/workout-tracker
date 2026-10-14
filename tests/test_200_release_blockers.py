import sqlite3

import pytest

import services.completed_revision_service as revision_service
from services.completed_revision_service import (
    CompletedRevisionError,
    capture_revision_snapshot,
    commit_completed_revision,
    editable_copies,
)
from services.workout_state_service import load_workout_state


def revision_db():
    conn=sqlite3.connect(":memory:")
    conn.executescript("""
    CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise TEXT,movement_type TEXT,status TEXT,date TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER,bodyweight_snapshot REAL,target_weight REAL,target_reps INTEGER);
    CREATE TABLE workout_sets(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id INTEGER,set_number INTEGER,weight REAL,reps INTEGER,rpe REAL,rest_seconds INTEGER,target_weight REAL,target_reps INTEGER,normal_target_weight REAL,normal_target_reps INTEGER,completed_at TEXT,is_complete INTEGER,progression_decision TEXT,progression_reason_code TEXT,progression_reason TEXT,progression_settings_snapshot TEXT,weight_source TEXT,reps_source TEXT);
    CREATE TABLE app_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,action TEXT,details TEXT);
    CREATE TABLE user_settings(setting_key TEXT PRIMARY KEY,setting_value TEXT);
    CREATE TABLE exercise_dict(name TEXT PRIMARY KEY,equipment TEXT);
    INSERT INTO user_settings VALUES('age','52');
    INSERT INTO user_settings VALUES('progression_profile','3');
    INSERT INTO exercise_dict VALUES('DB Press','Dumbbell');
    INSERT INTO workout_sessions VALUES(1,'DB Press','Compound','Completed','2026-10-01',1,'1','Monday',1,181,40,10);
    INSERT INTO workout_sessions VALUES(2,'DB Press','Compound','Pending','2026-10-08',1,'2','Monday',2,181,40,10);
    INSERT INTO workout_sets(session_id,set_number,weight,reps,rpe,rest_seconds,target_weight,target_reps,normal_target_weight,normal_target_reps,completed_at,is_complete,weight_source,reps_source) VALUES
      (1,1,40,10,8,60,40,10,40,10,'2026-10-01T10:00:00',1,'target','target'),
      (1,2,35,11,8,60,35,11,35,11,'2026-10-01T10:02:00',1,'target','target'),
      (1,3,30,12,8,60,30,12,30,12,'2026-10-01T10:04:00',1,'target','target'),
      (2,1,40,10,NULL,NULL,40,10,40,10,NULL,0,'target','target'),
      (2,2,35,11,NULL,NULL,35,11,35,11,NULL,0,'target','target'),
      (2,3,30,12,NULL,NULL,30,12,30,12,NULL,0,'target','target'),
      (2,4,25,13,NULL,NULL,25,13,25,13,NULL,0,'target','target');
    """)
    conn.commit()
    return conn


def test_completed_revision_passes_real_context_and_syncs_each_set(monkeypatch):
    conn=revision_db()
    captured={}
    def fake_recalculate(db,session_id,revised_sets,**kwargs):
        captured.update(kwargs)
        return {"recalculated":True,"next_targets":(
            {"w":42.5,"r":10},{"w":37.5,"r":11},{"w":32.5,"r":12}
        )}
    monkeypatch.setattr(revision_service,"recalculate_after_completed_revision",fake_recalculate)
    snapshot=capture_revision_snapshot(conn,1)
    result=commit_completed_revision(conn,snapshot,editable_copies(snapshot))
    assert captured["equipment_type"]=="Dumbbell"
    assert captured["is_bodyweight"] is False
    assert captured["bodyweight"]==181.0
    assert captured["age"]==52
    assert captured["profile"]==3
    assert result.future_session_ids_updated==(2,)
    rows=conn.execute("SELECT set_number,weight,reps,target_weight,target_reps FROM workout_sets WHERE session_id=2 ORDER BY set_number").fetchall()
    assert rows==[
        (1,42.5,10,42.5,10),(2,37.5,11,37.5,11),
        (3,32.5,12,32.5,12),(4,32.5,12,32.5,12),
    ]


def test_empty_next_targets_fails_closed_and_rolls_back(monkeypatch):
    conn=revision_db()
    before=conn.execute("SELECT * FROM workout_sets ORDER BY id").fetchall()
    monkeypatch.setattr(revision_service,"recalculate_after_completed_revision",
                        lambda *args,**kwargs:{"recalculated":True,"next_targets":()})
    snapshot=capture_revision_snapshot(conn,1)
    with pytest.raises(CompletedRevisionError):
        commit_completed_revision(conn,snapshot,editable_copies(snapshot))
    assert conn.execute("SELECT * FROM workout_sets ORDER BY id").fetchall()==before


def workout_db():
    conn=sqlite3.connect(":memory:")
    conn.executescript("""
    CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise TEXT,target_weight REAL,target_reps INTEGER,status TEXT,movement_type TEXT,category TEXT,workout_order INTEGER,day_of_week TEXT,week TEXT,meso_number INTEGER,date TEXT,bodyweight_snapshot REAL);
    CREATE TABLE workout_sets(session_id INTEGER,set_number INTEGER,weight REAL,reps INTEGER,rpe REAL,rest_seconds INTEGER,target_weight REAL,target_reps INTEGER,normal_target_weight REAL,normal_target_reps INTEGER,completed_at TEXT,is_complete INTEGER,weight_source TEXT,reps_source TEXT);
    CREATE TABLE readiness_logs(meso_number INTEGER,week TEXT,day_of_week TEXT,sleep REAL,joints REAL,drive REAL);
    CREATE TABLE exercise_dict(name TEXT PRIMARY KEY,setup_notes TEXT);
    INSERT INTO workout_sessions VALUES(1,'Bench',100,10,'Pending','Compound','Chest',1,'Monday','1',1,'2026-10-01',181);
    INSERT INTO exercise_dict VALUES('Bench','');
    """)
    conn.commit()
    return conn


def test_workout_loader_closes_only_its_own_transaction():
    conn=workout_db()
    load_workout_state(conn,meso_number=1,week='1',day_of_week='Monday')
    assert conn.in_transaction is False
    conn.execute("BEGIN")
    load_workout_state(conn,meso_number=1,week='1',day_of_week='Monday')
    assert conn.in_transaction is True
    conn.rollback()
