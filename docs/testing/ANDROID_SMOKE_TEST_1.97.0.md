# IronCycle 1.97.0 Android smoke test

1. Upgrade over Android-verified 1.96.0; confirm version 1.97.0, schema 20, integrity `ok`.
2. Open Weeks and days and select a day. Confirm the dialog closes immediately and the selected workout appears. Reopen and select another day; repeat across two weeks.
3. Add and Remove Set near the bottom; confirm no flash, movement, top snap, or warning.
4. Complete A1 and A2; confirm centralized execution application navigates to the correct member and set.
5. Create/remove a superset; confirm immediate synchronization.
6. Verify every Jump To button and category header.
7. Verify uneven groups, skipped/completed bypass, Skip/Unskip, weight/reps/RPE edits, completed revision, and Return to Pending.
8. Background/resume and force-stop/relaunch.
9. Run integrity and inspect logcat for modal lifecycle errors, controller exceptions, frozen controls, structural-refresh failures, and unhandled tasks.
