from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_submit_and_blur_pass_current_control_value():
 s=(ROOT/'main.py').read_text()
 assert 'w_f.on_submit = self.make_weight_commit_handler(idx, "weight_submit")' in s
 assert 'w_f.on_blur = self.make_weight_commit_handler(idx, "weight_blur")' in s
 b=method('make_weight_commit_handler','make_blur_handler')
 assert 'getattr(e.control, "value", None)' in b
def test_event_value_becomes_draft_authority_before_calculation():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert b.index('apply_direct_edit(set_data, "w", raw_value)') < b.index('raw_val = str(set_data.get("w", "")).strip()')
 assert b.index('set_data.clear(); set_data.update(updated)') < b.index('orig_e1rm = calculate_e1rm')
def test_target_baseline_remains_immutable():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'orig_w = float(self.set_targets[set_idx]["w"])' in b
 assert 'orig_r = int(self.set_targets[set_idx]["r"])' in b
 assert 'self.set_targets[set_idx]["r"] = new_target_r' not in b
def test_no_structural_refresh_or_card_replacement():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'request_structural_refresh' not in b
 assert 'replace_exercise_card_in_place' not in b
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.7"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
