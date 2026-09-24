"""Authoritative progression policy for IronCycle 1.74.

The database layer owns persistence. This module owns progression settings,
outcome classification, and next-target calculations. Lazy database access avoids
import cycles while keeping the policy independently testable.
"""
from constants import *

def get_db():
    from database import get_db as database_context
    return database_context()

def get_next_dumbbell(current_weight):
    db_rack = [2.5, 5.0, 7.5, 10.0, 12.5, 15.0] + [float(x) for x in range(20, 105, 5)]
    for w in db_rack:
        if w > current_weight:
            return w
    return current_weight # Maxed out!
def get_prev_dumbbell(current_weight):
    db_rack = [2.5, 5.0, 7.5, 10.0, 12.5, 15.0] + [float(x) for x in range(20, 105, 5)]
    for w in reversed(db_rack):
        if w < current_weight:
            return w
    return current_weight
def calculate_progression(first_set_w, first_set_reps, first_set_rpe, tgt_r, mov_type, readiness_score=15, joint_score=5, equipment_type="Barbell", is_bodyweight=False, age=43, profile=0):
    # Coerce None or non-numeric RPE to a neutral baseline value (8.0 = moderate effort)
    # so the engine never crashes silently when a set was logged without RPE.
    try:
        first_set_rpe = float(first_set_rpe) if first_set_rpe is not None else 8.0
    except (TypeError, ValueError):
        first_set_rpe = 8.0

    # Guard tgt_r (this week's target reps) the same way -- it flows into
    # `tgt_r - first_set_reps` arithmetic further down with no prior check.
    # A None/blank target_reps (e.g. an older row, or a data path that didn't
    # set it) would otherwise throw TypeError and silently abort the whole
    # week's progression with zero feedback to the user.
    try:
        tgt_r = int(tgt_r) if tgt_r is not None else 10
    except (TypeError, ValueError):
        tgt_r = 10

    # Same defensive coercion for the actual logged performance values --
    # these should always be numeric by the time they reach here, but the
    # cost of guarding is negligible next to a silently aborted week.
    try:
        first_set_w = float(first_set_w) if first_set_w is not None else 0.0
    except (TypeError, ValueError):
        first_set_w = 0.0
    try:
        first_set_reps = int(first_set_reps) if first_set_reps is not None else tgt_r
    except (TypeError, ValueError):
        first_set_reps = tgt_r

    is_heavy_compound = (mov_type == 'Compound' and first_set_w >= HEAVY_THRESHOLD_COMPOUND)
    is_heavy_isolation = (mov_type == 'Isolation' and first_set_w >= HEAVY_THRESHOLD_ISOLATION)

    standard_jump = COMPOUND_JUMP_STANDARD if mov_type == 'Compound' else ISOLATION_JUMP_STANDARD
    heavy_jump = COMPOUND_JUMP_HEAVY if mov_type == 'Compound' else ISOLATION_JUMP_HEAVY

    jump_size = heavy_jump if (is_heavy_compound or is_heavy_isolation) else standard_jump
    
    if is_bodyweight:
        jump_size = 0.0

    # --- PROGRESSION OVERRIDE LOGIC ---
    # Determine the effective profile: 1 (Conservative), 2 (Balanced), 3 (Aggressive)
    if profile == 0:  # Auto (Age-Based)
        if age < 35: effective_profile = 3
        elif age < 45: effective_profile = 2
        else: effective_profile = 1
    else:
        effective_profile = profile

    if effective_profile == 3: # Aggressive Profile
        REP_CEILING = 12
        FORCE_DOUBLE_PROG_WEIGHT = 9999 
    elif effective_profile == 2: # Balanced Profile
        REP_CEILING = 15
        FORCE_DOUBLE_PROG_WEIGHT = 225  
    else: # Conservative / Longevity Profile
        REP_CEILING = 18
        FORCE_DOUBLE_PROG_WEIGHT = 185  

    # Determine if we should use Double Progression
    use_double_progression = False
    if equipment_type == "Dumbbell":
        use_double_progression = True
    elif effective_profile == 1 and first_set_w >= FORCE_DOUBLE_PROG_WEIGHT and not is_bodyweight:
        use_double_progression = True

    # --- 1. DOUBLE PROGRESSION (Volume Accumulation) ---
    if use_double_progression:
        REP_FLOOR = tgt_r if tgt_r else 8
        
        if joint_score <= 2:
            lower_w = get_prev_dumbbell(first_set_w) if equipment_type == "Dumbbell" else max(first_set_w - standard_jump, 0.0)
            return lower_w, tgt_r

        if readiness_score <= 7 and first_set_rpe >= 9.0:
            return first_set_w, tgt_r
            
        miss_margin = tgt_r - first_set_reps
        
        if miss_margin >= 5:
            lower_w = get_prev_dumbbell(first_set_w) if equipment_type == "Dumbbell" else max(first_set_w - standard_jump, 0.0)
            if first_set_rpe <= 8.5:
                return lower_w, first_set_reps + 1
            else:
                return lower_w, tgt_r
        
        # The Graduation Check
        if first_set_reps >= REP_CEILING and first_set_rpe <= 9.0:
            next_w = get_next_dumbbell(first_set_w) if equipment_type == "Dumbbell" else first_set_w + standard_jump
            return next_w, REP_FLOOR
        else:
            # Grind Phase: Hold weight, build reps
            reps_to_add = 2 if first_set_rpe <= 8.0 else 1
            return first_set_w, first_set_reps + reps_to_add


    # --- 2. STANDARD PROGRESSION (Aggressive Load) ---
    if joint_score <= 2:
        return max(first_set_w - standard_jump, 0.0), tgt_r

    if readiness_score <= 7:
        jump_size = standard_jump if not is_bodyweight else 0.0
        if first_set_rpe >= 9.0:
            jump_size = 0.0

    miss_margin = tgt_r - first_set_reps

    if miss_margin >= 5:
        if first_set_rpe <= 8.5:
            return max(first_set_w - jump_size, 0.0), first_set_reps + 1
        else:
            return max(first_set_w - jump_size, 0.0), tgt_r

    elif miss_margin > 0:
        return first_set_w, tgt_r

    else:
        if first_set_rpe <= 8.5:
            if first_set_reps >= tgt_r + 3:
                return first_set_w + jump_size, tgt_r + (2 if is_bodyweight else 1)
            else:
                return first_set_w + jump_size, tgt_r + (1 if is_bodyweight else 0)
        elif 8.5 < first_set_rpe <= 9.5:
            if jump_size > 0:
                return first_set_w + standard_jump, tgt_r
            else:
                return first_set_w, tgt_r + 1
        else:
            return first_set_w, tgt_r + 1
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


