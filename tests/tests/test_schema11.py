from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_schema11_identity_model():
    c=(ROOT/'constants.py').read_text();d=(ROOT/'database.py').read_text()
    assert 'APP_VERSION = "1.13.0"' in c and 'DATABASE_SCHEMA_VERSION = 11' in c
    for marker in ('catalog_id','movement_family','equipment','angle','exercise_aliases','create_custom_exercise','preview_future_exercise_replacement','apply_future_exercise_replacement'):
        assert marker in d
    ast.parse(d)
def test_final_ui_paths():
    m=(ROOT/'main.py').read_text()
    for marker in ('open_guided_custom_exercise','Not specified is always valid','Add Catalog Exercise','open_future_plan_replacement','Completed sessions and sets are never edited'):
        assert marker in m
    ast.parse(m)