"""Phase 2 workout navigation state and post-render offset helpers."""
from dataclasses import dataclass
from app.navigation import category_anchor_key, exercise_anchor_key
@dataclass(frozen=True)
class WorkoutJumpRequest:
    key: str
    remount: bool = True
    numeric_fallback: bool = True
def category_state_key(name): return str(name or "").strip().lower()
def jump_to_category_state(collapsed, categories, selected):
    selected=str(selected or "").strip()
    if not selected: raise ValueError("category_name is required")
    result=dict(collapsed or {})
    for category in categories or ():
        if category: result[category_state_key(category)]=str(category)!=selected
    result[category_state_key(selected)]=False
    return result,WorkoutJumpRequest(category_anchor_key(selected))
def jump_to_exercise_state(collapsed,active,categories,selected,session_id):
    result,request=jump_to_category_state(collapsed,categories,selected); active=dict(active or {}); active[category_state_key(selected)]=session_id
    return result,active,WorkoutJumpRequest(exercise_anchor_key(session_id))
def find_control_offset(controls,wanted_key,*,height_estimator,gap=6.0,target_inset=8.0):
    def contains(c):
        if getattr(c,"key",None)==wanted_key:return True
        content=getattr(c,"content",None)
        if content is not None and contains(content):return True
        return any(contains(x) for x in (getattr(c,"controls",None) or ()))
    offset=0.0
    for control in controls or ():
        if contains(control):return max(0.0,offset-target_inset)
        offset+=float(height_estimator(control))+gap
    return None
