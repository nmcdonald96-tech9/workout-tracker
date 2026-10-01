from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_readiness_diagnostics_are_privacy_safe_and_actionable():
 b=method('release_readiness_lines','open_diagnostics_dialog')
 for marker in ('database_integrity','billing_ownership','onedrive_graph','onboarding','exercise_identity'): assert marker in b
 for prohibited in ('purchase_token','access_token','refresh_token','payment_details','backup_contents','set_data[','rpe_raw'): assert prohibited not in b
 assert 'clean install, trial expiry, restore matrix, accessibility, Play-delivered acceptance' in b
def test_diagnostics_includes_readiness_section():
 s=(ROOT/'main.py').read_text();a=s.index('    def open_diagnostics_dialog(');b=s.index('    async def copy_text_to_clipboard(',a);b=s[a:b]
 assert '*self.release_readiness_lines(integrity)' in b
def test_verified_workout_baseline_is_untouched():
 s=(ROOT/'main.py').read_text();a=s.index('    def commit_weight_edit(');b=s.index('    def make_weight_commit_handler(',a);weight=s[a:b]
 assert 'self.set_targets[set_idx]["r"] = new_target_r' not in weight
 assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in weight
 complete=method('make_set_done_handler','make_live_updater')
 assert 'self.app.advance_group_flow(self.db_id,set_idx+1)' in complete
def test_week_day_lifecycle_is_retained():
 assert 'self.close_week_day_selector()' in method('change_active_week','change_active_day')
 assert 'self.close_week_day_selector()' in method('change_active_day','toggle_add_exercise_form')
def test_packaging_dependency_locks_are_retained():
 for rel in ('packages/ironcycle-billing/flutter/ironcycle_billing/pubspec.yaml','packages/ironcycle-billing/src/ironcycle_billing/flutter/ironcycle_billing/pubspec.yaml'):
  text=(ROOT/rel).read_text();assert 'jni_flutter: 1.0.3' in text and 'in_app_purchase: 3.3.0' in text and 'in_app_purchase_android: 0.5.0' in text
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.3"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
