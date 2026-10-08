from pathlib import Path


SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def test_manual_reps_block_rpe_focus_weight_recalculation():
    block = method("make_rpe_focus_handler", "make_blur_handler")

    ownership_check = (
        'normalize_reps_source(draft.get("r_source")) == "user"'
    )
    weight_commit = "self.commit_weight_edit("

    assert ownership_check in block
    assert '"weight_rpe_focus_skipped_manual_reps"' in block
    assert weight_commit in block

    assert block.index(ownership_check) < block.index(weight_commit)


def test_rpe_focus_still_commits_non_manual_weight_edits():
    block = method("make_rpe_focus_handler", "make_blur_handler")

    assert "elif set_idx < len(self.weight_fields):" in block
    assert "weight_field = self.weight_fields[set_idx]" in block
    assert '"weight_rpe_focus"' in block


def test_rpe_guide_behavior_is_preserved():
    block = method("make_rpe_focus_handler", "make_blur_handler")

    assert "self.maybe_show_rpe_guide(e)" in block


def test_manual_reps_edit_establishes_user_ownership():
    block = method("make_live_updater", "autosave_pending_sets")

    assert "apply_direct_edit(set_data, key_type, raw_val)" in block


def test_rpe_updater_does_not_recalculate_reps():
    start = SOURCE.index("    def make_rpe_updater(")
    end = SOURCE.index("\n    def ", start + 1)
    block = SOURCE[start:end]

    assert '["rpe"]' in block
    assert "ev.control.value" in block
    assert "apply_weight_derived_reps(" not in block
    assert "commit_weight_edit(" not in block
    assert "refresh_weight_edit_feedback(" not in block
