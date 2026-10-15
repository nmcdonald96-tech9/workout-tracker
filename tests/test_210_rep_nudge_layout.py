from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")
def build_card_block():
    start = SOURCE.index("    def build_card(")
    end = SOURCE.index("    def _reopen_completed(", start)
    return SOURCE[start:end]
def test_active_stepper_stays_inline_without_footer_toolbar():
    b=build_card_block(); assert "rep_nudge_bar" not in b; assert 'ft.Text("Adjust reps"' not in b
    assert 'ft.Text("-1 REP"' not in b and 'ft.Text("+1 REP"' not in b
    assert "[set_indicator, w_f, reps_control, rpe_f, complete_set_btn]" in b
    assert 'content=set_row, padding=3' in b
def test_inline_stepper_keeps_editable_field_and_48_dp_targets():
    b=build_card_block(); assert "reps_control = r_f" in b and "r_f.expand = True" in b
    assert b.count('icon="remove"')==1 and b.count('icon="add"')==1
    assert b.count("width=48")>=2 and b.count("height=48")>=3
def test_stepper_is_active_pending_only():
    b=build_card_block(); assert 'if self.status == STATUS_PENDING and idx == kinetic_active_idx and not set_is_done:' in b
    assert "expand=4" in b and 'top=ft.BorderSide(1, "cyan700")' in b
def test_completion_is_compact_consistent_done_control():
    b=build_card_block(); assert 'content=ft.Text("✓" if set_is_done else "DONE"' in b
    assert "width=58" in b and '"Complete final set and log exercise"' in b
    assert '"DONE + LOG"' not in b and '"COMPLETE"' not in b
def test_row_spacing_is_reduced_for_portrait_fit():
    b=build_card_block(); assert 'alignment="start", vertical_alignment="center", spacing=4' in b
