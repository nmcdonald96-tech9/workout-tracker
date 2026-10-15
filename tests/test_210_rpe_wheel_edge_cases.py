from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def test_completed_revision_can_open_and_apply_picker_to_done_draft():
    block = method("make_rpe_picker_handler", "request_local_card_refresh")
    assert block.count("is_revision = self.db_id in self.app.completed_revision_sessions") == 2
    assert '(bool(drafts[set_idx].get("done")) and not is_revision)' in block
    assert '(bool(current[set_idx].get("done")) and not is_revision)' in block


def test_cancel_and_dismiss_flush_pending_reps_visual_restore():
    block = method("make_rpe_picker_handler", "request_local_card_refresh")
    assert 'def flush_pending_reps_refresh(event=None):' in block
    assert 'self.request_local_card_refresh("reps_restore_after_rpe")' in block
    assert 'on_dismiss=flush_pending_reps_refresh' in block
    assert block.index('def cancel(event=None):') < block.index('flush_pending_reps_refresh()', block.index('def cancel(event=None):'))


def test_apply_coalesces_reps_restore_into_picker_refresh():
    block = method("make_rpe_picker_handler", "request_local_card_refresh")
    shared_start = block.index("            def apply_selection(complete_set=False):")
    shared_end = block.index("            picker = ft.CupertinoPicker(", shared_start)
    shared = block[shared_start:shared_end]
    assert 'self._pending_reps_visual_refresh = False' in shared
    assert 'self.request_local_card_refresh("rpe_picker_applied")' in shared
    assert "if complete_set:" in shared


def test_first_use_guide_dismissal_cannot_deadlock_picker():
    guide = method("open_rpe_guide", "maybe_show_rpe_guide")
    assert 'on_dismiss=close' in guide
    field_start = SOURCE.index("            rpe_f = ft.TextField(")
    field_end = SOURCE.index("            self.weight_fields.append", field_start)
    field = SOURCE[field_start:field_end]
    assert "always_call_on_tap=True" in field
    assert "rpe_f.on_click = self.make_rpe_picker_handler(idx, rpe_hint)" in field


def test_guide_copy_distinguishes_picker_from_canonical_range():
    guide = method("open_rpe_guide", "maybe_show_rpe_guide")
    assert "The quick picker covers RPE 6 to 10" in guide
    assert "existing RPE values from 1 to 10" in guide
