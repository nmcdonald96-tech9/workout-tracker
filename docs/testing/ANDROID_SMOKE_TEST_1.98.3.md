# IronCycle 1.98.3 Android smoke test

1. Upgrade over 1.98.2; confirm version 1.98.3, schema 20, integrity `ok`.
2. Change a pending weight and leave the field. Confirm derived reps and plate feedback repaint immediately.
3. Enter valid RPE and tap Complete on a standalone nonfinal set. Confirm row dimming and next-set activation immediately.
4. Reopen that set and confirm immediate repaint.
5. Repeat weight and completion changes near the bottom; confirm no flash, viewport movement, or top snap.
6. Complete A1 and A2; confirm deliberate navigation still targets the current revisioned card.
7. Test Jump To buttons after multiple card revisions.
8. Add/Remove Set, uneven groups, Skip/Unskip, final-set logging, completed revision, Return to Pending, Weeks and days, and Diagnostics.
9. Background/resume and force-stop/relaunch.
10. Run integrity and inspect logcat for card lookup, revision update, frozen controls, structural refresh, and unhandled errors.
