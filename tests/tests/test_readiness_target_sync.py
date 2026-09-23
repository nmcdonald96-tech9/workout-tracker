"""Regression coverage for readiness-driven pending target synchronization."""

def follows_target(value, previous_target):
    if not str(value if value is not None else "").strip():
        return True
    try:
        return abs(float(value) - float(previous_target)) < 0.0001
    except Exception:
        return str(value).strip() == str(previous_target).strip()

def synchronized(value, previous_target, new_target, done=False):
    if done:
        return str(value)
    return str(new_target) if follows_target(value, previous_target) else str(value)

def test_plan_seeded_reps_follow_lower_readiness():
    assert synchronized("12", 12, 8) == "8"

def test_plan_seeded_weight_follows_lower_readiness():
    assert synchronized("100", 100, 80) == "80"

def test_ghost_value_materializes_at_adjusted_target():
    assert synchronized("", 12, 8) == "8"

def test_manual_rep_override_is_preserved():
    assert synchronized("10", 12, 8) == "10"

def test_manual_weight_override_is_preserved():
    assert synchronized("90", 100, 80) == "90"

def test_completed_set_is_immutable():
    assert synchronized("12", 12, 8, done=True) == "12"

def test_following_resumes_when_value_matches_prior_target():
    assert synchronized("8", 8, 10) == "10"