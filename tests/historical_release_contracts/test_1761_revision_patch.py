from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_and_schema():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.77.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 19' in constants


def test_revision_skip_is_guarded_and_never_uses_rows_to_save():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index("    def on_skip(self, ev):")
    end = source.index("    def on_unskip(self, ev):", start)
    block = source[start:end]
    assert "if self.db_id in self.app.completed_revision_sessions:" in block
    assert "Save or cancel the completed-exercise revision before skipping." in block
    assert "rows_to_save" not in block
    assert "completed_exercise_revision_saved" not in block


def test_successful_revision_save_records_and_clears_revision_state():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index("    def on_save(self, ev):")
    end = source.index("class WorkoutTrackerApp:", start)
    block = source[start:end]
    pop = block.index("revision_snapshot = self.app.completed_revision_sessions.pop")
    saved = block.index('"completed_exercise_revision_saved"')
    recalculated = block.index('"progression_targets_recalculated"')
    assert pop < saved < recalculated
    assert "revision_change_summary(revision_snapshot, revised_values)" in block


def test_combined_android_workflow_report_quotes_are_valid():
    workflow = (ROOT / ".github/workflows/main-android-apk-aab-authentic-packaging.yml").read_text(encoding="utf-8")
    assert 'echo "Permanent signer and package identity: verified"' in workflow
    assert 'echo "Google Play AAB signature and bundle structure: verified"' in workflow
    assert 'verified""' not in workflow
