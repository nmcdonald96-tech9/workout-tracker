# IronCycle 1.92.3

## Workout quick-navigation correction

- Keeps Jump To collapse state in the tuple-scoped key format consumed by the workout renderer.
- Opens the selected category and collapses the other categories for the current mesocycle, week, and day.
- Defers the category scroll until the replacement workout canvas and category anchor are mounted.
- Rebuilds the persistent Jump To header after adding an exercise, so a newly introduced category appears immediately.
- Avoids duplicate synchronous header or full-display rebuilding in the Add Exercise callback.
- Retains the 1.92.2 structural-refresh fault-containment and bounded recovery behavior.
- Leaves pending-set persistence, progression, target ownership, RPE, completed revision, backup, billing, OneDrive, and exercise identity unchanged.
- Database schema remains version 20. No migration is required.
