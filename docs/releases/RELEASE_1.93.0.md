# IronCycle 1.93.0

## Completed Exercise Revision and Progression Finalization

- Adds `services/completed_revision_service.py` as the non-UI authority for completed-set snapshots, deterministic fingerprints, service-level validation, bounded row reconciliation, atomic revision commits, privacy-safe transactional audit writes, and Return to Pending.
- Revision start and cancellation are memory-only. The completed session and completed rows remain unchanged until Save Revision commits successfully.
- Save Revision uses `BEGIN IMMEDIATE`, verifies the captured fingerprint, updates retained rows in place, inserts only new rows, deletes only removed rows, renumbers deterministically, delegates progression to `services.progression_service.recalculate_after_completed_revision()`, synchronizes eligible future target-owned drafts, and rolls back all effects on failure.
- Return to Pending preserves logged values as drafts, clears completion-only state, changes the session atomically, and reconciles eligible future targets.
- Historical `bodyweight_snapshot`, raw rest values, completion timestamps, target snapshots, and field ownership are preserved unless the corresponding value is intentionally changed.
- Audit metadata contains counts, IDs, status codes, and reconciliation outcomes only; exact workout values are excluded.
- `main.py` retains dialogs, draft editing, messages, navigation, scrolling, and structural refresh coordination. The new service imports no Flet code.

## Existing-contract adaptations

Schema 20 has set-level `weight_source` and `reps_source`, but no separate session-level target-owner columns and no dedicated pre-progression snapshot/history table. Therefore future protection is derived from the durable pending-set ownership rows, and Return to Pending restores target-owned future work from the completed set's normal target snapshot. User-owned pending rows are skipped. Eligibility is limited to the same exercise, same mesocycle, pending status, and later week/day/workout chronology; Deload sorts after numbered weeks. No synthetic columns or migration were added.

Schema 20 also has no durable revision-start record requirement. Revision start/cancel auditing is intentionally omitted so those memory-only actions cannot create an audit/database split.

## Version and schema

- `APP_VERSION = "1.93.0"`
- `DATABASE_SCHEMA_VERSION = 20`
- No migration.
