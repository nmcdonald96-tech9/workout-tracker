from exercise_catalog import CATALOG_VERSION,resolve_catalog_exercise

def test_catalog_v4_contains_starter_core_exercises():
 assert CATALOG_VERSION==5
 assert resolve_catalog_exercise("Front Plank")["id"]=="front_plank"
 assert resolve_catalog_exercise("Plank")["id"]=="front_plank"
 assert resolve_catalog_exercise("Pallof Press")["id"]=="pallof_press"

def test_uniform_review_preserves_history_contract():
 text=open("database.py",encoding="utf-8").read()
 assert "UPDATE workout_sessions SET exercise" not in text[text.index("def apply_uniform_exercise_link"): ]
 assert "COALESCE(min_reps" in text and "COALESCE(weight_step" in text
