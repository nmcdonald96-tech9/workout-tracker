# IronCycle 1.93.0 Android smoke test

Record device model, Android version, install type, source commit, APK version code, and pass/fail for every item.

1. Upgrade the exact Android-tested 1.92.3 baseline; confirm version 1.93.0, schema 20, existing history, and database integrity `ok`.
2. Open a completed exercise in revision mode. Make no changes and cancel; confirm completed history is unchanged.
3. Revise only RPE and save. Repeat for only weight, then only reps.
4. Add a set and save. In another revision, remove a set and save.
5. Enter RPE 8.3, 85, and 10.5; confirm each is rejected.
6. Trigger another validation failure; confirm the revision draft remains available for correction or cancellation.
7. Save a valid revision and verify History contains the corrected result exactly once.
8. Verify future progression updates exactly once. Verify manually owned pending targets remain unchanged.
9. Return a completed exercise to Pending. Confirm logged values become incomplete drafts and completion-only progression fields are cleared.
10. Complete the reopened exercise again; confirm progression recalculates once.
11. Background and resume during revision. Confirm the in-memory draft remains available and permanent completed history remains unchanged.
12. Force-stop during revision without saving. Relaunch and confirm permanent completed history remains unchanged.
13. Run the in-app database integrity check.
14. Review logcat for SQLite locking, `Frozen controls cannot be updated`, unhandled tasks, duplicate progression, and rollback errors. Expected result: none.
15. Regression-check pending-set edits, readiness, RPE help/validation, backup creation/restore, Billing screen, OneDrive screen, Jump To navigation, structural refresh, and one superset handoff.
