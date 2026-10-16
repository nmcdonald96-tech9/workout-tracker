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
    assert "self._reps_focus_sync_needed = set()" in init
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
    assert "self._reps_focus_sync_needed.discard(idx)" in card


def test_weight_commit_marks_blur_handoff_and_clears_other_paths():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    assert block.count('if event_name == "weight_blur":') == 2
    assert block.count("self._reps_focus_sync_needed.add(set_idx)") == 2
    assert block.count("self._reps_focus_sync_needed.discard(set_idx)") == 2
    assert block.count("self.committed_weight_values[set_idx]") == 2


def test_focus_first_commits_then_requests_card_refresh():
    block = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert "if not numeric_values_equal(field_weight, committed_weight):" in block
    assert '"weight_reps_focus"' in block
    assert "refresh_feedback=False" in block
    assert 'self.request_local_card_refresh("reps_focus_weight_sync")' in block


def test_blur_first_marker_still_forces_card_refresh():
    block = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert "elif set_idx not in self._reps_focus_sync_needed:" in block
    assert "self._reps_focus_sync_needed.discard(set_idx)" in block
    assert block.index("elif set_idx not in self._reps_focus_sync_needed:") < block.index("self.app._autofocus_reps_target")


def test_reps_focus_uses_one_shot_autofocus_target():
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
