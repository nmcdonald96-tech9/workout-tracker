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
    assert 'APP_VERSION = "2.1.0"' in text
    assert "DATABASE_SCHEMA_VERSION = 20" in text

def test_authentic_workflows_use_patched_flet_0865_template():
    workflows = (
        Path(".github/workflows/main-android-apk-authentic-packaging.yml"),
        Path(".github/workflows/main-android-apk-aab-authentic-packaging.yml"),
    )

    required = (
        "--branch v0.86.5",
        "https://github.com/flet-dev/flet.git",
        "$RUNNER_TEMP/flet-v0865",
        'old_line = "  jni: 1.0.0\\n"',
        'source.replace(old_line, "", 1)',
        '--template "$RUNNER_TEMP/flet-v0865"',
        "--template-dir client",
    )

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")

        for marker in required:
            assert marker in text, (
                f"{workflow} is missing required template marker: "
                f"{marker}"
            )

        assert "patch_flet_jni_override.py" not in text
        assert '"flet-cli==0.86.5"' not in text
