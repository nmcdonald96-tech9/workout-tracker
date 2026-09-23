from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_release_contract():
    c=(ROOT/"constants.py").read_text()
    assert 'APP_VERSION = "1.83.0"' in c
    assert 'DATABASE_SCHEMA_VERSION = 20' in c

def test_ownership_columns_migrate_and_default(tmp_path,monkeypatch):
    import database
    monkeypatch.setattr(database,"DB_PATH",str(tmp_path/"v183.db"))
    database.init_and_seed_db()
    with database.get_db() as conn:
        cols={r[1] for r in conn.execute("PRAGMA table_info(workout_sets)")}
    assert {"weight_source","reps_source"} <= cols

def test_rpe_and_ownership_wiring():
    source=(ROOT/"main.py").read_text()
    assert 'RPE must be 1 to 10 in 0.5 steps' in source
    assert 'COALESCE(weight_source,\'target\')' in source
    assert 'str(s_data.get("w_source", "target"))' in source
    assert 'Set {index} ownership: User override.' in source