import base64, json, sqlite3, zlib
from pathlib import Path
import pytest
from services.backup_service import BackupService
ROOT=Path(__file__).resolve().parents[1]

def make_db(path):
 with sqlite3.connect(path) as c:
  for table in ("workout_sessions","workout_sets","exercise_dict","readiness_logs","meso_configs","meso_names"):
   c.execute(f"CREATE TABLE {table}(id INTEGER)")
  c.execute("CREATE TABLE user_settings(setting_key TEXT PRIMARY KEY,setting_value TEXT)")
  c.commit()

def test_current_backup_inspection_is_non_destructive_and_metadata_only(tmp_path):
 source=tmp_path/'source.db';make_db(source);svc=BackupService()
 encoded=svc.create_backup_string(str(source),'1.99.10',20,'now')
 report=svc.inspect_backup_string(encoded)
 assert report['ok'] and report['integrity']=='ok'
 assert report['app_version']=='1.99.10' and report['schema_version']=='20'
 assert report['created_at_present'] and report['entitlement_embedded'] is False
 assert source.exists()

def test_invalid_and_corrupt_backups_are_rejected(tmp_path):
 svc=BackupService()
 for payload in ('', 'not-valid', base64.b64encode(b'not-zlib').decode()):
  with pytest.raises(Exception):svc.inspect_backup_string(payload)

def test_missing_required_tables_are_rejected(tmp_path):
 bad=tmp_path/'bad.db'
 with sqlite3.connect(bad) as c:c.execute('CREATE TABLE user_settings(setting_key TEXT,setting_value TEXT)')
 encoded=base64.b64encode(zlib.compress(bad.read_bytes())).decode()
 with pytest.raises(ValueError,match='Missing tables'):BackupService().inspect_backup_string(encoded)

def test_restore_pipeline_contracts_are_present():
 main=(ROOT/'main.py').read_text();db=(ROOT/'database.py').read_text()
 for marker in ('__pre-restore.icbackup','verify_restored_database(temp_db_path, allow_legacy=True)','init_and_seed_db()','post_verification = verify_restored_database(DB_PATH)'):
  assert marker in main
 assert 'def verify_restored_database(path, allow_legacy=False)' in db

def test_cloud_recovery_contracts_are_present():
 cloud=(ROOT/'onedrive_service.py').read_text();main=(ROOT/'main.py').read_text()
 for marker in ('def upload_backup','def latest_manifest','def download_latest','_download_graph_item','e.code!=302','Location'):
  assert marker in cloud
 assert '_cloud_restore_running' in main and 'finally:self._cloud_restore_running=False' in main.replace(' ','')

def test_entitlement_is_separate_from_workout_backup():
 backup=(ROOT/'services/backup_service.py').read_text();main=(ROOT/'main.py').read_text()
 assert 'ironcycle_entitlement.json' not in backup
 assert 'entitlement_embedded' in backup
 assert 'Entitlement storage: separate from workout backups' in main

def test_acceptance_ui_and_diagnostics_are_present():
 main=(ROOT/'main.py').read_text()
 assert 'Backup & Recovery Acceptance' in main
 assert 'Backup recovery acceptance profile: 1.99.10' in main
 assert 'Backup diagnostics data policy: metadata and status only; no backup contents' in main

def test_frozen_workout_and_entitlement_contracts_remain():
 main=(ROOT/'main.py').read_text()
 for marker in ('apply_weight_derived_reps','reps_restore_target_applied','startup_billing_rebuild_coalesced','CompletionAction.LOG_EXERCISE','Entitlement acceptance profile: 1.99.9'):
  assert marker in main

def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.16"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
