from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_review_and_catalog_ui_wiring():
    source=(ROOT/'main.py').read_text()
    for marker in ('Review Mesocycle','def open_blueprint_review','WEEKLY DISTRIBUTION','I reviewed the warnings','Create Mesocycle','def open_blueprint_replacement_suggestions','Add and Use'):
        assert marker in source
    assert 'Stamp Custom Meso' not in source
    ast.parse(source)
def test_catalog_add_helper():
    source=(ROOT/'database.py').read_text()
    assert 'def add_catalog_exercise_to_dictionary' in source
    ast.parse(source)
def test_version_schema():
    c=(ROOT/'constants.py').read_text()
    assert 'APP_VERSION = "1.13.0"' in c
    assert 'DATABASE_SCHEMA_VERSION = 11' in c
