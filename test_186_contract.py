from pathlib import Path

from services.rpe_service import RPE_ERROR, normalize_rpe
from services.target_ownership_service import TARGET, USER, WEIGHT_DERIVED, ownership_summary, reconcile_pending_draft

ROOT = Path(__file__).resolve().parents[1]


def test_186_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.86.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert (ROOT / "docs/releases/RELEASE_1.86.0.md").exists()


def test_canonical_rpe_contract():
    expected = {1: "1", 1.5: "1.5", 8: "8", "8.5": "8.5", 9.5: "9.5", 10: "10"}
    for raw, normalized in expected.items():
        assert normalize_rpe(raw) == normalized
    for raw in (None, "", 0, 0.5, 8.3, 10.5, 85, -1, "x"):
        assert normalize_rpe(raw) is None
    assert "1 to 10" in RPE_ERROR and "0.5 steps" in RPE_ERROR


def test_explicit_owner_wins_without_number_comparison():
    current = {"w": 130, "r": 12}
    target_owned = reconcile_pending_draft({"w": "145", "r": "16", "w_source": TARGET, "r_source": TARGET}, current)
    assert (target_owned["w"], target_owned["r"]) == ("130", "12")
    user_owned = reconcile_pending_draft({"w": "145", "r": "16", "w_source": USER, "r_source": WEIGHT_DERIVED}, current)
    assert (user_owned["w"], user_owned["r"]) == ("145", "16")


def test_ui_uses_shared_contracts():
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from services.rpe_service import RPE_ERROR, normalize_rpe" in main
    assert 'ownership_summary(draft, today, normal)' in main
    assert "RPE means Rate of Perceived Exertion" in main
