from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_insights_ui_wiring():
    source=(ROOT/'main.py').read_text()
    for marker in ('def open_exercise_insights','Exercise insights','Why this trend?','Observational only'):
        assert marker in source
    ast.parse(source)
def test_final_version_schema():
    c=(ROOT/'constants.py').read_text()
    assert 'APP_VERSION = "1.12.1"' in c
    assert 'DATABASE_SCHEMA_VERSION = 10' in c