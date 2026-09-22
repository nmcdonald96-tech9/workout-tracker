import sqlite3,pytest
from services.backup_service import BackupService
def make_db(path):
 with sqlite3.connect(path) as c:
  for t in ("workout_sessions","workout_sets","exercise_dict","readiness_logs","meso_configs","meso_names"): c.execute(f"CREATE TABLE {t}(id INTEGER)")
  c.execute("CREATE TABLE user_settings(setting_key TEXT PRIMARY KEY,setting_value TEXT)"); c.commit()
def test_round_trip(tmp_path):
 source=tmp_path/"source.db"; restored=tmp_path/"restored.db"; make_db(source); service=BackupService(); encoded=service.create_backup_string(str(source),"1.9.1",10,"now"); restored.write_bytes(service.decode(encoded)); assert service.validate_database(str(restored))
def test_corruption():
 with pytest.raises(Exception): BackupService().decode("not-valid")
