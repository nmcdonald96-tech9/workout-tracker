from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
def test_runtime_main_matches_known_working_commit():
 data=(ROOT/'main.py').read_bytes()
 assert hashlib.sha256(data).hexdigest()=='39e522c6064cfa0ee8807984219d7d7c34316dd0d3177828504de651d81dd107'
def test_secure_workflow_removes_git_before_build():
 s=(ROOT/'.github/workflows/main-android-apk-aab-authentic-packaging.yml').read_text()
 assert 'rm -rf .git' in s
 assert s.index('rm -rf .git') < s.index('flet build apk')
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.6"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
