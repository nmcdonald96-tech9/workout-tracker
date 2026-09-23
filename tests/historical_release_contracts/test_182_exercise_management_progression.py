from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def setup_db(tmp_path,monkeypatch):
    import database
    monkeypatch.setattr(database,'DB_PATH',str(tmp_path/'v182.db'))
    database.init_and_seed_db()
    return database

def test_release_contract():
    source=(ROOT/'constants.py').read_text()
    assert 'APP_VERSION = "1.82.0"' in source
    assert 'DATABASE_SCHEMA_VERSION = 19' in source

def test_unused_intentional_custom_can_be_removed(tmp_path,monkeypatch):
    db=setup_db(tmp_path,monkeypatch)
    db.create_classified_exercise('Big Buster','Abs','trunk_flexion','Bodyweight')
    usage=db.exercise_usage_summary('Big Buster')
    assert usage['can_delete'] is True
    db.delete_custom_exercise_definition('Big Buster')
    with db.get_db() as c:
        assert c.execute("SELECT 1 FROM exercise_dict WHERE name='Big Buster'").fetchone() is None

def test_completed_history_is_preserved(tmp_path,monkeypatch):
    db=setup_db(tmp_path,monkeypatch)
    db.create_classified_exercise('Big Buster','Abs','trunk_flexion','Bodyweight')
    with db.get_db() as c:
        c.execute("INSERT INTO workout_sessions(date,exercise,category,day_of_week,week,status,meso_number) VALUES('2026-09-22','Big Buster','Abs','Monday','1','Completed',1)")
        c.commit()
    usage=db.delete_custom_exercise_definition('Big Buster')
    assert usage['completed_sessions']==1
    with db.get_db() as c:
        assert c.execute("SELECT exercise FROM workout_sessions WHERE exercise='Big Buster'").fetchone()[0]=='Big Buster'

def test_pending_use_blocks_deletion(tmp_path,monkeypatch):
    db=setup_db(tmp_path,monkeypatch)
    db.create_classified_exercise('Big Buster','Abs','trunk_flexion','Bodyweight')
    with db.get_db() as c:
        c.execute("INSERT INTO workout_sessions(date,exercise,category,day_of_week,week,status,meso_number) VALUES('2026-09-22','Big Buster','Abs','Monday','1','Pending',1)")
        c.commit()
    assert db.exercise_usage_summary('Big Buster')['can_delete'] is False
    try: db.delete_custom_exercise_definition('Big Buster')
    except ValueError: pass
    else: raise AssertionError('pending custom exercise deletion should fail')

def test_canonical_deletion_is_blocked(tmp_path,monkeypatch):
    db=setup_db(tmp_path,monkeypatch)
    try: db.delete_custom_exercise_definition('Arnold Press')
    except ValueError: pass
    else: raise AssertionError('canonical deletion should fail')

def test_unified_browsers_and_explainability_are_present():
    source=(ROOT/'main.py').read_text()
    assert source.count('database.exercise_catalog_browser_entries()')>=2
    assert 'confirm_delete_dictionary_exercise' in source
    assert 'Weight-derived reps' in source
    assert 'Readiness-adjusted target' in source
    assert 'User override' in source
    assert 'Normal progression target' in source