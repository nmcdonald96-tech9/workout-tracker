from pathlib import Path
import pytest
from services.structural_refresh_service import StructuralRefreshCoordinator

ROOT = Path(__file__).resolve().parents[1]


def test_failed_request_is_preserved_without_hot_retry():
    queued = []
    coordinator = StructuralRefreshCoordinator(queued.append, lambda request: (_ for _ in ()).throw(RuntimeError("apply failed")))
    coordinator.request("add_set", rebuild_navigation=True, remount_canvas=True)
    with pytest.raises(RuntimeError, match="apply failed"):
        queued.pop(0)()
    assert not coordinator.running
    assert not coordinator.scheduled
    assert coordinator.pending
    assert coordinator.pending_reasons == ("add_set",)
    assert coordinator.pending_rebuild_navigation
    assert coordinator.pending_remount_canvas
    assert queued == []


def test_explicit_retry_applies_preserved_request():
    queued, applied = [], []
    fail = True
    def apply(request):
        nonlocal fail
        if fail:
            fail = False
            raise RuntimeError("first failure")
        applied.append(request)
    coordinator = StructuralRefreshCoordinator(queued.append, apply)
    coordinator.request("add_set")
    with pytest.raises(RuntimeError):
        queued.pop(0)()
    assert coordinator.retry_pending()
    queued.pop(0)()
    assert [item.reasons for item in applied] == [("add_set",)]
    assert not coordinator.pending


def test_repeated_failure_does_not_spin():
    queued = []
    coordinator = StructuralRefreshCoordinator(queued.append, lambda request: (_ for _ in ()).throw(RuntimeError("still broken")))
    coordinator.request("add_set")
    with pytest.raises(RuntimeError):
        queued.pop(0)()
    assert queued == []
    assert coordinator.pending


def test_failed_request_merges_with_later_request_and_promotes_flags():
    queued, applied = [], []
    fail = True
    def apply(request):
        nonlocal fail
        if fail:
            fail = False
            raise RuntimeError("first failure")
        applied.append(request)
    coordinator = StructuralRefreshCoordinator(queued.append, apply)
    coordinator.request("add_set", remount_canvas=True)
    with pytest.raises(RuntimeError):
        queued.pop(0)()
    coordinator.request("category_change", rebuild_navigation=True, remount_canvas=False)
    queued.pop(0)()
    request = applied[0]
    assert request.reasons == ("add_set", "category_change")
    assert request.rebuild_navigation
    assert request.remount_canvas


def test_reentrant_request_plus_failure_queues_exactly_one_follow_up():
    queued, applied = [], []
    coordinator = None
    def apply(request):
        applied.append(request)
        if len(applied) == 1:
            coordinator.request("follow_up", rebuild_navigation=True)
            raise RuntimeError("apply failed")
    coordinator = StructuralRefreshCoordinator(queued.append, apply)
    coordinator.request("first")
    with pytest.raises(RuntimeError):
        queued.pop(0)()
    assert len(queued) == 1
    queued.pop(0)()
    assert [item.reasons for item in applied] == [("first",), ("first", "follow_up")]
    assert applied[1].rebuild_navigation
    assert not coordinator.pending and not coordinator.running and not coordinator.scheduled


def test_retry_dispatch_failure_leaves_work_pending():
    queued = []
    coordinator = StructuralRefreshCoordinator(queued.append, lambda request: (_ for _ in ()).throw(RuntimeError("apply failed")))
    coordinator.request("add_set")
    with pytest.raises(RuntimeError):
        queued.pop(0)()
    coordinator._dispatch = lambda callback: (_ for _ in ()).throw(RuntimeError("dispatch failed"))
    with pytest.raises(RuntimeError, match="dispatch failed"):
        coordinator.retry_pending()
    assert coordinator.pending and not coordinator.running and not coordinator.scheduled
    coordinator._dispatch = queued.append
    coordinator._apply = lambda request: None
    assert coordinator.retry_pending()
    queued.pop(0)()
    assert not coordinator.pending


def test_duplicate_reasons_remain_deduplicated():
    queued = []
    coordinator = StructuralRefreshCoordinator(queued.append, lambda request: (_ for _ in ()).throw(RuntimeError("apply failed")))
    coordinator.request("add_set")
    with pytest.raises(RuntimeError):
        queued.pop(0)()
    coordinator.request("add_set")
    assert coordinator.pending_reasons == ("add_set",)


def test_application_logging_and_bounded_retry_contract():
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "[structural_refresh] FAILED:" in main
    assert "[structural_refresh] RETRY_QUEUED:" in main
    assert "[structural_refresh] RETRY_DISPATCH_FAILED:" in main
    failure = main.index("[structural_refresh] FAILED:")
    retry = main.index("coordinator.retry_pending()", failure)
    assert "await asyncio.sleep(0)" in main[failure:retry]


def test_1922_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.92.3"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants
    assert (ROOT / "docs/releases/RELEASE_1.92.2.md").exists()
    assert (ROOT / "docs/validation/VALIDATION_1.92.2.md").exists()
    assert (ROOT / "docs/testing/ANDROID_SMOKE_TEST_1.92.2.md").exists()