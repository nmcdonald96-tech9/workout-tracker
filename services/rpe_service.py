"""Canonical RPE parsing and validation for IronCycle."""
RPE_MIN = 1.0
RPE_MAX = 10.0
RPE_STEP = 0.5
RPE_ERROR = "RPE must be 1 to 10 in 0.5 steps, such as 8 or 8.5."

def normalize_rpe(value):
    raw = str(value if value is not None else "").strip()
    if not raw:
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if number < RPE_MIN or number > RPE_MAX:
        return None
    scaled = number / RPE_STEP
    if abs(scaled - round(scaled)) > 0.000001:
        return None
    return f"{number:g}"

def rpe_is_valid(value):
    return normalize_rpe(value) is not None