from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def method_block(name, next_name):
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index(f"    def {name}(")
    end = source.index(f"    def {next_name}(", start)
    return source[start:end]


def structure_editor_block():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index("    def open_structure_editor(")
    end = source.index("    def restore_future_schedule(", start)
    return source[start:end]


def test_release_contract_and_schema_stability():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.93.1"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert (ROOT / "docs/releases/RELEASE_1.93.1.md").exists()


def test_weight_blur_uses_value_only_feedback_not_structural_remount():
    block = method_block("make_blur_handler", "build_card")
    assert "self.refresh_weight_edit_feedback(set_idx)" in block
    assert 'request_structural_refresh("exercise_card_structure"' not in block
    assert "self.app.rebuild_entire_display()" not in block


def test_value_only_feedback_has_bounded_anchor_preserving_fallback():
    block = method_block("refresh_weight_edit_feedback", "make_blur_handler")
    assert "reps_field.update()" in block
    assert "self.plate_container.update()" in block
    assert "weight_edit_feedback_fallback" in block
    assert "self.app.pending_scroll_key = exercise_anchor_key(self.db_id)" in block
    assert "rebuild_navigation=False" in block
    assert "remount_canvas=True" in block


def test_reps_and_rpe_blur_remain_non_structural():
    block = method_block("make_blur_handler", "build_card")
    assert 'if key_type == "rpe":' in block
    assert 'if key_type != "w":' in block


def test_superset_assignment_refreshes_immediately_once():
    block = structure_editor_block()
    assert "superset_assignment_changed" in block
    assert "Superset group created." in block
    assert "Superset group removed." in block
    assert "self.pending_scroll_key = exercise_anchor_key(focus_session_id)" in block
    helper = block[block.index("        def refresh_workout_after_group_change"):block.index("        def group(")]
    assert helper.count("request_structural_refresh(") == 1
    assert "remount_canvas=True" in helper


def test_superset_creation_requires_two_pending_selections():
    block = structure_editor_block()
    assert "if len(selected_ids) < 2:" in block
    assert "Select at least two pending exercises." in block


def test_add_remove_set_structural_refresh_contract_is_retained():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    card = source[:source.index("class WorkoutTrackerApp:")]
    assert 'request_structural_refresh("exercise_card_structure"' in card
