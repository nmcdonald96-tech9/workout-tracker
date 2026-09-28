from pathlib import Path
from services.superset_execution_service import resolve_next_group_step,resolve_post_set_action
ROOT=Path(__file__).resolve().parents[1]
def block(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_compatibility_export_exists():assert callable(resolve_next_group_step) and callable(resolve_post_set_action)
def test_database_wrapper_imports():
 import database
 assert callable(database.resolve_next_group_step)
def test_add_remove_use_card_local_refresh():
 helper=block('request_set_structure_refresh','on_add_set')
 assert 'self.build_card()' in helper and 'self.update()' in helper
 assert 'request_structural_refresh(' not in helper and 'preserve_workout_viewport' not in helper
 add=block('on_add_set','on_remove_set');remove=block('on_remove_set','trigger_delete_warning')
 assert 'request_set_structure_refresh("add_set")' in add and 'request_set_structure_refresh("remove_set")' in remove
def test_completion_navigation_still_exists():
 s=(ROOT/'main.py').read_text();assert 'def advance_group_flow' in s and 'pending_scroll_key=exercise_anchor_key' in s.replace(' ','')
def test_compact_skipped_card_retained():
 s=(ROOT/'main.py').read_text();assert 'ExerciseCardMode.SKIPPED_COMPACT' in s and 'SKIPPED' in s and 'Unskip' in s
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.95.2"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
