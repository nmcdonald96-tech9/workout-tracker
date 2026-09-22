import json, tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from services.entitlement_service import EntitlementService, NOT_STARTED, TRIAL_ACTIVE, TRIAL_EXPIRED

def test_trial_lifecycle_and_backup_isolation():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"entitlement.json"; svc=EntitlementService(path,14,"ironcycle_lifetime_unlock")
        assert svc.snapshot().state==NOT_STARTED
        ok,snap=svc.allow_premium_action(); assert ok and snap.state==TRIAL_ACTIVE
        data=json.loads(path.read_text()); data["trial_expires_at"]=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(); path.write_text(json.dumps(data))
        svc=EntitlementService(path,14,"ironcycle_lifetime_unlock"); ok,snap=svc.allow_premium_action(); assert not ok and snap.state==TRIAL_EXPIRED

def test_purchase_is_not_faked():
    with tempfile.TemporaryDirectory() as d:
        svc=EntitlementService(Path(d)/"entitlement.json")
        assert svc.snapshot().billing_available is False
        assert "not connected" in svc.purchase_unavailable_message().lower()
