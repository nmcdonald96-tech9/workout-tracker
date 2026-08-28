def test_schema_integrity(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path)
 from database import init_and_seed_db,get_db
 from services.migration_service import MigrationInspector
 init_and_seed_db(); i=MigrationInspector(get_db); assert i.schema_version()==10 and i.integrity()=="ok" and "max_progression_weight" in i.columns("exercise_dict")
