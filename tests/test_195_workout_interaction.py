from pathlib import Path
from components.exercise_card_state import ExerciseCardMode,classify_exercise_card
from services.exercise_completion_service import CompletionAction,resolve_completion_action
ROOT=Path(__file__).resolve().parents[1]
def block(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_card_modes():
 assert classify_exercise_card('Skipped',prescribed_sets=2).mode==ExerciseCardMode.SKIPPED_COMPACT
 assert classify_exercise_card('Completed').mode==ExerciseCardMode.COMPLETED_COMPACT
 assert classify_exercise_card('Pending').editable
 assert classify_exercise_card('Completed',revision_active=True).mode==ExerciseCardMode.REVISION_FULL
def test_skipped_card_is_compact_and_noneditable():
 s=(ROOT/'main.py').read_text();snippet=s[s.index('if card_state.mode == ExerciseCardMode.SKIPPED_COMPACT:'):s.index('if self.status == STATUS_COMPLETED:',s.index('if card_state.mode'))]
 assert 'SKIPPED' in snippet and 'Unskip' in snippet and 'History' in snippet
 for term in ('weight_fields','reps_fields','rpe_fields','on_add_set','on_remove_set','make_set_done_handler'):assert term not in snippet
def test_completion_orchestration():
 assert resolve_completion_action(requested_complete=True,set_index=1,total_sets=2,all_done=True,execution_available=False).action==CompletionAction.LOG_EXERCISE
 assert resolve_completion_action(requested_complete=True,set_index=0,total_sets=2,all_done=False,execution_available=True).action==CompletionAction.APPLY_EXECUTION
 assert resolve_completion_action(requested_complete=False,set_index=0,total_sets=2,all_done=False,execution_available=False).action==CompletionAction.NO_ACTION
def test_add_remove_preserve_exact_offset_without_anchor():
 helper=block('request_set_structure_refresh','on_add_set');assert 'preserve_workout_viewport()' in helper and 'rebuild_navigation=False' in helper and 'remount_canvas=True' in helper
 add=block('on_add_set','on_remove_set');remove=block('on_remove_set','trigger_delete_warning')
 assert 'request_set_structure_refresh("add_set")' in add and 'pending_scroll_key' not in add
 assert 'request_set_structure_refresh("remove_set")' in remove and 'pending_scroll_key' not in remove
def test_viewport_restore_precedes_anchor_navigation():
 s=(ROOT/'main.py').read_text();start=s.index('if self.pending_scroll_offset is not None:');end=s.index('except Exception:',start)
 assert 'scroll_to(offset=restore_offset,duration=0)' in s[start:end]
 assert s.index('elif self.pending_scroll_key:',start)>start
def test_scroll_tracking_is_attached():
 s=(ROOT/'main.py').read_text();assert 'def capture_workout_scroll' in s and 'on_scroll=self.capture_workout_scroll' in s
def test_boundaries_are_framework_neutral():
 for rel in ('components/exercise_card_state.py','services/exercise_completion_service.py','services/superset_execution_service.py'):
  source=(ROOT/rel).read_text();assert 'import flet' not in source and '.commit(' not in source
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.95.1"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
