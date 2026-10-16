from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def build_card():
    return method("build_card", "_reopen_completed")


def test_committed_weight_state_is_app_owned_not_draft_owned():
    init = SOURCE[SOURCE.index("class ExerciseCard"):SOURCE.index("    def make_rpe_updater(")]
    assert 'self.app._committed_weight_values = {}' in init
    assert 'set_data["_committed_w"]' not in SOURCE
    assert 'drafts[set_idx]["_committed_w"]' not in SOURCE


def test_live_weight_keystrokes_do_not_change_committed_baseline():
    block = method("make_live_updater", "autosave_pending_sets")
    assert "apply_direct_edit(set_data, key_type, raw_val)" in block
    assert "_committed_weight_values" not in block


def test_weight_commit_compares_and_updates_committed_baseline():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    assert 'committed_weight = self.app._committed_weight_values.get(' in block
    assert 'numeric_values_equal(raw_value, committed_weight)' in block
    assert block.count('self.app._committed_weight_values[(self.db_id, set_idx)]') == 2


def test_reps_focus_commits_pending_weight_without_mounted_field_update():
    block = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert '"weight_reps_focus"' in block
    assert "refresh_feedback=False" in block
    assert 'self.request_local_card_refresh("reps_focus_weight_sync")' in block
    assert "refresh_weight_edit_feedback" not in block


def test_reps_focus_sets_one_shot_autofocus_target():
    block = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert 'self.app._autofocus_reps_target = (self.db_id, set_idx)' in block
    card = build_card()
    assert 'autofocus_reps = self.app._autofocus_reps_target == (self.db_id, idx)' in card
    assert 'autofocus=autofocus_reps' in card
    assert 'self.app._autofocus_reps_target = None' in card


def test_reps_field_has_focus_handler_and_existing_paths_remain():
    card = build_card()
    assert "r_f.on_focus = self.make_reps_focus_handler(idx)" in card
    assert 'w_f.on_submit = self.make_weight_commit_handler(idx, "weight_submit")' in card
    assert 'w_f.on_blur = self.make_weight_commit_handler(idx, "weight_blur")' in card
    assert "rpe_f.on_focus = self.make_rpe_focus_handler(idx)" in card


def test_rep_nudge_uses_committed_baseline_not_live_draft_weight():
    block = method("prepare_rep_nudge_weight", "nudge_active_set_reps")
    assert 'committed_weight = self.app._committed_weight_values.get(' in block
    assert 'numeric_values_equal(field_weight, committed_weight)' in block
    assert "draft_weight =" not in block


def test_card_local_replacement_contract_remains_in_place():
    block = SOURCE[SOURCE.index("    def replace_exercise_card_in_place("):SOURCE.index("    def remount_main_canvas(")]
    assert "self.main_canvas.controls[index] = replacement" in block
    assert "self.main_canvas.update()" in block
    assert "rebuild_entire_display" not in block
