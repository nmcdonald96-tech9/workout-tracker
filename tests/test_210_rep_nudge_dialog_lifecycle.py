from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def test_modal_preview_prepares_weight_before_reading_current_reps():
    block = method("open_rep_nudge_menu", "nudge_active_set_reps")
    assert "drafts = self.prepare_rep_nudge_weight(set_idx)" in block
    assert block.index("drafts = self.prepare_rep_nudge_weight(set_idx)") < block.index("current_reps =")
    assert "weight_prepared=True" in block


def test_prepare_weight_preserves_user_owned_reps():
    block = method("prepare_rep_nudge_weight", "flush_pending_reps_after_nudge_dialog")
    ownership = 'normalize_reps_source(drafts[set_idx].get("r_source")) == "user"'
    assert ownership in block
    assert "if not reps_are_user_owned" in block
    assert '"weight_rep_nudge_preview"' in block


def test_cancel_and_dismiss_flush_pending_reps_visual_restore():
    menu = method("open_rep_nudge_menu", "nudge_active_set_reps")
    flush = method("flush_pending_reps_after_nudge_dialog", "open_rep_nudge_menu")
    assert 'self.request_local_card_refresh("reps_restore_after_rep_nudge")' in flush
    assert "self._pending_reps_visual_refresh = False" in flush
    assert "self.flush_pending_reps_after_nudge_dialog()" in menu
    assert "on_dismiss=lambda ev: self.flush_pending_reps_after_nudge_dialog()" in menu


def test_successful_nudge_coalesces_to_one_card_refresh():
    block = method("nudge_active_set_reps", "request_local_card_refresh")
    assert "self._pending_reps_visual_refresh = False" in block
    assert block.count('self.request_local_card_refresh("rep_nudge_applied")') == 1
    assert "reps_restore_after_rep_nudge" not in block


def test_direct_nudge_still_prepares_weight_but_modal_choice_does_not_repeat_it():
    block = method("nudge_active_set_reps", "request_local_card_refresh")
    assert "weight_prepared=False" in block
    assert "if not weight_prepared:" in block
    assert "drafts = self.prepare_rep_nudge_weight(set_idx)" in block
