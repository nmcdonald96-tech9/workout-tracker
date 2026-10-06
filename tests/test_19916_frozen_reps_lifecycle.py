from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


def method(name, next_name):
    start = SOURCE.index(f"    def {name}(")
    end = SOURCE.index(f"    def {next_name}(", start)
    return SOURCE[start:end]


def test_release_contract_stays_schema_20():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.99.16"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert 'ENTITLEMENT_TEST_CONTROLS = False' in constants


def test_blank_reps_blur_never_mutates_event_control():
    block = method("make_blur_handler", "build_card")
    reps = block[block.index('if key_type == "r":'):block.index('if key_type == "rpe":')]
    assert 'clear_override(set_data, "r", current_target)' in reps
    assert 'self.autosave_pending_sets()' in reps
    assert 'e.control.value =' not in reps
    assert 'e.control.update()' not in reps
    assert '"reps_restore_target"' in reps
    assert 'remount_canvas=True' in reps
    assert 'reps_restore_target_applied' in reps


def test_weight_feedback_uses_authoritative_remount_not_stored_fields():
    block = method("refresh_weight_edit_feedback", "commit_weight_edit")
    assert 'self.reps_fields[' not in block
    assert '.value=' not in block.replace('"""', '')
    assert '.update()' not in block
    assert '"weight_edit_feedback"' in block
    assert 'request_structural_refresh(' in block
    assert 'remount_canvas=True' in block


def test_weight_commit_updates_model_before_requesting_repaint():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    derived = block.index('apply_weight_derived_reps(')
    autosave = block.index('self.autosave_pending_sets()', derived)
    repaint = block.index('self.refresh_weight_edit_feedback(set_idx)', autosave)
    assert derived < autosave < repaint


def test_existing_structural_coordinator_yields_before_remount():
    dispatch = method("_dispatch_structural_refresh", "_apply_structural_refresh")
    apply = method("_apply_structural_refresh", "request_structural_refresh")
    assert 'await asyncio.sleep(0)' in dispatch
    assert 'if request.remount_canvas: self.remount_main_canvas_on_rebuild = True' in apply
    assert 'self.rebuild_entire_display()' in apply


def test_workflows_target_hotfix_and_keep_verified_packaging():
    for name in ("main-android-apk-authentic-packaging.yml", "main-android-apk-aab-authentic-packaging.yml"):
        text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert 'test "$APP_VERSION" = "1.99.16"' in text
        assert 'flutter-version: 3.44.8' in text
        assert '$GITHUB_WORKSPACE/vendor/$BILLING_WHEEL_NAME' in text
