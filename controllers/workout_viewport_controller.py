"""Framework-neutral workout viewport intent and restoration state."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
class ViewportAction(str,Enum):
    NONE="none"; PRESERVE_OFFSET="preserve_offset"; SCROLL_TO_KEY="scroll_to_key"; RESET_TOP="reset_top"
@dataclass(frozen=True)
class ViewportInstruction:
    action:ViewportAction
    offset:Optional[float]=None
    key:Optional[str]=None
    reason:str=""
class WorkoutViewportController:
    def __init__(self):
        self.current_offset=0.0; self.pending_offset=None; self.pending_key=None
    def record_scroll(self,pixels):
        try:self.current_offset=max(0.0,float(pixels or 0.0))
        except (TypeError,ValueError):pass
        return self.current_offset
    def preserve_current(self,reason="structural_edit"):
        self.pending_offset=self.current_offset; self.pending_key=None
        return ViewportInstruction(ViewportAction.PRESERVE_OFFSET,self.pending_offset,None,reason)
    def navigate_to_key(self,key,reason="execution_navigation"):
        self.pending_key=str(key) if key is not None else None; self.pending_offset=None
        return ViewportInstruction(ViewportAction.SCROLL_TO_KEY,None,self.pending_key,reason)
    def reset_top(self,reason="view_change"):
        self.pending_key=None; self.pending_offset=None; self.current_offset=0.0
        return ViewportInstruction(ViewportAction.RESET_TOP,0.0,None,reason)
    def consume(self):
        if self.pending_offset is not None:
            instruction=ViewportInstruction(ViewportAction.PRESERVE_OFFSET,self.pending_offset,None,"post_mount_restore")
        elif self.pending_key:
            instruction=ViewportInstruction(ViewportAction.SCROLL_TO_KEY,None,self.pending_key,"post_mount_navigation")
        else:
            instruction=ViewportInstruction(ViewportAction.NONE,None,None,"no_pending_viewport_work")
        self.pending_offset=None; self.pending_key=None
        return instruction

    def diagnostics(self):
        if self.pending_offset is not None: pending=ViewportAction.PRESERVE_OFFSET.value
        elif self.pending_key: pending=ViewportAction.SCROLL_TO_KEY.value
        else: pending=ViewportAction.NONE.value
        return {"current_offset":round(self.current_offset,1),"pending_action":pending,"pending_key":self.pending_key}
