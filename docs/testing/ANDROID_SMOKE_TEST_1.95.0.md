# IronCycle 1.95.0 Android smoke test

1. Upgrade over 1.94.0; confirm version 1.95.0, schema 20, integrity `ok`.
2. Near the bottom of a workout, Add Set and Remove Set; confirm the exact viewport remains stable with no top alignment.
3. Repeat on first and last superset members.
4. Complete A1 and A2; confirm deliberate handoff navigation still occurs.
5. Verify unequal-set groups do not open nonexistent sets.
6. Skip an exercise; confirm a compact neutral card with History and Unskip only, no editable fields or completion controls.
7. Unskip; confirm the full pending card and drafts return.
8. Change weight/reps and confirm no flash or jump.
9. Create/remove a superset and confirm immediate synchronization.
10. Regression-check completed revision and Return to Pending.
11. Run integrity and inspect logcat for frozen controls, structural-refresh failures, blank canvas, and unhandled tasks.
