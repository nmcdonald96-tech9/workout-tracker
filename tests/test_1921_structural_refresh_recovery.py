from pathlib import Path

import pytest

from services.structural_refresh_service import StructuralRefreshCoordinator

ROOT = Path(__file__).resolve().parents[1]


def test_dispatch_failure_does_not_strand_pending_request():
    calls = []

    def failing_dispatch(callback):
        calls.append(callback)
        raise RuntimeError("dispatch failed")

    coordinator = StructuralRefreshCoordinator(failing_dispatch, lambda request: None)
    with pytest.raises(RuntimeError, match="dispatch failed"):
        coordinator.request("add_set")
    assert not coordinator.scheduled
    assert not coordinator.running

    queued = []
    coordinator._dispatch = queued.append
    assert coordinator.request("remove_set", rebuild_navigation=True)
    queued.pop(0)()


def test_apply_failure_rearms_reentrant_request_and_recovers():
    queued = []
    applied = []
    coordinator = None

    def apply(request):
        applied.append(request)
        if len(applied) == 1:
            coordinator.request("follow_up", rebuild_navigation=True)
            raise RuntimeError("apply failed")

    coordinator = StructuralRefreshCoordinator(queued.append, apply)
    coordinator.request("first")
    with pytest.raises(RuntimeError, match="apply failed"):
        queued.pop(0)()

    assert not coordinator.running
    assert coordinator.scheduled
    assert len(queued) == 1
    queued.pop(0)()
    assert [item.reasons for item in applied] == [("first",), ("follow_up",)]
    assert applied[1].rebuild_navigation


def test_patch_release_contract_and_async_failure_logging():
    constants = (ROOT / "constants.py").read_text()
    main = (ROOT / "main.py").read_text()
    assert 'APP_VERSION = "1.92.1"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert '[structural_refresh] FAILED:' in main
    assert (ROOT / "docs/releases/RELEASE_1.92.1.md").exists()
