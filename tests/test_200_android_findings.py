from pathlib import Path
from services.exercise_completion_service import CompletionAction, resolve_completion_action

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'main.py').read_text(encoding='utf-8')

def block(start_marker,end_marker):
    start=SOURCE.index(start_marker)
    end=SOURCE.index(end_marker,start)
    return SOURCE[start:end]

def test_final_grouped_set_logs_even_when_handoff_exists():
    instruction=resolve_completion_action(requested_complete=True,set_index=2,total_sets=3,all_done=True,execution_available=True)
    assert instruction.action==CompletionAction.LOG_EXERCISE

def test_nonfinal_grouped_set_still_applies_execution():
    instruction=resolve_completion_action(requested_complete=True,set_index=0,total_sets=3,all_done=False,execution_available=True)
    assert instruction.action==CompletionAction.APPLY_EXECUTION

def test_done_handler_retains_group_handoff_and_log_paths():
    done=block('    def make_set_done_handler(', '    def make_live_updater(')
    assert 'self.app.advance_group_flow(self.db_id,set_idx+1)' in done
    assert 'CompletionAction.LOG_EXERCISE:self.on_save(None);return' in done
    assert 'CompletionAction.APPLY_EXECUTION:return' in done

def test_library_closes_before_opening_editor_and_returns_fresh():
    opener=block('    def open_dictionary_progression_editor(', '    async def _return_to_exercise_library(')
    assert 'self.safe_close(getattr(self, "dict_dialog", None))' in opener
    assert 'self.page.run_task(self._open_library_progression_editor, exercise_name)' in opener
    editor=block('    def open_exercise_progression_editor(', '    def menu_manage_dict(')
    assert 'if return_to_library:' in editor
    assert 'self.page.run_task(self._return_to_exercise_library, exercise_name)' in editor
    assert 'ft.TextButton("Cancel",on_click=cancel)' in editor

def test_reopened_library_restores_selected_exercise():
    library=block('    def menu_manage_dict(', '    def on_dict_ex_change(')
    assert 'selected_exercise in self.current_dict_mapping' in library
    assert 'self.dict_dropdown.value = selected_exercise' in library
    assert 'self.on_dict_ex_change(None)' in library
