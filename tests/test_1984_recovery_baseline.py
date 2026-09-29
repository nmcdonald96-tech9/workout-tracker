from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_known_good_completion_path_is_restored():
 b=method('make_set_done_handler','make_live_updater')
 assert 'self.app.activate_exercise(category_name, self.db_id)' in b
 assert 'request_structural_refresh("exercise_card_structure"' in b
 assert 'exercise_card_revisions' not in b
def test_known_good_weight_feedback_is_restored():
 b=method('refresh_weight_edit_feedback','make_blur_handler')
 assert 'self.reps_fields[set_idx].update()' in b
 assert 'self.plate_container.update()' in b
 assert 'replace_exercise_card_in_place(self)' not in b
def test_add_remove_mounted_list_path_is_retained():
 s=(ROOT/'main.py').read_text();assert 'replace_exercise_card_in_place(self)' in method('request_set_structure_refresh','on_add_set')
 assert 'self.main_canvas.controls[index] = replacement' in method('replace_exercise_card_in_place','remount_main_canvas')
def test_diagnostics_uses_actual_lazy_coordinator():
 b=method('structural_refresh_status','open_diagnostics_dialog')
 assert '_structural_refresh_coordinator' in b and 'if coordinator is None:' in b
 assert 'self.structural_refresh.' not in (ROOT/'main.py').read_text()
def test_later_card_experiments_are_absent():
 s=(ROOT/'main.py').read_text()
 for marker in ('exercise_card_revisions','exercise_card_render_key','resolve_workout_render_key'):assert marker not in s
def test_workflow_compiles_controllers_and_builds_aab():
 s=(ROOT/'.github/workflows/main-android-apk-aab-authentic-packaging.yml').read_text()
 assert 'find app components controllers services views -type f' in s and 'flet build aab' in s
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.4"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
