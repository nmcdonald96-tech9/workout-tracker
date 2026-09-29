# IronCycle 1.98.4 Android recovery smoke test

1. Back up IronCycle data before installing.
2. Upgrade over 1.98.3; confirm version 1.98.4, schema 20, integrity `ok`, and existing history/pending drafts remain present.
3. Change a pending weight and confirm derived reps and plate feedback update immediately.
4. Enter valid RPE and tap Complete on a standalone nonfinal set. Confirm immediate row update and next-set activation.
5. Reopen the completed set and confirm immediate display.
6. Complete the final set and confirm normal logging.
7. Add and Remove Set near the bottom; confirm no flash, jump, or viewport movement.
8. Complete A1 and A2; test uneven groups and skipped/completed member bypass.
9. Create/remove a superset; test Jump To and Weeks and days.
10. Verify compact skipped cards, completed revision, Return to Pending, Backup Manager, and OneDrive screen.
11. Open Diagnostics immediately and after structural actions; confirm structural-refresh status displays without error.
12. Background/resume and force-stop/relaunch.
13. Run database integrity and inspect logcat for frozen controls, structural-refresh failures, and unhandled exceptions.
