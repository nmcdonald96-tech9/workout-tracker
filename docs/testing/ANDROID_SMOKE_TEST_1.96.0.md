# IronCycle 1.96.0 Android smoke test

1. Upgrade over Android-verified 1.95.2; confirm version 1.96.0, schema 20, integrity `ok`.
2. Add and Remove Set near the bottom; confirm no flash, top snap, viewport movement, or warning.
3. Repeat on first and last superset members.
4. Complete A1 and A2; confirm deliberate execution navigation remains correct.
5. Create and remove a superset; confirm immediate synchronization.
6. Use every Jump To button and category header; confirm collapse, ordering, and post-mount scroll behavior.
7. Switch workout day/week and return; confirm viewport intents do not leak across views.
8. Verify uneven groups, Skip/Unskip, weight/reps edits, completed revision, and Return to Pending.
9. Background/resume and force-stop/relaunch during a pending workout.
10. Run integrity and inspect logcat for frozen controls, controller exceptions, structural-refresh failures, blank canvas, and unhandled tasks.
