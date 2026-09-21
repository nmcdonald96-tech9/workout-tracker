
import importlib


def test_database_exports_authoritative_progression_functions():
    database = importlib.import_module("database")
    service = importlib.import_module("services.progression_service")
    assert database.calculate_set_specific_progression is service.calculate_set_specific_progression
    assert database.classify_set_progression is service.classify_set_progression
    assert database.get_effective_progression_settings is service.get_effective_progression_settings


def test_target_met_progresses_and_high_rpe_holds():
    from services.progression_service import classify_set_progression
    settings = {"reduction_threshold": 0.70, "max_progress_rpe": 9.5, "max_progression_weight": None}
    progressed = classify_set_progression(100, 10, 9.0, 100, 10, 100, 10, settings)
    held = classify_set_progression(100, 10, 10.0, 100, 10, 100, 10, settings)
    assert progressed["decision"] == "progress"
    assert held["decision"] == "hold"
    assert held["reason_code"] == "RPE_CEILING_EXCEEDED"


def test_readiness_resumes_normal_target():
    from services.progression_service import calculate_set_specific_progression
    targets, diagnostics = calculate_set_specific_progression(
        [(90, 8, 8.0, 90, 8, 100, 10)], 100, 10, "Compound",
        equipment_type="Barbell", exercise_name="Bench Press (Medium Grip)"
    )
    assert targets[0] == {"w": 100.0, "r": 10}
    assert diagnostics[0]["decision"] == "resume_normal"


def test_default_barbell_policy_remains_verified_legacy_math():
    from services.progression_service import calculate_set_specific_progression
    targets, diagnostics = calculate_set_specific_progression(
        [(100, 10, 8.0, 100, 10, 100, 10)], 100, 10, "Compound",
        equipment_type="Barbell", exercise_name="Bench Press (Medium Grip)", age=43, profile=0
    )
    assert targets[0] == {"w": 105.0, "r": 10}
    assert diagnostics[0]["decision"] == "progress"
