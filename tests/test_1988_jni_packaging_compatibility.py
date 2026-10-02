from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBSPECS = (
    ROOT / "packages/ironcycle-billing/flutter/ironcycle_billing/pubspec.yaml",
    ROOT / "packages/ironcycle-billing/src/ironcycle_billing/flutter/ironcycle_billing/pubspec.yaml",
)


def test_billing_pubspecs_pin_compatible_jni_flutter():
    for path in PUBSPECS:
        text = path.read_text(encoding="utf-8")
        assert "in_app_purchase: 3.3.0" in text
        assert "in_app_purchase_android: 0.5.0" in text
        assert "jni_flutter: 1.0.3" in text
        assert "jni_flutter: 1.0.4" not in text


def test_packaging_removes_repository_metadata_before_flet_build():
    path = ROOT / ".github/workflows/main-android-apk-aab-authentic-packaging.yml"
    text = path.read_text(encoding="utf-8")
    assert "rm -rf .git" in text
    assert text.index("rm -rf .git") < text.index("flet build apk")


def test_release_remains_1988_schema_20():
    text = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.99.14"' in text
    assert "DATABASE_SCHEMA_VERSION = 20" in text
