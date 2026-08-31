from pathlib import Path
import ast
R=Path(__file__).parents[1]
def test_android_quick_add_call_path_is_self_contained():
    source=(R/'main.py').read_text()
    assert 'def exercise_exists_locally(self, exercise_name):' in source
    assert 'not self.exercise_exists_locally(ex_name)' in source
    assert 'not exercise_exists(ex_name)' not in source
    ast.parse(source)
def test_database_api_is_complete():
    source=(R/'database.py').read_text()
    assert 'def exercise_exists(exercise_name):' in source
    ast.parse(source)
def test_version_and_schema():
    source=(R/'constants.py').read_text()
    assert 'APP_VERSION = "1.14.1"' in source
    assert 'DATABASE_SCHEMA_VERSION = 11' in source
