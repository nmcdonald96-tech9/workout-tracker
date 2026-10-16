from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(name, next_name):
    start = SOURCE.index(f"    def {name}(")
    end = SOURCE.index(f"    def {next_name}(", start)
    return SOURCE[start:end]


def test_handoff_target_survives_card_replacement():
    init = SOURCE[SOURCE.index("class ExerciseCard"):SOURCE.index("    def make_rpe_updater(")]
    assert 'self.app._reps_focus_sync_targets = set()' in init
    assert "self._reps_focus_sync_needed" not in SOURCE


def test_blur_and_focus_use_application_handoff_target():
    commit = method("commit_weight_edit", "make_weight_commit_handler")
    focus = method("make_reps_focus_handler", "make_rpe_focus_handler")
    marker = 'self.app._reps_focus_sync_targets.add((self.db_id, set_idx))'
    assert commit.count(marker) == 2
    assert '(self.db_id, set_idx) not in self.app._reps_focus_sync_targets' in focus
    assert 'self.app._reps_focus_sync_targets.discard((self.db_id, set_idx))' in focus


def test_coalesced_focus_refresh_requests_one_bounded_follow_up():
    refresh = method("request_local_card_refresh", "open_swap_dialog")
    assert 'if reason == "reps_focus_weight_sync":' in refresh
    assert "self._local_card_refresh_follow_up = True" in refresh
    assert 'current.request_local_card_refresh("reps_focus_weight_sync")' in refresh
    assert "current is not self" in refresh
    assert refresh.count('current.request_local_card_refresh("reps_focus_weight_sync")') == 1


def test_autofocus_target_is_not_consumed_while_building_controls():
    card = method("build_card", "_reopen_completed")
    assert 'autofocus_reps = self.app._autofocus_reps_target == (self.db_id, idx)' in card
    assert 'autofocus=autofocus_reps' in card
    assert 'self.app._autofocus_reps_target = None' not in card


def test_autofocus_target_is_consumed_after_replacement_mount():
    replace = method("replace_exercise_card_in_place", "remount_main_canvas")
    update = replace.index("self.main_canvas.update()")
    clear = replace.index("self._autofocus_reps_target = None")
    assert update < clear
    assert "self._reps_focus_sync_targets.discard(target)" in replace


def test_current_mounted_card_is_used_for_follow_up():
    helper = method("mounted_exercise_card", "replace_exercise_card_in_place")
    assert "exercise_anchor_key(session_id)" in helper
    refresh = method("request_local_card_refresh", "open_swap_dialog")
    assert "current = self.app.mounted_exercise_card(self.db_id)" in refresh
