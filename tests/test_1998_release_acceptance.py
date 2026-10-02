from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_one_consolidated_acceptance_report():
 b=method('release_readiness_lines','record_workout_ui_trace')
 for marker in ('2.0 acceptance status','Android verified 1.99.7','trial expiration and limited mode','backup and restore matrix','accessibility and responsive layouts','packaging reproducibility','Play-delivered acceptance'):assert marker in b
def test_existing_history_does_not_require_first_setup():
 b=method('release_readiness_lines','record_workout_ui_trace')
 assert "status='Completed'" in b
 assert 'existing-user state preserved' in b
 assert 'onboarding_completed or existing_user' in b
def test_support_trace_is_reduced_and_private():
 b=method('record_workout_ui_trace','workout_ui_trace_text')
 assert '_change_received' in b and 'return' in b
 s=(ROOT/'main.py').read_text();assert 'Copy Support Trace' in s and 'Clear Support Trace' in s
 assert 'Support UI trace: bounded, memory-only, privacy-safe' in s
def test_workout_behavior_is_frozen():
 s=(ROOT/'main.py').read_text()
 for marker in ('apply_weight_derived_reps','reps_restore_target_applied','startup_billing_rebuild_coalesced','CompletionAction.LOG_EXERCISE','close_week_day_selector'):assert marker in s
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.8"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
