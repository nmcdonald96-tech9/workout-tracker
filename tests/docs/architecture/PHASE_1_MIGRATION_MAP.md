# IronCycle 1.89 Phase 1 migration map

## What left `main.py`

- Local `WorkoutStateService` definition moved to `services/workout_service.py`.
- Local `workout_progress()` moved to `services/workout_service.py`.
- `WorkoutTrackerApp.ordered_day_names()` moved to `app/navigation.py` as `ordered_day_names()`.
- `WorkoutTrackerApp.category_anchor_key()` moved to `app/navigation.py` as `category_anchor_key()`.
- `WorkoutTrackerApp.exercise_anchor_key()` moved to `app/navigation.py` as `exercise_anchor_key()`.
- `ExerciseCard.format_target_weight()` moved to `components/exercise_card.py` as `format_target_weight()`.

## Call-site strategy

`main.py` directly imports the workout-flow and navigation contracts. Existing calls were changed from controller-bound methods to pure functions. No adapter objects, global mutable state, or database access were introduced.

## Deliberate non-moves

Phase 1 does not relocate Flet control construction, dialog ownership, controller fields, SQLite transactions, async lifecycle handling, or persistence orchestration. Those boundaries require state and lifecycle tests before extraction.
