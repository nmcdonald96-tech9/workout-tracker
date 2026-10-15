from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")
def method(start_name,end_name):
    start=SOURCE.index(f"    def {start_name}(");end=SOURCE.index(f"    def {end_name}(",start);return SOURCE[start:end]
def build_card_block():
    return method("build_card","_reopen_completed")
def test_single_48_dp_trigger_replaces_two_inline_buttons():
    b=build_card_block();assert 'nudge_slot = ft.Container(width=48, height=48)' in b
    assert 'content=ft.Text("±", size=22, weight="bold", color="cyan200")' in b and 'self.open_rep_nudge_menu(set_index, ev)' in b
    assert 'icon="remove"' not in b and 'icon="add"' not in b
    assert "reps_control" not in b
def test_active_and_inactive_rows_share_stable_columns():
    b=build_card_block();assert '[set_indicator, w_f, r_f, nudge_slot, rpe_f, complete_set_btn]' in b
    assert 'spacing=3' in b and 'width=54' in b
def test_rpe_uses_compact_label_without_suffix_slot():
    b=build_card_block();assert 'label="RPE"' in b
    assert 'suffix_icon="arrow_drop_down"' not in b
def test_nudge_dialog_has_explicit_minus_plus_and_cancel():
    b=method("open_rep_nudge_menu","nudge_active_set_reps")
    assert 'ft.Text("-1"' in b and 'ft.Text("+1"' in b
    assert b.count('height=48') >= 2
    assert 'ft.TextButton("Cancel"' in b
def test_nudge_prepares_pending_weight_before_rep_ownership():
    prepare=method("prepare_rep_nudge_weight","flush_pending_reps_after_nudge_dialog")
    nudge=method("nudge_active_set_reps","request_local_card_refresh")
    assert 'normalize_reps_source(drafts[set_idx].get("r_source")) == "user"' in prepare
    assert '"weight_rep_nudge_preview"' in prepare
    assert "drafts = self.prepare_rep_nudge_weight(set_idx)" in nudge
    assert nudge.index("drafts = self.prepare_rep_nudge_weight(set_idx)") < nudge.index("updated = nudge_pending_reps(")
