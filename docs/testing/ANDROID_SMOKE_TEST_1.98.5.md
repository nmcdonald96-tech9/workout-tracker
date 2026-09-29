# IronCycle 1.98.5 Android smoke test

1. Back up data, upgrade, and confirm version 1.98.5, schema 20, integrity `ok`.
2. Change weight and confirm derived reps and plate feedback update immediately.
3. Enter valid RPE and tap Complete on a standalone nonfinal set; confirm immediate row update and next-set activation.
4. Reopen the set; complete the final set and confirm normal logging.
5. Add/Remove Set near the bottom and confirm no flash or viewport movement.
6. Complete A1/A2 and verify unequal groups and skipped/completed bypass.
7. Create/remove a superset; test Jump To and Weeks and days auto-close.
8. Verify compact skipped cards, completed revision, Return to Pending, Diagnostics, Backup Manager, and OneDrive screen.
9. Background/resume and force-stop/relaunch.
10. Run integrity and inspect logcat for frozen controls, structural-refresh failures, and unhandled exceptions.
