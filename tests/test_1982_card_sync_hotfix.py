from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_weight_feedback_replaces_card_not_mounted_fields():
 b=method('refresh_weight_edit_feedback','make_blur_handler')
 assert 'replace_exercise_card_in_place(self)' in b
 assert 'reps_fields[set_idx].update()' not in b
 assert 'plate_container.update()' not in b
def test_weight_blur_persists_before_card_refresh():
 b=method('make_blur_handler','build_card')
 assert b.rindex('self.autosave_pending_sets(); self.refresh_weight_edit_feedback(set_idx)') > b.index('apply_weight_derived_reps')
def test_standalone_nonfinal_completion_replaces_current_card():
 b=method('make_set_done_handler','make_live_updater')
 tail=b[b.index('completion_instruction='):]
 assert 'CompletionAction.APPLY_EXECUTION' in tail
 assert 'CompletionAction.LOG_EXERCISE' in tail
 assert 'self.app.replace_exercise_card_in_place(self)' in tail
 assert 'self.app.activate_exercise' not in tail
 assert 'request_structural_refresh("exercise_card_structure"' not in tail[tail.index('if completion_instruction.action==CompletionAction.LOG_EXERCISE'):]
def test_grouped_completion_keeps_deliberate_navigation():
 b=method('make_set_done_handler','make_live_updater')
 assert 'self.app.advance_group_flow(self.db_id,set_idx+1)' in b
 assert 'if completion_instruction.action==CompletionAction.APPLY_EXECUTION:' in b
def test_add_remove_path_is_unchanged():
 s=(ROOT/'main.py').read_text();assert 'replace_exercise_card_in_place(self)' in method('request_set_structure_refresh','on_add_set')
 assert 'self.main_canvas.controls[index] = replacement' in method('replace_exercise_card_in_place','remount_main_canvas')
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.2"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
