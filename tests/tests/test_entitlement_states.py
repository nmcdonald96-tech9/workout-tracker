import json, tempfile
from pathlib import Path
from services.entitlement_service import *

def test_simulations_are_memory_only_and_reversible():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"entitlement.json";svc=EntitlementService(path)
        svc.allow_premium_action();disk_before=path.read_text()
        real=svc.snapshot();assert real.state==TRIAL_ACTIVE
        sim=svc.set_test_simulation(TRIAL_EXPIRED);assert sim.simulated and sim.limited_mode
        allowed,_=svc.allow_premium_action();assert not allowed
        assert path.read_text()==disk_before
        sim=svc.set_test_simulation(LIFETIME_UNLOCKED);assert sim.simulated
        allowed,_=svc.allow_premium_action();assert allowed
        assert path.read_text()==disk_before
        restored=svc.clear_test_simulation();assert not restored.simulated and restored.state==TRIAL_ACTIVE

def test_simulation_disappears_on_restart():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"entitlement.json";svc=EntitlementService(path)
        svc.allow_premium_action();svc.set_test_simulation(LIFETIME_UNLOCKED)
        restarted=EntitlementService(path);assert restarted.snapshot().state==TRIAL_ACTIVE

def test_pending_and_offline_preserve_existing_trial_access():
    with tempfile.TemporaryDirectory() as d:
        svc=EntitlementService(Path(d)/"entitlement.json");svc.allow_premium_action()
        for state in (PURCHASE_CHECK_PENDING,TEMPORARILY_OFFLINE):
            svc.set_test_simulation(state);allowed,snap=svc.allow_premium_action();assert allowed and not snap.limited_mode