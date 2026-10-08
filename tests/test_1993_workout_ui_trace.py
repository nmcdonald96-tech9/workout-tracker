from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_trace_is_bounded_and_privacy_safe():
 b=method('record_workout_ui_trace','workout_ui_trace_text')
 assert 'workout_ui_trace_limit' in b
 for prohibited in ('raw_value','draft.get("w"','draft.get("r"','rpe','exercise'): assert prohibited not in b
def test_trace_captures_card_event_and_control_lifecycle():
 s=(ROOT/'main.py').read_text()
 for marker in ('card_created','card_built','weight_submit','weight_blur','_derived_applied','reps_update_started','reps_update_returned','reps_update_local_refresh','local_card_refresh_finished'): assert marker in s
def test_trace_buttons_are_available_in_diagnostics():
 s=(ROOT/'main.py').read_text()
 assert 'Copy Support Trace' in s and 'Clear Support Trace' in s
 assert 'Support UI trace: bounded, memory-only, privacy-safe' in s
def test_weight_event_authority_is_preserved():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'apply_direct_edit(set_data, "w", raw_value)' in b
 assert 'self.set_targets[set_idx]["r"] = new_target_r' not in b
def test_no_card_replacement_or_structural_refresh_in_weight_commit():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'replace_exercise_card_in_place' not in b and 'request_structural_refresh' not in b
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "2.0.0"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
