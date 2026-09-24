from pathlib import Path

from app.navigation import category_anchor_key, exercise_anchor_key, ordered_day_names
from components.exercise_card import format_target_weight
from services.workout_service import WorkoutStateService, workout_progress

ROOT = Path(__file__).resolve().parents[1]


def test_189_release_contract_and_schema_stability():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.90.1"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert (ROOT / "docs/releases/RELEASE_1.89.0.md").exists()


def test_phase1_helpers_are_not_defined_in_main():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "class WorkoutStateService:" not in source
    assert "def workout_progress(" not in source
    assert "def ordered_day_names(" not in source
    assert "def category_anchor_key(" not in source
    assert "def exercise_anchor_key(" not in source
    assert "def format_target_weight(" not in source
    assert "from services.workout_service import WorkoutStateService, workout_progress" in source
    assert "from app.navigation import category_anchor_key, exercise_anchor_key, ordered_day_names" in source


def test_navigation_contract_is_deterministic():
    assert ordered_day_names() == [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    assert category_anchor_key("Upper Back / Rear Delts") == "category-upper-back---rear-delts"
    assert exercise_anchor_key(42) == "exercise-42"


def test_card_weight_formatting_contract():
    assert format_target_weight(True, 0) == "BW"
    assert format_target_weight(True, 25) == "BW + 25 lbs"
    assert format_target_weight(False, 135) == "135 lbs"
    assert format_target_weight(False, "unknown") == "unknown lbs"


def test_workout_flow_contracts():
    rows = [{"done": True, "rpe": "8"}, {"done": False, "rpe": ""}]
    assert WorkoutStateService.active_set_position(rows) == (2, 2)
    assert WorkoutStateService.next_action(rows) == "Enter RPE, then complete Set 2."
    sessions = [
        (1, "A", 0, 0, "Completed", "Compound", "Chest"),
        (2, "B", 0, 0, "Skipped", "Isolation", "Chest"),
        (3, "C", 0, 0, "Pending", "Compound", "Back"),
    ]
    result = workout_progress(sessions, {1: [{"done": True}], 3: [{"done": False}]})
    assert result == {
        "completed_exercises": 1,
        "skipped_exercises": 1,
        "total_exercises": 3,
        "completed_sets": 1,
        "total_sets": 2,
        "completed_categories": 1,
        "total_categories": 2,
    }


def test_phase1_modules_do_not_import_flet_or_database():
    for relative in ("app/navigation.py", "components/exercise_card.py", "services/workout_service.py"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "import flet" not in source
        assert "import database" not in source
        assert "from database" not in source
