# IronCycle 1.94.0

## Superset Execution Boundary

- Adds `services/superset_execution_service.py` as the framework-neutral authority for post-set routing.
- Returns typed instructions for standalone set advancement, group advancement, exercise readiness, group readiness, and no-action states.
- Preserves resolver-v2 round-major ordering, unequal set counts, skipped/completed bypass, and single-member continuation.
- Keeps a compatibility wrapper in `database.py` while routing `main.py` through the typed service.
- Leaves Flet controls, scrolling, structural refresh, exercise logging, progression, and persistence in their established authorities.
- Retains 1.93.1 weight-edit and immediate group-assignment fixes plus 1.93.2 Add/Remove Set viewport retention.
- Schema remains 20. No migration.
