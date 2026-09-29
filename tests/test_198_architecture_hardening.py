from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_legacy_superset_adapter_is_retired():
 main=(ROOT/'main.py').read_text();db=(ROOT/'database.py').read_text();svc=(ROOT/'services/superset_execution_service.py').read_text()
 assert 'resolve_next_group_step' not in main+db+svc
 assert 'as_legacy_group_step' not in svc
 assert 'resolve_post_set_action' in main and 'resolve_post_set_action' in svc
def test_card_guidance_uses_typed_instruction():
 s=(ROOT/'main.py').read_text();a=s.index('        group_instruction=None');b=s.index('        chips_row.controls.append',a);x=s[a:b]
 assert 'resolve_post_set_action' in x and 'target_exercise' in x and 'target_set_number' in x
def test_navigation_writes_use_controller_apis():
 s=(ROOT/'main.py').read_text();
 for marker in ('reason="category_jump"','reason="category_toggle"','reason="add_exercise"','reason="activate_exercise"'):assert marker in s
 assert 'workout_view_controller.set_active' in s and 'workout_view_controller.set_collapsed' in s
def test_boundaries_are_framework_and_persistence_neutral():
 for rel in ('controllers/workout_view_controller.py','controllers/workout_viewport_controller.py'):
  s=(ROOT/rel).read_text();assert 'import flet' not in s and 'from database' not in s and 'sqlite3' not in s and '.commit(' not in s
def test_architecture_policy_is_not_duplicated_in_main():
 s=(ROOT/'main.py').read_text();assert 'def resolve_post_set_action(' not in s and 'def category_sort_key(' not in s
 assert 'def preserve_current(' not in s and 'def navigate_to_key(' not in s
def test_android_verified_add_remove_path_is_retained():
 s=(ROOT/'main.py').read_text();assert 'replace_exercise_card_in_place(self)' in s and 'self.main_canvas.controls[index] = replacement' in s
def test_privacy_safe_controller_diagnostics_are_present():
 s=(ROOT/'main.py').read_text();assert 'Workout view controller: active' in s and 'Viewport pending action:' in s and 'Structural refresh coordinator:' in s
 assert 'pending_key' not in s[s.index('"Workout view controller: active"'):s.index('"Unequal group set counts: supported"')]
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.1"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c

def test_authentic_aab_workflow_compiles_controllers():
 workflow=(ROOT/'.github/workflows/main-android-apk-aab-authentic-packaging.yml').read_text()
 assert 'find app components controllers services views -type f' in workflow
 assert 'flet build aab' in workflow
 assert "IronCycle-${{ env.APP_VERSION }}-android-play-artifacts" in workflow
