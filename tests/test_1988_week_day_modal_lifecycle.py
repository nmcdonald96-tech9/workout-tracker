from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_selector_owns_and_clears_dialog_reference():
 close=method('close_week_day_selector','open_week_day_selector')
 assert 'getattr(self, "week_day_dialog", None)' in close
 assert 'self.safe_close(dialog)' in close
 assert 'self.week_day_dialog = None' in close
 open_block=method('open_week_day_selector','get_previous_workout_comparison')
 assert 'self.week_day_dialog = dialog' in open_block
 assert 'self.close_week_day_selector()' in open_block
def test_week_change_closes_dialog_before_context_change():
 b=method('change_active_week','change_active_day')
 assert b.index('self.close_week_day_selector()') < b.index('self.set_active_position(')
 assert b.index('self.set_active_position(') < b.index('self.rebuild_entire_display()')
def test_day_change_closes_dialog_before_context_change():
 b=method('change_active_day','toggle_add_exercise_form')
 assert b.index('self.close_week_day_selector()') < b.index('self.current_day = day_str')
 assert b.index('self.current_day = day_str') < b.index('self.rebuild_entire_display()')
def test_weight_baseline_fix_is_untouched():
 s=(ROOT/'main.py').read_text();a=s.index('    def commit_weight_edit(');b=s.index('    def make_weight_commit_handler(',a);block=s[a:b]
 assert 'self.set_targets[set_idx]["r"] = new_target_r' not in block
 assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in block
def test_complete_handler_is_untouched_by_modal_patch():
 b=method('make_set_done_handler','make_live_updater')
 assert 'self.app.advance_group_flow(self.db_id,set_idx+1)' in b
 assert 'CompletionAction.LOG_EXERCISE' in b
def test_release_contract():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.99.9"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
