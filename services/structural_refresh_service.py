"""Coalesced post-callback structural refresh coordination.

The coordinator is framework-neutral. It merges repeated structure-changing
requests, runs at most one apply callback at a time, and preserves failed work
for one bounded application-level recovery attempt or a later explicit retry.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class StructuralRefreshRequest:
    reasons: tuple[str, ...]
    rebuild_navigation: bool
    remount_canvas: bool


class StructuralRefreshCoordinator:
    def __init__(self, dispatch: Callable, apply: Callable):
        self._dispatch = dispatch
        self._apply = apply
        self._reasons = []
        self._rebuild_navigation = False
        self._remount_canvas = False
        self._scheduled = False
        self._running = False

    @property
    def pending(self):
        return bool(self._reasons)

    @property
    def pending_reasons(self):
        return tuple(self._reasons)

    @property
    def pending_rebuild_navigation(self):
        return self._rebuild_navigation

    @property
    def pending_remount_canvas(self):
        return self._remount_canvas

    @property
    def scheduled(self):
        return self._scheduled

    @property
    def running(self):
        return self._running

    def _merge_request(self, request):
        for reason in request.reasons:
            if reason not in self._reasons:
                self._reasons.append(reason)
        self._rebuild_navigation |= bool(request.rebuild_navigation)
        self._remount_canvas |= bool(request.remount_canvas)

    def _schedule_drain(self):
        """Schedule one drain without stranding pending work on failure."""
        self._scheduled = True
        try:
            self._dispatch(self.drain)
        except Exception:
            self._scheduled = False
            raise

    def request(self, reason, *, rebuild_navigation=False, remount_canvas=True):
        label = str(reason or "structural_change").strip() or "structural_change"
        self._merge_request(
            StructuralRefreshRequest(
                (label,), bool(rebuild_navigation), bool(remount_canvas)
            )
        )
        if self._scheduled or self._running:
            return False
        self._schedule_drain()
        return True

    def retry_pending(self):
        """Schedule preserved work once when no drain is active or queued."""
        if not self._reasons or self._scheduled or self._running:
            return False
        self._schedule_drain()
        return True

    def drain(self):
        """Apply one snapshot while keeping failed and reentrant work recoverable."""
        if self._running:
            return False
        self._scheduled = False
        if not self._reasons:
            return False

        request = StructuralRefreshRequest(
            tuple(self._reasons), self._rebuild_navigation, self._remount_canvas
        )
        self._reasons.clear()
        self._rebuild_navigation = False
        self._remount_canvas = False
        self._running = True
        apply_failed = False
        had_reentrant_work = False
        try:
            self._apply(request)
        except Exception:
            apply_failed = True
            had_reentrant_work = bool(self._reasons)
            reentrant = StructuralRefreshRequest(
                tuple(self._reasons),
                self._rebuild_navigation,
                self._remount_canvas,
            )
            self._reasons.clear()
            self._rebuild_navigation = False
            self._remount_canvas = False
            # Failed intent stays first; later work is merged after it.
            self._merge_request(request)
            self._merge_request(reentrant)
            raise
        finally:
            self._running = False
            if apply_failed:
                # Reentrant work earns one follow-up drain. A lone failed
                # snapshot remains pending for retry_pending() or a later request.
                if had_reentrant_work and self._reasons and not self._scheduled:
                    self._schedule_drain()
            elif self._reasons and not self._scheduled:
                self._schedule_drain()
        return True
