"""Pure target-ownership rules for pending IronCycle sets."""
TARGET = "target"
USER = "user"
WEIGHT_DERIVED = "weight_derived"
VALID_WEIGHT_SOURCES = {TARGET, USER}
VALID_REPS_SOURCES = {TARGET, USER, WEIGHT_DERIVED}

def normalize_weight_source(value):
    value = str(value or TARGET).strip().lower()
    return value if value in VALID_WEIGHT_SOURCES else TARGET

def normalize_reps_source(value):
    value = str(value or TARGET).strip().lower()
    return value if value in VALID_REPS_SOURCES else TARGET

def source_for_direct_edit(raw_value):
    return USER if str(raw_value or "").strip() else TARGET

def reconcile_pending_draft(draft, current_target, *, is_complete=False):
    resolved = dict(draft or {})
    ws = normalize_weight_source(resolved.get("w_source"))
    rs = normalize_reps_source(resolved.get("r_source"))
    resolved["w_source"], resolved["r_source"] = ws, rs
    if not is_complete:
        if ws == TARGET: resolved["w"] = str(current_target["w"])
        if rs == TARGET: resolved["r"] = str(current_target["r"])
    return resolved

def apply_direct_edit(draft, field, raw_value):
    if field not in ("w", "r"): raise ValueError("field must be 'w' or 'r'")
    updated = dict(draft or {})
    updated[field] = raw_value
    updated[f"{field}_source"] = source_for_direct_edit(raw_value)
    if field == "r": updated.pop("derived_from_weight", None)
    return updated

def apply_weight_derived_reps(draft, new_weight, derived_reps):
    updated = dict(draft or {})
    updated["w"], updated["w_source"] = str(new_weight), USER
    updated["r"], updated["r_source"] = str(int(derived_reps)), WEIGHT_DERIVED
    updated["derived_from_weight"] = str(new_weight)
    return updated

def clear_override(draft, field, current_target):
    if field not in ("w", "r"): raise ValueError("field must be 'w' or 'r'")
    updated = dict(draft or {})
    updated[field] = str(current_target[field])
    updated[f"{field}_source"] = TARGET
    if field == "r": updated.pop("derived_from_weight", None)
    return updated

def ownership_summary(draft, current_target, normal_target):
    ws = normalize_weight_source((draft or {}).get("w_source"))
    rs = normalize_reps_source((draft or {}).get("r_source"))
    if USER in (ws, rs): return "User override. Manual weight or reps are preserved until changed or cleared."
    if rs == WEIGHT_DERIVED: return "Weight-derived reps. Entering a weight adjusted reps to preserve approximately the same target effort."
    if current_target != normal_target:
        return f"Readiness-adjusted target. Today {current_target['w']:g} x {current_target['r']}; normal trajectory {normal_target['w']:g} x {normal_target['r']}."
    return "Normal progression target. The displayed values follow the current progression trajectory."