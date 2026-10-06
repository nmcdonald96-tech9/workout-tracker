# IronCycle 1.99.16

## Localized reps synchronization and frozen-control hotfix

- Blank reps blur restores authoritative target ownership without mutating the frozen event TextField.
- The restored value is repainted only after RPE blur through a deferred, card-only replacement, preserving RPE entry and the workout ListView.
- Weight-derived reps retain the immediate mounted-control fast path; frozen or stale references fall back to a deferred replacement of only the affected exercise card.
- The hotfix does not remount the workout canvas, reset scroll, reactivate Set 1, or alter completed-set state.
- Schema remains 20; no feature, progression, entitlement, Billing, OneDrive, backup, or superset changes.
