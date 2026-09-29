from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name=None):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(')
 b=s.index(f'    def {next_name}(',a) if next_name else len(s);return s[a:b]
def test_week_day_selection_closes_modal_before_context_rebuild():
 s=(ROOT/'main.py').read_text();x=method('close_week_day_selector','open_week_day_selector')
 assert 'self.safe_close(dialog)' in x and 'self.week_day_dialog = None' in x
 for name in ('change_active_week','change_active_day'):
  b=method(name,'toggle_add_exercise_form' if name=='change_active_day' else 'change_active_day')
  assert 'self.close_week_day_selector()' in b
  assert b.index('self.close_week_day_selector()') < b.index('self.rebuild_entire_display()')
def test_execution_instruction_application_is_centralized():
 s=(ROOT/'main.py').read_text();apply=method('apply_execution_instruction','advance_group_flow');advance=method('advance_group_flow','activate_exercise')
 assert 'workout_view_controller.focus_category' in apply
 assert 'workout_viewport_controller.navigate_to_key' in apply
 assert 'self.apply_execution_instruction(instruction)' in advance
def test_viewport_application_has_one_post_mount_path():
 s=(ROOT/'main.py').read_text();rebuild=method('rebuild_entire_display')
 assert 'workout_viewport_controller.consume()' in rebuild
 assert 'ViewportAction.PRESERVE_OFFSET' in rebuild and 'ViewportAction.SCROLL_TO_KEY' in rebuild
def test_transitional_resolver_stays_available_until_callers_are_gone():
 from services.superset_execution_service import resolve_post_set_action
 assert callable(resolve_post_set_action)
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.2"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
