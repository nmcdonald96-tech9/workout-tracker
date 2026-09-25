from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def active_python_source():
    paths = [ROOT / "main.py"]

    for directory in ("app", "components", "services", "views"):
        paths.extend(sorted((ROOT / directory).glob("*.py")))

    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in paths
        if path.exists()
    )


def test_1911_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")

    assert 'APP_VERSION = "1.92.2"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants


def test_removed_navigation_methods_are_not_called():
    source = active_python_source()

    forbidden = (
        "self.app.exercise_anchor_key(",
        "self.app.category_anchor_key(",
        "self.exercise_anchor_key(",
        "self.category_anchor_key(",
    )

    for expression in forbidden:
        assert expression not in source


def test_navigation_helpers_are_called_directly():
    main = (ROOT / "main.py").read_text(encoding="utf-8")

    assert "from app.navigation import" in main
    assert "exercise_anchor_key" in main
    assert "category_anchor_key" in main

    assert main.count("exercise_anchor_key(self.db_id)") >= 1


def test_pending_set_lifecycle_remains_connected():
    main = (ROOT / "main.py").read_text(encoding="utf-8")

    assert "from services.pending_set_service import (" in main
    assert "save_pending_sets_atomic(" in main
    assert "def flush_pending_set_drafts(self):" in main