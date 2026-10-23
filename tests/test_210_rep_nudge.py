from pathlib import Path
import pytest

from services.rep_nudge_service import REP_NUDGE_DELTAS, nudge_pending_reps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def test_service_supports_only_plus_or_minus_one():
    assert REP_NUDGE_DELTAS == (-1, 1)
    with pytest.raises(ValueError):
        nudge_pending_reps({"r": "10"}, 10, 2)


def test_nudge_marks_reps_user_owned_and_preserves_other_fields():
    draft = {
        "w": "185", "r": "10", "rpe": "8.5",
        "w_source": "target", "r_source": "weight_derived",
        "derived_from_weight": "185",
    }
    updated = nudge_pending_reps(draft, 10, -1, min_reps=1, max_reps=50)
    assert updated["r"] == "9"
    assert updated["r_source"] == "user"
    assert "derived_from_weight" not in updated
    assert updated["w"] == "185"
    assert updated["rpe"] == "8.5"
    assert draft["r"] == "10"


def test_nudge_uses_target_for_blank_and_clamps_to_limits():
    assert nudge_pending_reps({"r": ""}, 8, 1, min_reps=5, max_reps=10)["r"] == "9"
    assert nudge_pending_reps({"r": "5"}, 8, -1, min_reps=5, max_reps=10)["r"] == "5"
    assert nudge_pending_reps({"r": "10"}, 8, 1, min_reps=5, max_reps=10)["r"] == "10"


def test_handler_is_active_pending_only_model_first_and_card_local():
    block = method("nudge_active_set_reps", "request_local_card_refresh")
    assert "self.status != STATUS_PENDING" in block
    assert 'next((i for i, row in enumerate(drafts) if not bool(row.get("done"))), -1)' in block
    assert "set_idx != active_idx" in block
    assert "nudge_pending_reps(" in block
    assert "self.autosave_pending_sets()" in block
    assert "self.refresh_rep_nudge_feedback(set_idx)" in block
    assert ".update()" not in block
    assert "rebuild_entire_display" not in block


def test_ui_shows_direct_stacked_rep_controls_for_active_pending_set():
    assert 'if self.status == STATUS_PENDING and idx == kinetic_active_idx and not set_is_done:' in SOURCE
    assert 'content=ft.Text("+", size=16' in SOURCE
    assert 'content=ft.Text("−", size=18' in SOURCE
    assert 'self.nudge_active_set_reps(set_index, 1)' in SOURCE
    assert 'self.nudge_active_set_reps(set_index, -1)' in SOURCE
    assert "open_rep_nudge_menu" not in SOURCE

def test_nudge_does_not_change_rpe_wheel_or_version_contracts():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "2.1.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert 'RPE_PICKER_OPTIONS = tuple(f"{value / 2:g}" for value in range(12, 21))' in (
        ROOT / "services/rpe_picker_service.py"
    ).read_text(encoding="utf-8")
