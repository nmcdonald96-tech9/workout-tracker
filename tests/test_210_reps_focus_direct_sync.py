from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(name, next_name):
    start = SOURCE.index(f"    def {name}(")
    end = SOURCE.index(f"    def {next_name}(", start)
    return SOURCE[start:end]


def test_focus_sync_uses_existing_reps_control_not_card_replacement():
    focus = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert "reps_field = self.reps_fields[set_idx]" in focus
    assert "request_local_card_refresh" not in focus
    assert "replace_exercise_card_in_place" not in focus
    assert "_autofocus_reps_target" not in focus


def test_sync_blurs_updates_and_refocuses_across_event_boundaries():
    focus = method("make_reps_focus_handler", "make_rpe_focus_handler")
    blur = focus.index("field.blur()")
    value = focus.index('field.value = str(current_drafts[set_idx].get("r", ""))')
    update = focus.index("field.update()")
    refocus = focus.index("field.focus()")
    assert blur < value < update < refocus
    between_blur_and_update = focus[blur:update]
    between_update_and_focus = focus[update:refocus]
    assert "await asyncio.sleep(0)" in between_blur_and_update
    assert "await asyncio.sleep(0)" in between_update_and_focus


def test_both_callback_orders_remain_supported():
    focus = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert "changed_here = not numeric_values_equal(field_weight, committed_weight)" in focus
    assert '"weight_reps_focus"' in focus
    assert "elif target not in self.app._reps_focus_sync_targets:" in focus
    assert "self.app._reps_focus_sync_targets.discard(target)" in focus


def test_programmatic_refocus_does_not_reenter_sync():
    focus = method("make_reps_focus_handler", "make_rpe_focus_handler")
    discard = focus.index("self.app._reps_focus_sync_targets.discard(target)")
    refocus = focus.index("field.focus()")
    assert discard < refocus


def test_stale_card_guard_prevents_old_control_updates():
    focus = method("make_reps_focus_handler", "make_rpe_focus_handler")
    assert "current = self.app.mounted_exercise_card(self.db_id)" in focus
    assert "current is not self" in focus


def test_no_autofocus_replacement_contract_remains():
    assert "_autofocus_reps_target" not in SOURCE
    card = method("build_card", "_reopen_completed")
    assert "autofocus=autofocus_reps" not in card
