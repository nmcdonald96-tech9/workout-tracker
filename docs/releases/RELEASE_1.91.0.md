# IronCycle 1.91.0

## Pending Set Lifecycle

- Introduces `services/pending_set_service.py` as the authority for incomplete set drafts.
- Consolidates pending-set creation, Add Set, Remove Set, Copy Previous Set, ownership-source preservation, RPE draft normalization, atomic autosave, restart restoration, empty trailing-draft protection, and lifecycle flushing.
- Invalid partial numeric or RPE input stays in memory and cannot delete the last durable database draft.
- Autosave replaces one session's rows inside a single SQLite transaction using `BEGIN IMMEDIATE`, commit, and rollback.
- App lifecycle changes flush all registered pending draft contexts locally without network activity.
- Database schema remains 20. No migration is required.
