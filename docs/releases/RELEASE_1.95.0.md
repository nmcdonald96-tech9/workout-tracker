# IronCycle 1.95.0

## Workout Interaction and Presentation Boundary

- Preserves the exact numeric workout viewport during Add Set and Remove Set; execution completion retains deliberate target navigation.
- Renders skipped exercises as compact neutral, noneditable cards with History and Unskip actions.
- Adds `components/exercise_card_state.py` for pure card-mode classification.
- Adds `services/exercise_completion_service.py` for UI-neutral post-completion orchestration.
- Retains the typed 1.94 superset execution boundary, unequal-set safety, skipped/completed bypass, and single-member continuation.
- Retains stable weight/reps edits and immediate superset assignment refresh.
- Schema remains 20. No migration.
