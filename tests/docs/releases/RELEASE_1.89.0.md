# IronCycle 1.89.0

## Phase 1 architecture extraction

IronCycle 1.89.0 begins a behavior-preserving decomposition of `main.py`. Phase 1 moves only deterministic, low-risk helpers. Stateful Flet controls, database transactions, lifecycle handlers, billing, backup transfer, and workout-save orchestration remain in place for Phase 2 review.

### Extracted boundaries

- Workout flow status, next-action text, elapsed-time calculation, and workout progress aggregation now live in `services/workout_service.py`.
- Weekday order and stable workout-scroll keys now live in `app/navigation.py`.
- Exercise-card target-weight formatting now lives in `components/exercise_card.py`.
- `main.py` imports the new boundaries instead of defining duplicate helper contracts.

### Tests and compatibility

- Added `tests/test_189_phase1_architecture.py` for release, ownership-boundary, navigation, formatting, and workout-flow contracts.
- Existing `WorkoutStateService` imports remain compatible.
- Database schema remains version 20. No database migration is required.
- User data, progression policy, billing, OneDrive, backup formats, and Android package identity are unchanged.
