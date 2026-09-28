# IronCycle 1.95.1

## Corrective release

- Restores the `resolve_next_group_step()` compatibility export required by `database.py` and grouped-card rendering.
- Changes Add Set and Remove Set from full workout-canvas remounts to card-local reconstruction and update.
- Keeps the mounted workout ListView and its viewport unchanged during set-count editing.
- Retains deliberate navigation after set completion, compact skipped cards, completion orchestration, and typed superset execution.
- Schema remains 20. No migration.
