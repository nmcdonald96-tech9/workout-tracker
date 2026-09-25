"""Coalesced post-callback structural refresh coordination."""
from dataclasses import dataclass
from typing import Callable
@dataclass(frozen=True)
class StructuralRefreshRequest:
    reasons: tuple[str, ...]
    rebuild_navigation: bool
    remount_canvas: bool
class StructuralRefreshCoordinator:
    def __init__(self, dispatch: Callable, apply: Callable):
        self._dispatch=dispatch; self._apply=apply; self._reasons=[]
        self._rebuild_navigation=False; self._remount_canvas=False
        self._scheduled=False; self._running=False
    @property
    def scheduled(self): return self._scheduled
    def request(self, reason, *, rebuild_navigation=False, remount_canvas=True):
        label=str(reason or "structural_change").strip() or "structural_change"
        if label not in self._reasons: self._reasons.append(label)
        self._rebuild_navigation |= bool(rebuild_navigation)
        self._remount_canvas |= bool(remount_canvas)
        if self._scheduled or self._running: return False
        self._scheduled=True; self._dispatch(self.drain); return True
    def drain(self):
        if self._running: return False
        self._scheduled=False
        if not self._reasons: return False
        request=StructuralRefreshRequest(tuple(self._reasons),self._rebuild_navigation,self._remount_canvas)
        self._reasons.clear(); self._rebuild_navigation=False; self._remount_canvas=False; self._running=True
        try: self._apply(request)
        finally: self._running=False
        if self._reasons and not self._scheduled:
            self._scheduled=True; self._dispatch(self.drain)
        return True
