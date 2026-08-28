"""Authoritative progression policy for IronCycle 1.9.1.
Persistence remains available through database.get_db via lazy lookup, avoiding import cycles.
"""
from constants import *

def get_db():
    from database import get_db as database_context
    return database_context()

def get_next_dumbbell(weight):
    from database import get_next_dumbbell as fn
    return fn(weight)

def get_prev_dumbbell(weight):
    from database import get_prev_dumbbell as fn
    return fn(weight)

def calculate_progression(*args, **kwargs):
    from database import calculate_progression as fn
    return fn(*args, **kwargs)

_EFFECTIVE_SETTINGS_CACHE = {}

def invalidate_progression_settings_cache(exercise_name=None):
    if exercise_name is None:
        _EFFECTIVE_SETTINGS_CACHE.clear()
        return
    for key in list(_EFFECTIVE_SETTINGS_CACHE):
        if key[0] == exercise_name:
            _EFFECTIVE_SETTINGS_CACHE.pop(key, None)

def get_effective_progression_settings(exercise_name, movement_type, equipment_type, age=43, profile=0):
    """Resolve exercise overrides over current profile and movement defaults."""
    cache_key = (exercise_name, movement_type, equipment_type, int(age or 0), int(profile or 0))
    cached = _EFFECTIVE_SETTINGS_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    effective_profile = profile
    if effective_profile == 0:
        effective_profile = 3 if age < 35 else (2 if age < 45 else 1)
    profile_rep_ceiling = 12 if effective_profile == 3 else (15 if effective_profile == 2 else 18)
    default_step = COMPOUND_JUMP_STANDARD if movement_type == "Compound" else ISOLATION_JUMP_STANDARD
    result = {
        "custom_active": False,
        "progression_step": default_step, "progression_step_source": "movement_default",
        "reduction_steps": 1, "reduction_steps_source": "global_default",
        "rep_ceiling": profile_rep_ceiling, "rep_ceiling_source": "profile",
        "reduction_threshold": STRAIGHT_SET_REDUCE_REP_COMPLETION, "reduction_threshold_source": "global_default",
        "max_progress_rpe": STRAIGHT_SET_MAX_PROGRESS_RPE, "max_progress_rpe_source": "global_default",
        "max_progression_weight": None, "max_progression_weight_source": "none",
    }
    try:
        with get_db() as conn:
            row = conn.execute("""SELECT progression_mode, progression_step, reduction_steps, rep_ceiling,
                                  reduction_threshold, max_progress_rpe, max_progression_weight FROM exercise_dict WHERE name=?""", (exercise_name,)).fetchone()
        if row and row[0] == "custom":
            result["custom_active"] = True
            keys = ["progression_step", "reduction_steps", "rep_ceiling", "reduction_threshold", "max_progress_rpe", "max_progression_weight"]
            for key, value in zip(keys, row[1:]):
                if value is not None:
                    result[key] = float(value) if key in ("progression_step", "reduction_threshold", "max_progress_rpe", "max_progression_weight") else int(value)
                    result[key + "_source"] = "exercise_override"
    except Exception:
        pass
    if equipment_type == "Dumbbell":
        result["progression_step_source"] = "dumbbell_rack"
    _EFFECTIVE_SETTINGS_CACHE[cache_key] = dict(result)
    return result


def classify_set_progression(actual_weight, actual_reps, actual_rpe, target_weight, target_reps,
                             normal_target_weight, normal_target_reps, settings):
    """Single source of truth for set outcome classification."""
    target_reps = max(1, int(target_reps or 1))
    ratio = int(actual_reps or 0) / target_reps
    regulated = abs(float(target_weight or 0) - float(normal_target_weight or target_weight or 0)) > 0.01 or int(target_reps) != int(normal_target_reps or target_reps)
    max_weight = settings.get("max_progression_weight")
    at_load_ceiling = max_weight is not None and float(actual_weight or 0) >= float(max_weight) - 0.01
    if regulated:
        decision, code, reason = "resume_normal", "READINESS_ISOLATED", "Temporary readiness regulation was isolated; the normal trajectory resumes."
    elif at_load_ceiling and int(actual_reps or 0) >= target_reps and float(actual_rpe or 8) <= float(settings["max_progress_rpe"]):
        decision, code, reason = "hold", "LOAD_CEILING_REACHED", f"The {float(max_weight):g} lb progression ceiling has been reached; load is held."
    elif int(actual_reps or 0) >= target_reps and float(actual_rpe or 8) <= float(settings["max_progress_rpe"]):
        decision, code, reason = "progress", "TARGET_ACHIEVED", f"Target achieved within the RPE {settings['max_progress_rpe']:g} ceiling."
    elif int(actual_reps or 0) >= target_reps:
        decision, code, reason = "hold", "RPE_CEILING_EXCEEDED", f"Target achieved, but RPE exceeded {settings['max_progress_rpe']:g}."
    elif ratio < float(settings["reduction_threshold"]):
        decision, code, reason = "reduce", "SUBSTANTIAL_MISS", f"Rep completion was below {settings['reduction_threshold']*100:g}%."
    else:
        decision, code, reason = "hold", "SMALL_MISS", "The set was a small miss, so the normal target is held."
    return {"decision": decision, "reason_code": code, "reason": reason, "completion_ratio": round(ratio,4), "readiness_regulated": regulated}


