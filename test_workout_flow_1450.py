from pathlib import Path
import sqlite3,database
from constants import STATUS_PENDING
def test_category_order_and_in_category_move(tmp_path):
 p=tmp_path/'x.db';c=sqlite3.connect(p);c.execute("CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,category TEXT,status TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER)");c.executemany("INSERT INTO workout_sessions VALUES(?,?,?,1,'7','Friday',?)",[(1,'Biceps',STATUS_PENDING,1),(2,'Triceps',STATUS_PENDING,2),(3,'Biceps',STATUS_PENDING,3)]);c.commit();c.close();old=database.DB_PATH;database.DB_PATH=str(p)
 try:assert database.reorder_pending_exercise_in_category(1,'7','Friday',3,-1)
 finally:database.DB_PATH=old
 with sqlite3.connect(p) as c:assert c.execute("SELECT id FROM workout_sessions WHERE category='Biceps' ORDER BY workout_order").fetchall()==[(3,),(1,)]
def test_ui_contract():
 t=Path(__file__).with_name('main.py').read_text();assert 'grouped by muscle' in t;assert 'Card ↑' in t and 'A↑' in t;assert 'COALESCE(workout_order,id)' in t;assert 'source_session_id=self.db_id' in t;assert 'detailed_zone' in t
def test_version_schema():
 t=Path(__file__).with_name('constants.py').read_text();assert 'APP_VERSION = "1.45.0"' in t and 'DATABASE_SCHEMA_VERSION = 16' in t
