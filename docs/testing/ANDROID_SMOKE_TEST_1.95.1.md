# IronCycle 1.95.1 Android smoke test

1. Upgrade over 1.95.0; confirm version 1.95.1, schema 20, integrity `ok`.
2. Open a grouped workout and navigate History then Workout; confirm no resolver import crash.
3. Create/remove a superset; confirm immediate refresh and no crash.
4. Add and Remove Set near the bottom; confirm the existing ListView stays mounted and the viewport does not flash or reset.
5. Repeat Add/Remove on first and last superset members.
6. Complete A1 and A2; confirm deliberate execution navigation still occurs.
7. Verify uneven sets, skipped compact cards, Unskip, weight/reps edits, completed revision, and Return to Pending.
8. Run integrity and inspect logcat for import errors, frozen controls, failed local card updates, and unhandled tasks.
