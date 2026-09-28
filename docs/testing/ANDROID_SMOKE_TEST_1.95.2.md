# IronCycle 1.95.2 Android smoke test

1. Upgrade over 1.95.1; confirm version 1.95.2, schema 20, integrity `ok`.
2. Add and Remove Set near the bottom. Confirm the card updates immediately while the screen remains at the exact position, with no flash, top alignment, or warning.
3. Repeat on the first and last members of a superset.
4. Create and remove a superset. Confirm labels update immediately without visiting History.
5. Complete A1 and A2. Confirm deliberate execution navigation still occurs.
6. Verify uneven sets, skipped compact cards, Unskip, weight/reps edits, completed revision, and Return to Pending.
7. Review logcat for resolver import errors, frozen-control errors, card-replacement failures, structural-refresh failures, and unhandled tasks.
