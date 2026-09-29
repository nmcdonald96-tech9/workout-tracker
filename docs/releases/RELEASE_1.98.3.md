# IronCycle 1.98.3

## Forced card reconciliation hotfix

- Uses per-exercise render revisions so Flet mounts a genuinely fresh exercise card after same-structure value and completion changes.
- Locates mounted exercise cards by durable `db_id` rather than render key.
- Resolves stable exercise navigation anchors to the current revisioned render key.
- Preserves the mounted workout ListView and exact viewport during local card replacement.
- Retains 1.98.2 persistence, weight-derived rep calculation, standalone completion, grouped execution navigation, and Add/Remove Set behavior.
- Schema remains 20. No migration.
