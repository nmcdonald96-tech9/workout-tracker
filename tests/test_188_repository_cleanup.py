from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.92.1"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert (ROOT / "docs/releases/RELEASE_1.88.0.md").exists()
    assert (ROOT / "docs/releases/RELEASE_1.90.0.md").exists()


def test_duplicate_test_tree_removed():
    assert not (ROOT / "tests/tests").exists()


def test_historical_contracts_are_separated_and_ignored():
    config = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "historical_release_contracts" in config
    historical = ROOT / "tests/historical_release_contracts"
    assert historical.is_dir()
    assert any(historical.glob("test_*.py"))


def test_canonical_test_documentation_exists():
    assert (ROOT / "tests/README.md").exists()
    assert (ROOT / "docs/TESTING.md").exists()


def test_rpe_portrait_label_is_compact_but_validation_remains():
    from services.rpe_service import RPE_ERROR

    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'label="RPE"' in main
    assert 'label="RPE 1-10 • 0.5 steps"' not in main
    assert "RPE means Rate of Perceived Exertion" in main
    assert RPE_ERROR.startswith("RPE must be 1 to 10 in 0.5 steps")


def test_187_snapshot_loader_is_retained():
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from services.workout_state_service import load_workout_state" in main
    assert "workout_snapshot.card_context" in main
    assert "loaded_drafts = []" in main