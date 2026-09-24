"""Pure workout flow and progress helpers.

This module intentionally has no Flet or database dependency. 1.89 Phase 1 moves
these deterministic contracts out of ``main.py`` so they can be tested without
constructing the application controller.
"""
from datetime import datetime


class WorkoutStateService:
    @staticmethod
    def first_incomplete_set(rows):
        return next((i for i, value in enumerate(rows or []) if not value.get("done")), None)

    @staticmethod
    def completed_count(rows):
        return sum(1 for value in rows or [] if value.get("done"))

    @staticmethod
    def exercise_started(rows):
        return any(value.get("done") for value in rows or [])

    @classmethod
    def active_set_position(cls, rows):
        rows = rows or []
        index = cls.first_incomplete_set(rows)
        return (0, 0) if not rows else ((index + 1) if index is not None else len(rows), len(rows))

    @classmethod
    def next_action(cls, rows, exercise_status="Pending"):
        if exercise_status == "Completed":
            return "Exercise logged. Continue to the next movement."
        index = cls.first_incomplete_set(rows)
        if index is None:
            return "All sets complete. Log the exercise."
        if not str(rows[index].get("rpe", "")).strip():
            return f"Enter RPE, then complete Set {index + 1}."
        return f"Complete Set {index + 1} to continue."

    @staticmethod
    def elapsed_since(timestamp, now=None):
        try:
            if not timestamp:
                return None
            return max(0, int(((now or datetime.now()) - datetime.fromisoformat(str(timestamp))).total_seconds()))
        except (TypeError, ValueError):
            return None


def workout_progress(rows, drafts):
    rows = rows or []
    drafts = drafts or {}
    categories = {row[6] for row in rows if row[6]}
    completed_categories = {
        category for category in categories
        if all(row[4] != "Pending" for row in rows if row[6] == category)
    }
    sets = [entry for row in rows for entry in drafts.get(row[0], [])]
    return {
        "completed_exercises": sum(row[4] == "Completed" for row in rows),
        "skipped_exercises": sum(row[4] == "Skipped" for row in rows),
        "total_exercises": len(rows),
        "completed_sets": sum(bool(entry.get("done")) for entry in sets),
        "total_sets": len(sets),
        "completed_categories": len(completed_categories),
        "total_categories": len(categories),
    }
