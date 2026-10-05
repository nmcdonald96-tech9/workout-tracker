import json
from dataclasses import replace
from pathlib import Path
from services.entitlement_service import (
    EntitlementService, entitlement_access_policy, NOT_STARTED, TRIAL_ACTIVE,
    TRIAL_EXPIRED, LIFETIME_UNLOCKED, PURCHASE_CHECK_PENDING, TEMPORARILY_OFFLINE,
)
ROOT=Path(__file__).resolve().parents[1]

def service(tmp_path):
    return EntitlementService(tmp_path/'entitlement.json',14,'ironcycle_lifetime_unlock')

def test_policy_matrix_preserves_data_and_backup_access(tmp_path):
    svc=service(tmp_path); real=svc.snapshot()
    for state in (NOT_STARTED,TRIAL_ACTIVE,TRIAL_EXPIRED,LIFETIME_UNLOCKED,PURCHASE_CHECK_PENDING,TEMPORARILY_OFFLINE):
        snap=svc.set_test_simulation(state); policy=entitlement_access_policy(snap)
        assert policy['view_history'] and policy['diagnostics'] and policy['data_preserved']
        assert policy['local_backup_export'] and policy['local_backup_restore'] and policy['cloud_backup_restore']
    expired=entitlement_access_policy(svc.set_test_simulation(TRIAL_EXPIRED))
    assert expired['limited_mode'] and not expired['premium_mutation']

def test_active_and_lifetime_allow_premium_mutation(tmp_path):
    svc=service(tmp_path)
    assert entitlement_access_policy(svc.set_test_simulation(TRIAL_ACTIVE))['premium_mutation']
    assert entitlement_access_policy(svc.set_test_simulation(LIFETIME_UNLOCKED))['premium_mutation']

def test_transient_states_preserve_existing_entitled_access(tmp_path):
    svc=service(tmp_path);svc.allow_premium_action()
    for state in (PURCHASE_CHECK_PENDING,TEMPORARILY_OFFLINE):
        policy=entitlement_access_policy(svc.set_test_simulation(state))
        assert policy['premium_mutation'] and policy['transient_access_preserved']

def test_simulations_never_persist_or_create_ownership(tmp_path):
    svc=service(tmp_path); path=tmp_path/'entitlement.json'; svc.snapshot(); before=path.read_text()
    svc.set_test_simulation(LIFETIME_UNLOCKED)
    assert path.read_text()==before
    restarted=EntitlementService(path)
    assert restarted.snapshot().state==NOT_STARTED

def test_acceptance_controls_and_diagnostics_are_present():
    constants=(ROOT/'constants.py').read_text();main=(ROOT/'main.py').read_text()
    assert 'ENTITLEMENT_TEST_CONTROLS = False' in constants
    assert 'Entitlement Acceptance Test' in main
    assert 'entitlement_acceptance_lines' in main
    assert 'Local backup export:' in main and 'Workout data preservation:' in main
    assert 'purchase_token' not in main[main.index('    def entitlement_acceptance_lines'):main.index('    def release_readiness_lines')]

def test_backup_manager_is_not_premium_gated():
    main=(ROOT/'main.py').read_text();a=main.index('    def open_backup_manager(');b=main.index('    def backup_reason_label(',a)
    assert 'require_premium' not in main[a:b]

def test_workout_interaction_contracts_remain_frozen():
    main=(ROOT/'main.py').read_text()
    for marker in ('apply_weight_derived_reps','reps_restore_target_applied','startup_billing_rebuild_coalesced','CompletionAction.LOG_EXERCISE','close_week_day_selector'):
        assert marker in main

def test_release_contract():
    c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.99.15"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
