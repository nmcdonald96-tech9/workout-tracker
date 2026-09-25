# IronCycle 1.92.0
## Structural refresh coordination
- Adds a framework-neutral structural-refresh coordinator that coalesces repeated requests.
- Defers mounted workout-tree replacement until the active Flet callback yields.
- Promotes merged requests to the strongest required refresh: navigation rebuild and canvas remount.
- Routes ExerciseCard structure-changing callbacks through the coordinator instead of rebuilding inline.
- Retains pending-set atomic persistence, target ownership, RPE validation, progression behavior, and navigation helpers.
- Database schema remains version 20. No migration is required.
