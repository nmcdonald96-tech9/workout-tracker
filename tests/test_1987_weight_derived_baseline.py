from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_weight_blur_does_not_mutate_authoritative_rep_target():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'self.set_targets[set_idx]["r"] = new_target_r' not in b
 assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in b
 assert 'set_data.clear(); set_data.update(updated)' in b
def test_clear_weight_restores_authoritative_original_target():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'clear_override(updated, "r", current_target)' in b
def test_repeated_edit_math_has_stable_baseline():
 from database import calculate_e1rm
 orig_w,orig_r=130.0,20
 orig_e1rm=calculate_e1rm(orig_w,orig_r,0.0)
 def derived(new_w):
  return int(round(37-(36*new_w/orig_e1rm))) if new_w<orig_e1rm else 1
 assert derived(300.0)==1
 assert derived(150.0)>1
def test_weight_feedback_path_remains_immediate():
 b=method('refresh_weight_edit_feedback','commit_weight_edit')
 assert 'field=self.reps_fields[set_idx]' in b and 'field.update()' in b
 assert 'self.plate_container.update()' in b
def test_no_card_reconciliation_experiments():
 s=(ROOT/'main.py').read_text()
 for marker in ('exercise_card_revisions','exercise_card_render_key','resolve_workout_render_key'): assert marker not in s
def test_release_contract():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.99.3"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
