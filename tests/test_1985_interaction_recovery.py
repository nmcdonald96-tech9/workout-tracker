from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_weight_feedback_is_exact_1952_path():
 b=method('refresh_weight_edit_feedback','make_blur_handler')
 assert 'self.reps_fields[set_idx].update()' in b
 assert 'self.plate_container.update()' in b
 assert 'replace_exercise_card_in_place(self)' not in b
def test_weight_blur_calculates_persists_then_updates_feedback():
 b=method('make_blur_handler','build_card')
 assert 'apply_weight_derived_reps' in b
 assert b.rindex('self.autosave_pending_sets(); self.refresh_weight_edit_feedback(set_idx)') > b.index('apply_weight_derived_reps')
def test_standalone_complete_always_uses_deferred_refresh():
 b=method('make_set_done_handler','make_live_updater'); tail=b[b.index('completion_instruction='):]
 assert 'self.app.activate_exercise' not in tail
 assert 'self.app.pending_scroll_key = exercise_anchor_key(self.db_id)' in tail
 assert 'request_structural_refresh(' in tail and 'remount_canvas=True' in tail
def test_grouped_and_final_completion_paths_are_retained():
 b=method('make_set_done_handler','make_live_updater')
 assert 'self.app.advance_group_flow(self.db_id,set_idx+1)' in b
 assert 'CompletionAction.LOG_EXERCISE' in b and 'CompletionAction.APPLY_EXECUTION' in b
def test_add_remove_set_path_is_1952_path():
 assert 'replace_exercise_card_in_place(self)' in method('request_set_structure_refresh','on_add_set')
def test_week_day_selection_closes_dialog():
 assert 'self.safe_close(dialog)' in method('close_week_day_selector','open_week_day_selector')
 assert 'self.close_week_day_selector()' in method('change_active_week','change_active_day')
 assert 'self.close_week_day_selector()' in method('change_active_day','toggle_add_exercise_form')
def test_diagnostics_uses_lazy_coordinator():
 b=method('structural_refresh_status','open_diagnostics_dialog')
 assert '_structural_refresh_coordinator' in b and 'if coordinator is None:' in b
 assert 'self.structural_refresh.' not in (ROOT/'main.py').read_text()
def test_release_contract():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.98.5"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c

def test_authentic_workflow_matches_1952_package_layout():
 workflow=(ROOT/'.github/workflows/main-android-apk-aab-authentic-packaging.yml').read_text()
 assert 'find app components services views -type f' in workflow
 assert 'find app components controllers services views -type f' not in workflow
