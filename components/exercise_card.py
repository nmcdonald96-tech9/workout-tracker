"""Pure presentation helpers used by workout exercise cards."""


def active_set_index(rows):
    for index, row in enumerate(rows or []):
        if not row.get("done"):
            return index
    return len(rows) - 1 if rows else 0


def format_target_weight(is_bodyweight, weight_value):
    try:
        weight = float(weight_value)
        if is_bodyweight:
            return "BW" if weight == 0 else f"BW + {weight:g} lbs"
        return f"{weight:g} lbs"
    except (TypeError, ValueError):
        return "BW" if is_bodyweight else f"{weight_value} lbs"
