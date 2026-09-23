from pathlib import Path

def setup_db(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);import database;database.DB_PATH=str(tmp_path/"identity.db");database.init_and_seed_db();return database

def test_version_schema_and_catalog():
 c=Path(__file__).resolve().parents[1].joinpath("constants.py").read_text();assert 'APP_VERSION = "1.77.0"' in c;assert 'DATABASE_SCHEMA_VERSION = 19' in c
 from exercise_catalog import CATALOG_VERSION
 assert CATALOG_VERSION==5

def test_fresh_catalog_is_canonical(tmp_path,monkeypatch):
 db=setup_db(tmp_path,monkeypatch);s=db.exercise_identity_summary();assert s["total"]==71 and s["canonical"]==71 and s["needs_review"]==0

def test_intentional_custom_is_resolved(tmp_path,monkeypatch):
 db=setup_db(tmp_path,monkeypatch)
 with db.get_db() as c:c.execute("INSERT INTO exercise_dict(name,category,identity_status,is_custom) VALUES('My Movement','Custom','needs_review',0)");c.commit()
 db.mark_exercise_intentional_custom("My Movement");s=db.exercise_identity_summary();assert s["intentional_custom"]==1 and s["needs_review"]==0

def test_display_name_preserves_history(tmp_path,monkeypatch):
 db=setup_db(tmp_path,monkeypatch)
 with db.get_db() as c:c.execute("INSERT INTO workout_sessions(exercise,status) VALUES('Arnold Press','Completed')");c.commit()
 db.set_exercise_display_name("Arnold Press","Rotating Dumbbell Press")
 with db.get_db() as c:
  row=c.execute("SELECT name,display_name,identity_status FROM exercise_dict WHERE name='Arnold Press'").fetchone();history=c.execute("SELECT exercise FROM workout_sessions ORDER BY id DESC LIMIT 1").fetchone()[0]
 assert row==('Arnold Press','Rotating Dumbbell Press','customized_canonical') and history=='Arnold Press'

def test_review_returns_only_needs_review(tmp_path,monkeypatch):
 db=setup_db(tmp_path,monkeypatch)
 with db.get_db() as c:c.execute("INSERT INTO exercise_dict(name,category,movement_family,equipment,identity_status,is_custom) VALUES('Unknown Press','Shoulders','Legacy','Legacy','needs_review',0)");c.commit()
 assert [x['name'] for x in db.uniform_exercise_review()]==['Unknown Press']


def test_schema18_migration_classifies_existing_rows(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);import sqlite3, database
 path=tmp_path/"legacy18.db";database.DB_PATH=str(path)
 with sqlite3.connect(path) as c:
  c.execute("CREATE TABLE exercise_dict(name TEXT PRIMARY KEY,category TEXT,movement_pattern TEXT,setup_notes TEXT,catalog_id TEXT,display_name TEXT,movement_family TEXT,movement_type TEXT,equipment TEXT,angle TEXT,is_custom INTEGER)")
  c.execute("CREATE TABLE user_settings(setting_key TEXT PRIMARY KEY,setting_value TEXT)")
  c.execute("INSERT INTO exercise_dict VALUES('Arnold Press','Shoulders','Legacy','',NULL,'Arnold Press','Legacy','Compound','Legacy','Not specified',0)")
  c.execute("INSERT INTO exercise_dict VALUES('Bench Press (Medium Grip)','Chest','Horizontal Press','','bench_press_medium_grip','Bench Press (Medium Grip)','horizontal_press','Compound','Barbell','Not specified',0)")
  c.commit()
 database.init_and_seed_db()
 with database.get_db() as c:
  states=dict(c.execute("SELECT name,identity_status FROM exercise_dict WHERE name IN ('Arnold Press','Bench Press (Medium Grip)')"))
 assert states['Arnold Press']=='needs_review' and states['Bench Press (Medium Grip)']=='canonical'