def _custom_weight_step(weight, movement_type, equipment_type, settings, direction=1, steps=1):
    result=float(weight or 0)
    for _ in range(max(1,int(steps))):
        if equipment_type == "Dumbbell":
            result = get_next_dumbbell(result) if direction > 0 else get_prev_dumbbell(result)
        else:
            result=max(0.0, result + float(settings["progression_step"]) * direction)
        if direction > 0 and settings.get("max_progression_weight") is not None:
            result=min(result, float(settings["max_progression_weight"]))
    return result

def calculate_set_specific_progression(completed_sets, default_target_weight, default_target_reps,
                                       movement_type, readiness_score=15, joint_score=5,
                                       equipment_type="Barbell", is_bodyweight=False,
                                       bodyweight=0.0, age=43, profile=0, exercise_name=None):
    next_targets, diagnostics = [], []
    fallback_w=float(default_target_weight or (0 if is_bodyweight else 45)); fallback_r=max(1,int(default_target_reps or 10))
    settings=get_effective_progression_settings(exercise_name, movement_type, equipment_type, age, profile)
    for set_index,row in enumerate(completed_sets or []):
        try:
            actual_w=float(row[0] if row[0] is not None else fallback_w); actual_r=int(row[1] or 0); actual_rpe=float(row[2] if len(row)>2 and row[2] is not None else 8)
            target_w=float(row[3] if len(row)>3 and row[3] is not None else fallback_w); target_r=int(row[4] if len(row)>4 and row[4] is not None else fallback_r)
            normal_w=float(row[5] if len(row)>5 and row[5] is not None else target_w); normal_r=int(row[6] if len(row)>6 and row[6] is not None else target_r)
        except (TypeError,ValueError): continue
        if actual_r<=0: continue
        outcome=classify_set_progression(actual_w,actual_r,actual_rpe,target_w,target_r,normal_w,normal_r,settings)
        decision=outcome["decision"]
        if decision=="resume_normal": next_w,next_r=normal_w,normal_r
        elif decision=="progress":
            if not settings.get("custom_active"):
                # Preserve the Android-verified 1.3.0 target math exactly for all
                # exercises that continue to inherit defaults.
                next_w,next_r=calculate_progression(actual_w,actual_r,actual_rpe,normal_r,movement_type,15,5,equipment_type=equipment_type,is_bodyweight=is_bodyweight,age=age,profile=profile)
            elif actual_r >= int(settings["rep_ceiling"]):
                next_w=_custom_weight_step(actual_w,movement_type,equipment_type,settings,1,1) if not is_bodyweight else actual_w
                next_r=target_r if not is_bodyweight else target_r+1
            else:
                next_w,next_r=actual_w,actual_r+1
        elif decision=="reduce":
            if is_bodyweight and normal_w<=0: next_w,next_r=0.0,max(1,min(normal_r-1,actual_r+1))
            else: next_w,next_r=_custom_weight_step(normal_w,movement_type,equipment_type,settings,-1,settings["reduction_steps"]),normal_r
        else: next_w,next_r=normal_w,normal_r
        next_w=max(0.0,float(next_w)); next_r=max(1,int(next_r))
        diagnostic={"set_number":set_index+1,"actual_weight":actual_w,"actual_reps":actual_r,"actual_rpe":actual_rpe,
                    "prior_target_weight":target_w,"prior_target_reps":target_r,"normal_target_weight":normal_w,"normal_target_reps":normal_r,
                    "next_weight":next_w,"next_reps":next_r,"settings":settings}
        diagnostic.update(outcome); diagnostics.append(diagnostic); next_targets.append({"w":next_w,"r":next_r})
    return next_targets, diagnostics

