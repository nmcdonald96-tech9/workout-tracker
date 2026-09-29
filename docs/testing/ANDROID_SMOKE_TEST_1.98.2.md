# IronCycle 1.98.2 Android smoke test

1. Upgrade over 1.98.1; confirm version 1.98.2, schema 20, integrity `ok`.
2. Change a pending set weight and leave the field. Confirm derived reps, plate feedback, and ownership guidance update immediately without navigating away.
3. Repeat weight editing near the bottom and confirm no flash, top snap, or viewport movement.
4. Enter valid weight, reps, and RPE; tap Complete on a standalone nonfinal set. Confirm the row dims and the next set becomes active immediately.
5. Reopen a completed set and confirm the card updates immediately.
6. Complete a final standalone set and confirm normal exercise logging.
7. Complete A1 and A2; confirm deliberate group navigation remains correct.
8. Verify unequal groups and skipped/completed member bypass.
9. Add and Remove Set and confirm exact viewport retention.
10. Verify Jump To, Weeks and days, compact skipped cards, completed revision, Return to Pending, and Diagnostics.
11. Background/resume and force-stop/relaunch.
12. Run integrity and inspect logcat for weight feedback, card replacement, frozen controls, structural refresh, and unhandled exceptions.
