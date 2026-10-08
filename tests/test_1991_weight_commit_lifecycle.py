from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_submit_and_blur_share_one_commit_handler():
 s=(ROOT/'main.py').read_text()
 assert 'w_f.on_submit = self.make_weight_commit_handler(idx, "weight_submit")' in s
 assert 'w_f.on_blur = self.make_weight_commit_handler(idx, "weight_blur")' in s
 b=method('make_weight_commit_handler','make_blur_handler')
 assert 'self.commit_weight_edit(set_idx, getattr(e.control, "value", None), event_name)' in b
def test_commit_uses_immutable_target_baseline():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'orig_w = float(self.set_targets[set_idx]["w"])' in b
 assert 'orig_r = int(self.set_targets[set_idx]["r"])' in b
 assert 'self.set_targets[set_idx]["r"] = new_target_r' not in b
 assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in b
def test_commit_is_safe_when_submit_then_blur_repeat_same_weight():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert b.count('self.autosave_pending_sets()') >= 2
 assert 'self.refresh_weight_edit_feedback(set_idx)' in b
 assert 'request_structural_refresh' not in b
 assert 'replace_exercise_card_in_place' not in b
def test_clear_weight_restores_target_owned_values():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'clear_override(set_data, "w", current_target)' in b
 assert 'clear_override(updated, "r", current_target)' in b
def test_manual_reps_then_later_weight_remains_left_to_right_authority():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'apply_weight_derived_reps' in b
 live=method('make_live_updater','autosave_pending_sets')
 assert 'apply_direct_edit(set_data, key_type, raw_val)' in live
def test_verified_interactions_remain_present():
 s=(ROOT/'main.py').read_text()
 assert 'self.close_week_day_selector()' in method('change_active_week','change_active_day')
 done=method('make_set_done_handler','make_live_updater')
 assert 'CompletionAction.LOG_EXERCISE' in done and 'self.app.advance_group_flow' in done
def test_readiness_diagnostics_remain_present():
 assert '2.0 acceptance status' in method('release_readiness_lines','open_diagnostics_dialog')
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "2.0.0"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
