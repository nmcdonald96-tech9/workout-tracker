# IronCycle 1.92.3 Android smoke test

1. Upgrade over 1.92.2 and confirm version 1.92.3, schema 20, and database integrity `ok`.
2. Open a workout containing at least three categories.
3. Tap the middle Jump To button. Confirm the selected category opens, the other categories collapse, and the selected header scrolls into view after one rebuild.
4. Tap the first and last Jump To buttons. Confirm each reaches a distinct category without becoming inert.
5. Repeatedly tap the currently selected category. Confirm no blank canvas, duplicate controls, or exception appears.
6. Add the first exercise in a category not currently present. Confirm one new Jump To button appears immediately without leaving the workout view.
7. Tap the new button. Confirm its category opens and scrolls into view.
8. Add another exercise to that category. Confirm the existing Jump To button is not duplicated.
9. Delete the final pending exercise in a disposable category. Confirm its Jump To button disappears immediately.
10. Enter pending weight, reps, and RPE, use Jump To, then return. Confirm the draft values and ownership remain unchanged.
11. Complete one superset handoff. Confirm the established next-member progression remains correct.
12. Background and resume, then force-stop and relaunch. Confirm active workout restoration and database integrity.
13. Review logcat for `Frozen controls cannot be updated`, unhandled task exceptions, blank canvas, and structural-refresh failure markers.
