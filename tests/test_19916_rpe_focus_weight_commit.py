from pathlib import Path


SOURCE = Path("main.py").read_text(encoding="utf-8")


def test_rpe_focus_finishes_same_row_weight_commit():
    assert "def make_rpe_focus_handler(self, set_idx):" in SOURCE
    assert '"rpe_focus_received"' in SOURCE
    assert "weight_field = self.weight_fields[set_idx]" in SOURCE
    assert '"weight_rpe_focus"' in SOURCE


def test_rpe_field_uses_row_specific_focus_handler():
    assert "rpe_f.on_focus = self.make_rpe_focus_handler(idx)" in SOURCE
    assert "rpe_f.on_focus = self.maybe_show_rpe_guide" not in SOURCE


def test_failed_reps_page_flush_is_absent():
    assert '"reps_page_flush_started"' not in SOURCE
    assert '"reps_page_flush_returned"' not in SOURCE


def test_rpe_guide_is_preserved():
    start = SOURCE.index("def make_rpe_focus_handler(self, set_idx):")
    end = SOURCE.index("def make_blur_handler(self, set_idx, key_type):", start)
    handler = SOURCE[start:end]
    assert "self.maybe_show_rpe_guide(e)" in handler
