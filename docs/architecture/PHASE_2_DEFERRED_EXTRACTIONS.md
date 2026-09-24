# Deferred Phase 2 stateful extractions

The following remain in `main.py` because each owns mutable UI, persistence, platform, or lifecycle state:

- `ExerciseCard` control construction, draft mutation, autosave, completed-exercise revision, and save orchestration.
- `WorkoutTrackerApp` shell construction, route switching, dialog ownership, snackbar handling, and canvas remount behavior.
- Active mesocycle, week, and day selection plus missed-workout rollover and schedule editing.
- Readiness capture, readiness-adjusted drafts, and progression execution wiring.
- Superset activation, focus state, scrolling, and cross-card handoff.
- SQLite settings access, mesocycle discovery, exercise history lookup, and local backup-directory selection.
- Backup Manager, Wi-Fi transfer server, multipart parsing, OneDrive authorization and polling.
- Billing reconciliation, purchase and restore dialogs, entitlement simulation, and resume behavior.
- Analytics, workout summary, mesocycle report, strength standards, and chart control state.
- First Setup, template recommendation, blueprint editing and stamping, and Exercise Library dialogs.

Before Phase 2, add tests around controller state transitions, dialog lifecycle, page resume, transaction boundaries, and Android mounted-control behavior. Extract one stateful vertical slice at a time rather than moving methods solely by size.
