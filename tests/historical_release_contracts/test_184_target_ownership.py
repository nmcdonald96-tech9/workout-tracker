from pathlib import Path

ROOT = Path(__file__).parents[1]


def valid_rpe(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return 1.0 <= number <= 10.0 and abs(number * 2 - round(number * 2)) <= 0.000001


def test_184_version_and_release_notes():
    assert 'APP_VERSION = "1.85.0"' in (ROOT / "constants.py").read_text(encoding="utf-8")
    assert (ROOT / "docs/releases/RELEASE_1.84.0.md").exists()


def test_pending_target_ownership_is_explicit():
    text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'reconcile_pending_draft' in text
    assert 'services.target_ownership_service' in text
    assert 'if bool(draft.get("done"))' in text
    assert 'if bool(is_complete) and stw is not None' in text


def test_rpe_contract_rejects_invalid_values():
    for value in (1, 1.5, 8, 8.5, 9.5, 10):
        assert valid_rpe(value)
    for value in (0, 0.5, 8.3, 10.5, 85, -1, "x", ""):
        assert not valid_rpe(value)
    text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'number < 1.0 or number > 10.0' in text
    assert 'number * 2 - round(number * 2)' in text
    assert 'How RPE Works' in text
