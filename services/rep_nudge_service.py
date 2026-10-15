"""Framework-neutral active-set rep nudge helpers for IronCycle."""
from services.target_ownership_service import apply_direct_edit

REP_NUDGE_DELTAS = (-1, 1)


def nudge_pending_reps(draft, target_reps, delta, *, min_reps=1, max_reps=50):
    """Return a copied draft with clamped, user-owned reps."""
    if int(delta) not in REP_NUDGE_DELTAS:
        raise ValueError("Rep nudge must be -1 or +1.")
    row = dict(draft or {})
    raw_reps = str(row.get("r", "")).strip()
    try:
        base_reps = int(float(raw_reps)) if raw_reps else int(target_reps)
    except (TypeError, ValueError):
        base_reps = int(target_reps)
    low = max(1, int(min_reps or 1))
    high = max(low, int(max_reps or 50))
    nudged = max(low, min(high, base_reps + int(delta)))
    return apply_direct_edit(row, "r", str(nudged))
