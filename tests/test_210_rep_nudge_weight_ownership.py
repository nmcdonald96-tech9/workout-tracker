from pathlib import Path

from services.rep_nudge_service import numeric_values_equal

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def test_numeric_weight_equivalence_ignores_formatting():
    assert numeric_values_equal("60", "60.0")
    assert numeric_values_equal("60.00", 60)
    assert not numeric_values_equal("60", "60.5")


def test_untouched_weight_nudge_skips_weight_commit():
    block = method("prepare_rep_nudge_weight", "nudge_active_set_reps")
    assert "field_weight =" in block and "committed_weight =" in block
    assert "if not numeric_values_equal(field_weight, committed_weight):" in block
    assert block.index("if not numeric_values_equal") < block.index("self.commit_weight_edit(")


def test_changed_weight_commits_without_intermediate_feedback_update():
    block = method("prepare_rep_nudge_weight", "nudge_active_set_reps")
    assert '"weight_rep_nudge_preview"' in block
    assert "refresh_feedback=False" in block


def test_same_weight_delayed_blur_preserves_user_owned_reps():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    guard = 'raw_value is not None and numeric_values_equal(raw_value, committed_weight)'
    assert guard in block
    assert '"_same_committed_weight_skipped"' in block
    assert block.index(guard) < block.index('updated = apply_direct_edit(set_data, "w", raw_value)')


def test_different_weight_still_runs_weight_derived_commit():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    assert "new_w = float(raw_val)" in block
    assert "apply_weight_derived_reps(set_data, new_w, new_target_r)" in block


def test_feedback_refresh_can_be_suppressed_for_combined_nudge_flow():
    block = method("commit_weight_edit", "make_weight_commit_handler")
    assert "refresh_feedback=True" in block
    assert block.count("if refresh_feedback else True") == 2
