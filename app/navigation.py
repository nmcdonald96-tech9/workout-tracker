"""Deterministic navigation identifiers and canonical weekday ordering."""

DAYS_OF_WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def ordered_day_names():
    return list(DAYS_OF_WEEK)


def category_anchor_key(category_name):
    safe = "".join(
        character.lower() if character.isalnum() else "-"
        for character in str(category_name)
    ).strip("-")
    return f"category-{safe}"


def exercise_anchor_key(session_id):
    return f"exercise-{session_id}"
