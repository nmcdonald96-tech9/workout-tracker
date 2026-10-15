from pathlib import Path

SOURCE = Path("main.py").read_text(encoding="utf-8")


def block(start, end):
    first = SOURCE.index(start)
    return SOURCE[first:SOURCE.index(end, first)]


def test_done_and_apply_done_share_canonical_group_router():
    done = block("    def make_set_done_handler(", "    def make_live_updater(")
    picker = block("    def make_rpe_picker_handler(", "    def prepare_rep_nudge_weight(")
    assert "self.app.resolve_group_flow(self.db_id, set_idx + 1)" in done
    assert "self.app.apply_group_flow_instruction(group_instruction)" in done
    assert "self.make_set_done_handler(set_idx)(completion_event)" in picker


def test_group_handoff_keeps_target_set_and_scroll_destination():
    flow = block("    def resolve_group_flow(", "    def activate_exercise(")
    assert "nxt['pending_set']" in flow
    assert 'exercise_anchor_key(nxt["session_id"])' in flow
    assert "instruction.as_legacy_group_step()" in flow


def test_cyclic_router_is_framework_neutral():
    service = Path("services/superset_execution_service.py").read_text(encoding="utf-8")
    assert "import flet" not in service
    assert "select_cyclic_target" in service
    assert "GROUP_NEXT_CYCLIC" in service
