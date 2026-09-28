# IronCycle 1.93.1

## Android value-edit and superset-assignment refresh hotfix

- Keeps valid pending weight edits on the mounted workout canvas instead of remounting the full workout view.
- Updates weight-derived reps and plate feedback in place, preserving the current exercise and viewport.
- Retains an anchor-preserving deferred-remount fallback if the packaged runtime rejects an in-place control update.
- Refreshes the workout immediately after creating or removing a superset group.
- Adds visible confirmation for group creation and removal and requires at least two pending exercises to create a group.
- Preserves pending-set persistence, ownership, structural-refresh fault containment, superset resolver v2, completed-revision transactions, progression, Billing, OneDrive, and backup behavior.
- Database schema remains version 20. No migration is required.
