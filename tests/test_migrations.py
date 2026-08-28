def test_schema(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path)
 from database import init_and_seed_db,get_db
 init_and_seed_db()
 with get_db() as c:
  assert c.execute("SELECT setting_value FROM user_settings WHERE setting_key='schema_version'").fetchone()[0]=='10'
  assert 'max_progression_weight' in {r[1] for r in c.execute('PRAGMA table_info(exercise_dict)')}
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
