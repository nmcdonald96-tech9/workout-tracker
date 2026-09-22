from pathlib import Path
import ast
R=Path(__file__).parents[1]
def test_progression_editor_and_card_shortcut():
 s=(R/'main.py').read_text()
 assert 'def open_exercise_progression_editor' in s
 assert 'Modify progression' in s
 assert 'Maximum progression weight (lb)' in s
 assert 'Reset Defaults' in s
 assert 'simulate_progression' in s
 assert 'invalidate_progression_settings_cache(exercise_name)' in s
 assert 'Completed sets and historical targets are never changed.' in s
 ast.parse(s)
def test_unified_library_and_quick_add_fix():
 s=(R/'main.py').read_text()
 assert '📚 Exercise Library' in s
 assert 'MY EXERCISES' in s and 'BROWSE CATALOG' in s
 assert 'not self.exercise_exists_locally(ex_name)' in s
 assert 'not exercise_exists(ex_name)' not in s
def test_version_schema():
 c=(R/'constants.py').read_text();assert 'APP_VERSION = "1.15.1"' in c and 'DATABASE_SCHEMA_VERSION = 11' in c
