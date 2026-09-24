import sqlite3
from services.workout_state_service import SAVED_SET_WIDTH, load_workout_state


def make_conn():
    conn=sqlite3.connect(':memory:')
    conn.executescript('''
    CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise TEXT,target_weight REAL,target_reps INTEGER,status TEXT,movement_type TEXT,category TEXT,workout_order INTEGER,day_of_week TEXT,week TEXT,meso_number INTEGER,bodyweight_snapshot REAL,date TEXT);
    CREATE TABLE workout_sets(session_id INTEGER,set_number INTEGER,weight REAL,reps INTEGER,rpe REAL,rest_seconds INTEGER,target_weight REAL,target_reps INTEGER,normal_target_weight REAL,normal_target_reps INTEGER,completed_at TEXT,is_complete INTEGER,weight_source TEXT,reps_source TEXT);
    CREATE TABLE readiness_logs(meso_number INTEGER,week TEXT,day_of_week TEXT,sleep REAL,joints REAL,drive REAL);
    CREATE TABLE exercise_dict(name TEXT PRIMARY KEY,setup_notes TEXT);
    ''')
    return conn


def test_populated_snapshot_preserves_ownership_and_bounds_queries():
    conn=make_conn()
    conn.execute("INSERT INTO workout_sessions VALUES (1,'Calf Machine',195,26,'Pending','Isolation','Calves',1,'Monday','1',1,180,'2026-09-23')")
    conn.execute("INSERT INTO workout_sets VALUES (1,1,205,22,NULL,NULL,195,26,195,30,NULL,0,'user','weight_derived')")
    conn.execute("INSERT INTO readiness_logs VALUES (1,'1','Monday',4,3,4)")
    conn.execute("INSERT INTO exercise_dict VALUES ('Calf Machine','Seat position 4')")
    snap=load_workout_state(conn,meso_number=1,week='1',day_of_week='Monday')
    assert snap.query_count==6
    assert len(snap.saved_sets[1][0])==SAVED_SET_WIDTH
    assert snap.saved_sets[1][0][-2:]==('user','weight_derived')
    assert snap.card_context(1,'Calf Machine','Calves')['saved_note']=='Seat position 4'


def test_empty_snapshot_uses_two_queries():
    snap=load_workout_state(make_conn(),meso_number=1,week='1',day_of_week='Sunday')
    assert snap.current_rows==()
    assert snap.query_count==2