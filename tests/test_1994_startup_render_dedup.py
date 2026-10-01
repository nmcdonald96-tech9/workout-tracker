from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def method(name, next_name):
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index(f"    async def {name}(")
    end = source.index(f"    def {next_name}(", start)
    return source[start:end]

def test_owned_startup_reconciliation_does_not_rebuild_workout_twice():
    block = method("reconcile_billing_ownership", "entitlement_snapshot")
    assert 'was_owned = self.entitlement.snapshot().state == LIFETIME_UNLOCKED' in block
    assert 'if reason == "startup" and was_owned:' in block
    assert 'startup_billing_rebuild_coalesced' in block
    assert block.index('if reason == "startup" and was_owned:') < block.index('self.rebuild_entire_display()')

def test_real_entitlement_transition_still_rebuilds():
    block = method("reconcile_billing_ownership", "entitlement_snapshot")
    assert 'billing_rebuild_requested' in block
    assert 'self.rebuild_entire_display()' in block

def test_diagnostic_trace_is_retained():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'Copy UI Trace' in source
    assert 'reps_update_exception' in source
    assert 'card_created' in source

def test_weight_logic_is_not_changed_by_startup_patch():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index('    def commit_weight_edit(')
    end = source.index('    def make_weight_commit_handler(', start)
    block = source[start:end]
    assert 'apply_direct_edit(set_data, "w", raw_value)' in block
    assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in block
    assert 'request_structural_refresh' not in block
    assert 'replace_exercise_card_in_place' not in block

def test_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.99.4"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
