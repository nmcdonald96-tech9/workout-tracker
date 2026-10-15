from pathlib import Path
import pytest

from services.rpe_picker_service import (
    RPE_PICKER_OPTIONS,
    apply_picker_selection,
    picker_index,
    picker_value,
    resolve_picker_default,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def test_wheel_options_are_6_to_10_in_half_steps():
    assert RPE_PICKER_OPTIONS == ("6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10")


def test_default_prefers_current_then_suggested_then_eight():
    assert resolve_picker_default("9", "8") == "9"
    assert resolve_picker_default("", "8.5") == "8.5"
    assert resolve_picker_default("5.5", "7.5") == "7.5"
    assert resolve_picker_default("85", "") == "8"
    assert picker_index("8") == 4


def test_selection_applies_only_rpe_and_rejects_outside_wheel():
    draft = {"w": "185", "r": "10", "rpe": "", "w_source": "target", "r_source": "user"}
    updated = apply_picker_selection(draft, "8.5")
    assert updated == {**draft, "rpe": "8.5"}
    assert draft["rpe"] == ""
    assert picker_value("5.5") is None
    with pytest.raises(ValueError):
        apply_picker_selection(draft, "10.5")


def test_rpe_field_is_read_only_and_opens_picker_without_keyboard():
    assert "ft.CupertinoPicker(" in SOURCE
    assert "rpe_f.on_click = self.make_rpe_picker_handler(idx, rpe_hint)" in SOURCE
    rpe_field = SOURCE[SOURCE.index("            rpe_f = ft.TextField("):SOURCE.index("            self.weight_fields.append", SOURCE.index("            rpe_f = ft.TextField("))]
    assert "read_only=True" in rpe_field
    assert "show_cursor=False" in rpe_field
    assert "keyboard_type=ft.KeyboardType.NUMBER" not in rpe_field
    assert "rpe_f.on_focus = self.make_rpe_focus_handler(idx)" in rpe_field


def test_picker_is_model_first_cancel_safe_and_card_local():
    block = method("make_rpe_picker_handler", "request_local_card_refresh")
    assert 'resolve_picker_default(drafts[set_idx].get("rpe"), suggested_rpe)' in block
    assert 'ft.TextButton("Cancel", on_click=cancel)' in block
    assert "apply_picker_selection(current[set_idx], selected[\"value\"])" in block
    assert "self.autosave_pending_sets()" in block
    assert 'self.request_local_card_refresh("rpe_picker_applied")' in block
    assert ".update()" not in block
    assert "rebuild_entire_display" not in block


def test_existing_weight_to_rpe_focus_contract_is_preserved():
    block = method("make_rpe_focus_handler", "make_blur_handler")
    assert 'normalize_reps_source(draft.get("r_source")) == "user"' in block
    assert '"weight_rpe_focus_skipped_manual_reps"' in block
    assert "self.commit_weight_edit(" in block
    assert "self.maybe_show_rpe_guide(e)" in block
