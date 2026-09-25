# IronCycle 1.92.2 Android smoke test

1. Upgrade over 1.92.1 and confirm version 1.92.2.
2. Confirm schema 20 and database integrity `ok`.
3. Rapidly tap Add Set twice.
4. Remove the last set immediately.
5. Copy Previous Set.
6. Enter weight and allow reps to auto-adjust.
7. Manually override reps.
8. Complete the active set while changing category navigation.
9. Collapse and reopen the active category.
10. Complete one superset handoff.
11. Background and resume with a pending draft.
12. Force-stop and relaunch.
13. Confirm draft values and ownership sources restore.
14. Review logcat.

The following must be absent:

- `Frozen controls cannot be updated`
- `Task exception was never retrieved`
- duplicate workout canvas
- blank workout canvas

Normally these should also be absent:

- `[structural_refresh] FAILED:`
- `[structural_refresh] RETRY_DISPATCH_FAILED:`

For an instrumented failure build, confirm one failure marker is followed by no more than one bounded recovery attempt.
