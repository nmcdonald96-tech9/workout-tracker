from pathlib import Path
import sqlite3,database
from constants import STATUS_PENDING

def test_group_member_position_swap(tmp_path):
 p=tmp_path/'g.db';c=sqlite3.connect(p);c.execute('CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,meso_number INTEGER,week TEXT,day_of_week TEXT,exercise_group_id TEXT,group_position INTEGER,status TEXT)');c.executemany("INSERT INTO workout_sessions VALUES(?,1,'1','Monday','G',?,?)",[(1,1,STATUS_PENDING),(2,2,STATUS_PENDING),(3,3,STATUS_PENDING)]);c.commit();c.close();old=database.DB_PATH;database.DB_PATH=str(p)
 try:assert database.set_group_member_position(1,'1','Monday',2,-1)
 finally:database.DB_PATH=old
 with sqlite3.connect(p) as c:assert c.execute('SELECT id,group_position FROM workout_sessions ORDER BY id').fetchall()==[(1,2),(2,1),(3,3)]
def test_card_direct_structure_access_and_labels():
 t=Path(__file__).with_name('main.py').read_text();assert 'Workout Structure & Supersets' in t;assert 'source_session_id=self.db_id' in t;assert "tooltip='Earlier group position'" in t;assert "Grouped: A↑/A↓ changes A1/A2/A3 position" in t
def test_three_meaningful_modes_and_standard_dimensions():
 t=Path(__file__).with_name('main.py').read_text();assert '"STANDARD":(False,"compact")' in t;assert '"FOCUS":(True,"compact")' in t;assert '"DETAILED":(False,"detailed")' in t;assert 'padding=8 if self.app.ui_density == "detailed" else 6' in t
def test_schema_and_version():
 t=Path(__file__).with_name('constants.py').read_text();assert 'APP_VERSION = "1.44.0"' in t and 'DATABASE_SCHEMA_VERSION = 16' in t
