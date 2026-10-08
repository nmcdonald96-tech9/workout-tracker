from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/'.github/workflows/main-android-apk-aab-authentic-packaging.yml'

def source():return WORKFLOW.read_text()
def test_release_contract_and_rc_controls():
 c=(ROOT/'constants.py').read_text()
 assert 'APP_VERSION = "2.0.0"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
 assert 'ENTITLEMENT_TEST_CONTROLS = False' in c

def test_workflow_is_valid_yaml_and_immutable_checkout():
 data=yaml.safe_load(source());assert data['jobs']['build']['runs-on']=='ubuntu-24.04'
 s=source();assert 'fetch-depth: 0' in s and 'persist-credentials: false' in s
 assert 'git rev-parse HEAD' in s and 'SOURCE_COMMIT' in s

def test_reproducible_source_archive_and_tracked_manifest():
 s=source()
 assert 'git ls-files -z | LC_ALL=C sort -z | xargs -0 sha256sum' in s
 assert 'git archive --format=tar --prefix=IronCycle-source/ HEAD | gzip -n -9' in s
 assert 'SOURCE_ARCHIVE_SHA256.txt' in s and 'cmp --silent' in s

def test_android_artifact_identity_and_hashes():
 s=source()
 for marker in ("versionName='$APP_VERSION'","versionCode='$ANDROID_VERSION_CODE'",'ANDROID_ARTIFACT_SHA256.txt','ANDROID_ARTIFACT_INVENTORY.txt','EXPECTED_PACKAGE_ID'):
  assert marker in s
 assert 'apksigner' in s and 'jarsigner -verify' in s

def test_packaged_dependency_and_billing_evidence_remain():
 s=source()
 for marker in ('msal','requests','jwt','cryptography','billing_pubspec','billing_extension','jni_flutter: 1.0.3'):
  assert marker in s or marker in (ROOT/'packages/ironcycle-billing/flutter/ironcycle_billing/pubspec.yaml').read_text()

def test_evidence_uploaded_with_apk_and_aab():
 s=source();assert '${{ env.VERIFIED_APK }}' in s and '${{ env.VERIFIED_AAB }}' in s
 assert 'release-evidence/' in s and 'IronCycle_Authentic_Packaging_Verification.txt' in s

def test_verified_gates_and_pending_play_rc():
 m=(ROOT/'main.py').read_text()
 assert 'accessibility and responsive layouts: Android verified 1.99.13' in m
 assert 'packaging reproducibility: APK Android verified 1.99.14; combined AAB and repeat-build acceptance pending' in m
 assert 'Play-delivered acceptance: pending 2.0 release candidate' in m

def test_frozen_product_contracts_remain():
 m=(ROOT/'main.py').read_text()
 for marker in ('apply_weight_derived_reps','display_mode_rebuild_finished','Entitlement acceptance profile: 1.99.9','Backup recovery acceptance profile: 1.99.10','Accessibility and layout acceptance profile: 1.99.11'):
  assert marker in m
