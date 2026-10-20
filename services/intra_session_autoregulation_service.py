"""Pure intra-session fatigue advisory and pending-draft transformations."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass

@dataclass(frozen=True)
class FatigueAdvisory:
    trigger_index: int
    reason: str
    actions: tuple[str, ...]


def _number(value, fallback=0.0):
    try: return float(value)
    except (TypeError, ValueError): return float(fallback)


def readiness_reduced(target, normal_target):
    return abs(_number(target.get("w"))-_number(normal_target.get("w"))) > .01 or int(_number(target.get("r"),1)) != int(_number(normal_target.get("r"),1))


def previous_dumbbell(weight):
    rack=[2.5,5,7.5,10,12.5,15]+list(range(20,105,5))
    return max((float(x) for x in rack if x < float(weight)), default=float(weight))


def reduced_weight(current, equipment, *, weight_step=None, min_weight=0.0):
    current=_number(current); minimum=max(0.0,_number(min_weight))
    if current <= minimum or (equipment == "Bodyweight" and current <= 0): return None
    raw=current*.95
    if equipment == "Dumbbell": candidate=previous_dumbbell(current)
    else:
        step=_number(weight_step, 5.0 if equipment == "Barbell" else 2.5) or (5.0 if equipment == "Barbell" else 2.5)
        candidate=round(raw/step)*step
        if candidate >= current: candidate=current-step
    candidate=max(minimum,float(candidate))
    return candidate if candidate < current else None


def evaluate_fatigue_advisory(*, rows, trigger_index, targets, normal_targets, reduction_threshold, equipment, weight_step=None, min_weight=0.0, deload=False, revision=False, handled=False):
    if deload or revision or handled or trigger_index < 0 or trigger_index >= len(rows): return None
    target=targets[min(trigger_index,len(targets)-1)]; normal=normal_targets[min(trigger_index,len(normal_targets)-1)]
    if readiness_reduced(target,normal): return None
    remaining=[i for i in range(trigger_index+1,len(rows)) if not rows[i].get("done")]
    if not remaining: return None
    row=rows[trigger_index]; rpe=_number(row.get("rpe")); target_reps=max(1,int(_number(target.get("r"),1))); ratio=int(_number(row.get("r")))/target_reps
    if rpe < 9.5 and ratio >= float(reduction_threshold): return None
    actions=[]
    if any(reduced_weight(rows[i].get("w"),equipment,weight_step=weight_step,min_weight=min_weight) is not None for i in remaining): actions.append("reduce_load")
    if any(int(_number(rows[i].get("r"),1)) > 1 for i in remaining): actions.append("reduce_reps")
    if len(remaining) >= 2: actions.append("scratch_final")
    if not actions: return None
    actions.append("keep_plan")
    reason=f"Set {trigger_index + 1} RPE {rpe:g}" if rpe>=9.5 else f"Set {trigger_index + 1} rep miss"
    return FatigueAdvisory(trigger_index,reason,tuple(actions))


def apply_action(rows, *, action, trigger_index, targets, equipment, weight_step=None, min_weight=0.0):
    original=deepcopy(list(rows)); changed=[]; result=deepcopy(list(rows))
    remaining=[i for i in range(trigger_index+1,len(result)) if not result[i].get("done")]
    if action == "reduce_load":
        for i in remaining:
            new=reduced_weight(result[i].get("w"),equipment,weight_step=weight_step,min_weight=min_weight)
            if new is None: continue
            result[i]["w"]=str(new); result[i]["w_source"]="user"
            if result[i].get("r_source") == "weight_derived":
                current=max(1,int(_number(result[i].get("r"),1))); target=max(1,int(_number(targets[min(i,len(targets)-1)].get("r"),1)))
                clamped=min(current,target); result[i]["r"]=str(clamped); result[i]["r_source"]="target" if clamped == target else "user"
            changed.append(i)
    elif action == "reduce_reps":
        for i in remaining:
            old=max(1,int(_number(result[i].get("r"),1))); new=max(1,old-1)
            if new != old: result[i]["r"]=str(new); result[i]["r_source"]="user"; changed.append(i)
    elif action == "scratch_final" and len(remaining) >= 2 and remaining[-1] == len(result)-1:
        changed.append(remaining[-1]); result.pop()
    elif action != "keep_plan": raise ValueError("Unsupported fatigue action.")
    return result, original, tuple(changed)
