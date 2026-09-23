from pathlib import Path

def setup_db(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);import database;database.DB_PATH=str(tmp_path/"display.db");database.init_and_seed_db();return database

def test_version_schema():
 c=Path(__file__).resolve().parents[1].joinpath("constants.py").read_text();assert 'APP_VERSION = "1.78.0"' in c;assert 'DATABASE_SCHEMA_VERSION = 19' in c

def test_resolver_reset_and_stable_identity(tmp_path,monkeypatch):
 db=setup_db(tmp_path,monkeypatch);stable='Overhand EZ Bar Curl';db.set_exercise_display_name(stable,'A1 Overhand EZ Bar Curl');assert db.exercise_display_name(stable)=='A1 Overhand EZ Bar Curl'
 with db.get_db() as c:before=c.execute("SELECT name,catalog_id,identity_status FROM exercise_dict WHERE name=?",(stable,)).fetchone()
 assert before==(stable,'overhand_ez_bar_curl','customized_canonical');db.restore_canonical_display_name(stable)
 with db.get_db() as c:after=c.execute("SELECT name,display_name,catalog_id,identity_status FROM exercise_dict WHERE name=?",(stable,)).fetchone()
 assert after==(stable,stable,'overhand_ez_bar_curl','canonical')

def test_main_wiring_is_non_destructive():
 s=Path(__file__).resolve().parents[1].joinpath('main.py').read_text();assert 'exercise_display_name(self.exercise)' in s;assert 'Change Display Name' in s;assert 'Restore Canonical Name' in s;assert 'UPDATE workout_sessions SET exercise = ? WHERE exercise = ?' not in s