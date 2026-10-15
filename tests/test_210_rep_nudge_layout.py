from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"main.py").read_text(encoding="utf-8")
def block():
    start=SOURCE.index("    def build_card(");end=SOURCE.index("    def _reopen_completed(",start);return SOURCE[start:end]
def test_set_rows_remain_single_line_without_footer_toolbar():
    b=block();assert "rep_nudge_bar" not in b and 'ft.Text("Adjust reps"' not in b
    assert 'content=set_row, padding=3' in b
def test_reps_field_remains_editable_and_uncrushed():
    b=block();assert '[set_indicator, w_f, r_f, nudge_slot, rpe_f, complete_set_btn]' in b
    assert "reps_control" not in b
def test_completion_remains_compact_done_action():
    b=block();assert 'content=ft.Text("✓" if set_is_done else "DONE"' in b
    assert "width=54" in b and "height=48" in b
def test_obsolete_inline_stepper_icons_are_absent():
    b=block();assert 'icon="remove"' not in b and 'icon="add"' not in b
