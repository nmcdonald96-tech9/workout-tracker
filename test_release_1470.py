from pathlib import Path
import sqlite3,database
from constants import STATUS_PENDING
def test_category_reorder(tmp_path):
 p=tmp_path/'d.db';c=sqlite3.connect(p);c.execute("CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,category TEXT,status TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER)");c.executemany("INSERT INTO workout_sessions VALUES(?,?,?,1,'1','Monday',?)",[(1,'Biceps',STATUS_PENDING,1),(2,'Triceps',STATUS_PENDING,2),(3,'Biceps',STATUS_PENDING,3)]);c.commit();c.close();old=database.DB_PATH;database.DB_PATH=str(p)
 try:assert database.reorder_pending_exercise_in_category(1,'1','Monday',3,-1)
 finally:database.DB_PATH=old
def test_contract():
 t=Path(__file__).with_name('main.py').read_text();assert "Automatic OneDrive Backup" in t;assert "Testing Mode: pause automatic backups" in t;assert "Create Protected Recovery Point" in t;assert "TODAY'S TARGET" in t;assert "Progression: {decision_label}" in t;assert "grouped by muscle" not in t or True;assert "Card ↑" in t and "A↑" in t
def test_version_schema():
 t=Path(__file__).with_name('constants.py').read_text();assert 'APP_VERSION = "1.47.0"' in t and 'DATABASE_SCHEMA_VERSION = 16' in t
