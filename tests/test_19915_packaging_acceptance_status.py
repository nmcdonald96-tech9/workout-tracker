from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_release_contract():
 c=(ROOT/'constants.py').read_text()
 assert 'APP_VERSION = "1.99.15"' in c
 assert 'DATABASE_SCHEMA_VERSION = 20' in c
 assert 'ENTITLEMENT_TEST_CONTROLS = False' in c

def test_diagnostics_match_release_candidate_reality():
 m=(ROOT/'main.py').read_text()
 assert 'Entitlement test controls: disabled for release-candidate builds; 1.99.9 closed acceptance completed' in m
 assert 'packaging reproducibility: APK Android verified 1.99.14; combined AAB and repeat-build acceptance pending' in m
 assert 'Play-delivered acceptance: pending 2.0 release candidate' in m

def test_both_workflows_target_current_version_and_toolchain():
 for name in ('main-android-apk-authentic-packaging.yml','main-android-apk-aab-authentic-packaging.yml'):
  s=(ROOT/'.github/workflows'/name).read_text()
  assert 'test "$APP_VERSION" = "1.99.15"' in s
  assert 'flutter-version: 3.44.8' in s
  assert '$GITHUB_WORKSPACE/vendor/$BILLING_WHEEL_NAME' in s
  assert 'distribution("ironcycle-billing")' in s
  assert 'rm -rf .git' in s

def test_apk_only_remains_aab_free():
 s=(ROOT/'.github/workflows/main-android-apk-authentic-packaging.yml').read_text()
 assert 'flet build apk' in s
 for marker in ('flet build aab','VERIFIED_AAB','build/aab','jarsigner -verify'):
  assert marker not in s

def test_combined_workflow_retains_play_artifacts():
 s=(ROOT/'.github/workflows/main-android-apk-aab-authentic-packaging.yml').read_text()
 for marker in ('flet build apk','flet build aab','VERIFIED_APK','VERIFIED_AAB','jarsigner -verify'):
  assert marker in s