def progression_clarity(settings,cw,cr,nw,nr,reason_code=None):
    cw=float(cw or 0);nw=float(nw or 0);cr=int(cr or 0);nr=int(nr or 0);cap=settings.get("max_progression_weight");return {"load":f"{'Load held' if nw==cw else 'Load increases' if nw>cw else 'Load reduces'}: {nw:g} lb","reps":f"{'Reps held' if nr==cr else 'Reps increase' if nr>cr else 'Reps reset'}: {nr}","at_cap":cap is not None and nw>=float(cap),"reason_code":reason_code}

def simulate_progression(settings,w,r,equipment_type="Barbell"):
    w=float(w or 0);r=int(r or 0);ceiling=int(settings["rep_ceiling"])
    if r<ceiling:return {"next_weight":w,"next_reps":r+1,"summary":f"Build reps: {w:g} x {r+1}"}
    n=get_next_dumbbell(w) if equipment_type=="Dumbbell" else w+float(settings["progression_step"]);cap=settings.get("max_progression_weight")
    if cap is not None and n>float(cap):return {"next_weight":float(cap),"next_reps":ceiling,"summary":f"Load cap: hold {float(cap):g} lb and maintain up to {ceiling} reps"}
    return {"next_weight":n,"next_reps":8,"summary":f"Graduate load: {n:g} lb, reps reset for the next climb"}
