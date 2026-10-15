from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def picker_block():
    start = SOURCE.index("    def make_rpe_picker_handler(")
    end = SOURCE.index("    def prepare_rep_nudge_weight(", start)
    return SOURCE[start:end]


def test_apply_and_done_is_available_only_for_active_pending_set():
    block = picker_block()
    assert 'active_idx = next((i for i, row in enumerate(drafts) if not bool(row.get("done"))), -1)' in block
    assert 'can_apply_and_done = self.status == STATUS_PENDING and not is_revision and set_idx == active_idx' in block
    assert 'ft.ElevatedButton("Apply & Done", on_click=apply_and_done)' in block


def test_revision_mode_keeps_apply_without_apply_and_done():
    block = picker_block()
    assert "not is_revision" in block
    assert 'dialog_actions = [ft.TextButton("Cancel", on_click=cancel), ft.ElevatedButton("Apply", on_click=apply)]' in block
    assert "if can_apply_and_done:" in block


def test_apply_and_done_uses_canonical_completion_handler():
    block = picker_block()
    assert "def apply_selection(complete_set=False):" in block
    assert "def apply_and_done(event=None):" in block
    assert "return apply_selection(complete_set=True)" in block
    assert "self.make_set_done_handler(set_idx)(completion_event)" in block
    assert '"value": True, "data": True' in block


def test_apply_and_done_avoids_intermediate_card_refresh():
    block = picker_block()
    complete_branch = block[block.index("if complete_set:"):block.index("return True", block.index("if complete_set:"))]
    assert 'request_local_card_refresh("rpe_picker_applied")' in complete_branch
    assert complete_branch.index("self.make_set_done_handler(set_idx)(completion_event)") < complete_branch.index("else:")
    assert complete_branch.index("else:") < complete_branch.index('request_local_card_refresh("rpe_picker_applied")')


def test_cancel_and_outside_dismiss_remain_noncommitting():
    block = picker_block()
    cancel = block[block.index("def cancel(event=None):"):block.index("def apply_selection", block.index("def cancel(event=None):"))]
    assert "apply_picker_selection" not in cancel
    assert "make_set_done_handler" not in cancel
    assert "on_dismiss=flush_pending_reps_refresh" in block


def test_apply_still_saves_without_completing():
    block = picker_block()
    assert "def apply(event=None):" in block
    assert "return apply_selection(complete_set=False)" in block
