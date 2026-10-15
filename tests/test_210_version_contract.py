from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_version_advances_without_schema_change():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "2.1.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert 'ENTITLEMENT_TEST_CONTROLS = False' in constants


def test_android_workflows_gate_2_1_and_schema_20():
    for name in (
        "main-android-apk-authentic-packaging.yml",
        "main-android-apk-aab-authentic-packaging.yml",
    ):
        source = (
            ROOT / ".github/workflows" / name
        ).read_text(encoding="utf-8")
        assert 'test "$APP_VERSION" = "2.1.0"' in source
        assert "grep -q 'DATABASE_SCHEMA_VERSION = 20' constants.py" in source
        assert "grep -q 'ENTITLEMENT_TEST_CONTROLS = False' constants.py" in source


def test_diagnostics_separate_2_1_development_from_2_0_baseline():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert '"2.1 development status"' in source
    assert '"2.1 RPE wheel: Android accepted on feature branch"' in source
    assert '"2.1 schema: unchanged at 20"' in source
    assert (
        '"2.1 release channel: development APK only; '
        'not a Play release candidate"' in source
    )
    assert '"2.0 acceptance status (preserved baseline)"' in source
