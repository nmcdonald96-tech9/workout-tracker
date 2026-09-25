# IronCycle 1.91.1

## Navigation Helper Hotfix

- Corrects three ExerciseCard callbacks that still called
  `exercise_anchor_key()` as a WorkoutTrackerApp instance method.
- Prevents the Android crash that occurred after changing a pending set's weight.
- Retains the 1.91.0 Pending Set Lifecycle consolidation.
- Preserves atomic pending-set persistence and restart restoration.
- Database schema remains version 20.
- No database migration is required.
