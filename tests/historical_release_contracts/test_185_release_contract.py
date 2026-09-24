from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_version_schema_and_release_files():
    c=(ROOT/"constants.py").read_text()
    assert 'APP_VERSION = "1.85.0"' in c
    assert 'DATABASE_SCHEMA_VERSION = 20' in c
    assert (ROOT/"docs/releases/RELEASE_1.85.0.md").exists()
    assert (ROOT/"services/target_ownership_service.py").exists()

def test_main_uses_central_ownership_service_and_rpe_blur_feedback():
    m=(ROOT/"main.py").read_text()
    assert 'from services.target_ownership_service import' in m
    assert 'reconcile_pending_draft' in m
    assert 'RPE must be 1 to 10 in 0.5 steps, such as 8 or 8.5.' in m
    assert 'label="RPE 1-10 • 0.5 steps"' in m
