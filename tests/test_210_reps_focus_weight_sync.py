from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def build_card():
    return method("build_card", "_reopen_completed")


def test_committed_weight_and_handoff_marker_are_card_owned():
    init = SOURCE[SOURCE.index("class ExerciseCard"):SOURCE.index("    def make_rpe_updater(")]
    assert "self.committed_weight_values = {}" in init
    assert "self.app._reps_focus_sync_targets = set()" in init
    assert "self.app._committed_weight_values" not in SOURCE
    assert 'set_data["_committed_w"]' not in SOURCE


def test_live_weight_keystrokes_do_not_change_committed_baseline():
    block = method("make_live_updater", "autosave_pending_sets")
    assert "apply_direct_edit(set_data, key_type, raw_val)" in block
    assert "committed_weight_values" not in block


def test_build_resets_card_baseline_to_reconciled_weight():
    card = build_card()
    assert 'self.committed_weight_values[idx] = str(set_data.get("w", ""))' in card
    assert "setdefault" not in card[card.index("self.committed_weight_values"):]
    assert "self._reps_focus_sync_needed" not in card


def test_weight_commit_marks_blur_handoff_and_clears_other_paths():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    assert block.count('if event_name == "weight_blur":') == 2
    assert block.count("self.app._reps_focus_sync_targets.add((self.db_id, set_idx))") == 2
    assert block.count("self.app._reps_focus_sync_targets.discard((self.db_id, set_idx))") == 2
    assert block.count("self.committed_weight_values[set_idx]") == 2


def test_focus_first_commits_then_runs_direct_sync():
    block = method("make_reps_tap_handler", "make_rpe_focus_handler")
    assert "changed_here = not numeric_values_equal(field_weight, committed_weight)" in block
    assert '"weight_reps_focus"' in block
    assert "refresh_feedback=False" in block
    assert "runner(synchronize_focused_reps)" in block


def test_blur_first_marker_still_forces_direct_sync():
    block = method("make_reps_tap_handler", "make_rpe_focus_handler")
    assert "elif target not in self.app._reps_focus_sync_targets:" in block
    assert "self.app._reps_focus_sync_targets.discard(target)" in block
    assert block.index("elif target not in self.app._reps_focus_sync_targets:") < block.index("runner(synchronize_focused_reps)")


def test_reps_focus_uses_explicit_focus_boundaries():
    block = method("make_reps_tap_handler", "make_rpe_focus_handler")
    assert "field.blur()" in block
    assert "field.update()" in block
    assert "field.focus()" in block
    assert "request_local_card_refresh" not in block


def test_reps_field_has_focus_handler_and_existing_paths_remain():
    card = build_card()
    assert "r_f.on_click = self.make_reps_tap_handler(idx)" in card
    assert 'w_f.on_submit = self.make_weight_commit_handler(idx, "weight_submit")' in card
    assert 'w_f.on_blur = self.make_weight_commit_handler(idx, "weight_blur")' in card
    assert "rpe_f.on_focus = self.make_rpe_focus_handler(idx)" in card


def test_rep_nudge_uses_card_committed_baseline():
    block = method("prepare_rep_nudge_weight", "nudge_active_set_reps")
    assert "committed_weight = self.committed_weight_values.get(" in block
    assert "numeric_values_equal(field_weight, committed_weight)" in block
    assert "draft_weight =" not in block


def test_card_local_replacement_preserves_viewport_contract():
    block = SOURCE[SOURCE.index("    def replace_exercise_card_in_place("):SOURCE.index("    def remount_main_canvas(")]
    assert "self.main_canvas.controls[index] = replacement" in block
    assert "self.main_canvas.update()" in block
    assert "rebuild_entire_display" not in block
