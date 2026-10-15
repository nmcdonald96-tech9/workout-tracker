from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def build_card_block():
    return method("build_card", "_reopen_completed")


def test_stacked_slot_replaces_popup_trigger():
    block = build_card_block()

    assert 'nudge_slot = ft.Container(width=44, height=48)' in block
    assert 'content=ft.Text("+", size=16' in block
    assert 'content=ft.Text("−", size=18' in block
    assert "open_rep_nudge_menu" not in SOURCE


def test_active_and_inactive_rows_share_stable_columns():
    block = build_card_block()

    assert (
        "[set_indicator, w_f, r_f, nudge_slot, "
        "rpe_f, complete_set_btn]"
    ) in block
    assert "spacing=3" in block
    assert "width=44" in block
    assert "width=54" in block


def test_rpe_uses_compact_label_without_suffix_slot():
    block = build_card_block()

    assert 'label="RPE"' in block
    assert 'suffix_icon="arrow_drop_down"' not in block


def test_nudge_prepares_pending_weight_before_rep_ownership():
    prepare = method(
        "prepare_rep_nudge_weight",
        "nudge_active_set_reps",
    )
    nudge = method(
        "nudge_active_set_reps",
        "request_local_card_refresh",
    )

    assert (
        'normalize_reps_source('
        'drafts[set_idx].get("r_source")) == "user"'
    ) in prepare
    assert '"weight_rep_nudge_preview"' in prepare
    assert (
        "drafts = self.prepare_rep_nudge_weight(set_idx)"
    ) in nudge
