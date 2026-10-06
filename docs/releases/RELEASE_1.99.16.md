# IronCycle 1.99.16

## Android reps control lifecycle hotfix

- Fixes the deterministic Android crash when blank reps blur into RPE and the mounted reps field is frozen.
- Replaces direct mutation of mounted or stale reps and plate controls with a deferred, coalesced workout remount sourced from the authoritative draft model.
- Repairs the related intermittent condition where weight-derived reps could remain visually stale until leaving for History and returning.
- Preserves manual reps ownership, blank-reps target restoration, autosave, scroll retention, display modes, Billing, OneDrive, backups, and schema 20.
- No feature, entitlement-policy, progression, superset, backup-format, or database migration changes.
