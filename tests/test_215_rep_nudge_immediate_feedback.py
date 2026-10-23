from pathlib import Path

SOURCE = Path("main.py").read_text()


def method(first, second):
    start = SOURCE.index(f"    def {first}(")
    end = SOURCE.index(f"    def {second}(", start)
    return SOURCE[start:end]


def test_nudge_persists_once_then_flushes_mounted_card_in_same_callback():
    block = method("nudge_active_set_reps", "request_local_card_refresh")
    assert "drafts[set_idx].update(updated)" in block
    assert "self.autosave_pending_sets()" in block
    assert "if not self.autosave_pending_sets():" not in block
    assert "self.refresh_rep_nudge_feedback(set_idx)" in block
    assert 'request_local_card_refresh("rep_nudge_applied")' not in block
    assert block.index("drafts[set_idx].update(updated)") < block.index("self.autosave_pending_sets()")
    assert block.index("self.autosave_pending_sets()") < block.index("self.refresh_rep_nudge_feedback(set_idx)")


def test_immediate_feedback_uses_current_mounted_card_and_one_card_update():
    block = method("refresh_rep_nudge_feedback", "open_swap_dialog")
    assert "mounted_card is self" in block
    assert 'getattr(field, "page", None) is card_page' in block
    assert 'field.key = f"reps-{self.db_id}-{set_idx}-{rev}"' in block
    assert 'field.value = str(draft.get("r", ""))' in block
    assert "calculate_plates_per_side" in block
    assert "self.plate_feedback_label.value" in block
    assert "self.plate_container.visible" in block
    assert "self.update()" in block
    assert "field.update()" not in block
    assert 'request_local_card_refresh("rep_nudge_feedback_fallback")' in block
    assert "rebuild_entire_display" not in block
    assert "request_structural_refresh" not in block


def test_nudge_clears_delayed_focus_handoffs_and_advances_revision_once():
    block = method("nudge_active_set_reps", "refresh_rep_nudge_feedback")
    assert "self.app._reps_focus_sync_targets.discard(rev_key)" in block
    assert "self.app._autofocus_reps_target = None" in block
    assert "self.app._reps_field_sync_rev[rev_key]" in block
    assert block.count("nudge_pending_reps(") == 1


def test_rpe_focus_preserves_user_owned_nudged_reps():
    block = method("make_rpe_focus_handler", "make_blur_handler")
    assert 'normalize_reps_source(draft.get("r_source")) == "user"' in block
    assert '"weight_rpe_focus_skipped_manual_reps"' in block
