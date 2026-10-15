"""Framework-neutral RPE wheel selection helpers for IronCycle."""
from services.rpe_service import RPE_ERROR, normalize_rpe

RPE_PICKER_OPTIONS = tuple(f"{value / 2:g}" for value in range(12, 21))
RPE_PICKER_DEFAULT = "8"


def picker_value(value):
    """Return a normalized wheel value, or None when it is outside 6-10."""
    normalized = normalize_rpe(value)
    return normalized if normalized in RPE_PICKER_OPTIONS else None


def resolve_picker_default(current_value=None, suggested_value=None):
    """Prefer the current value, then the suggested value, then neutral RPE 8."""
    return (
        picker_value(current_value)
        or picker_value(suggested_value)
        or RPE_PICKER_DEFAULT
    )


def picker_index(value):
    """Return the stable index used to center a CupertinoPicker."""
    normalized = resolve_picker_default(value)
    return RPE_PICKER_OPTIONS.index(normalized)


def apply_picker_selection(draft, selected_value):
    """Apply a valid 6-10 wheel selection without changing other draft fields."""
    normalized = picker_value(selected_value)
    if normalized is None:
        raise ValueError(RPE_ERROR)
    updated = dict(draft or {})
    updated["rpe"] = normalized
    return updated
