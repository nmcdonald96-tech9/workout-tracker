# IronCycle 1.92.0 Android smoke test
Record device model, Android version, install type, source commit, APK version code, and pass/fail for every step.
1. Build the signed APK with the authentic Android workflow.
2. Upgrade over 1.91.1. Confirm version 1.92.0, schema 20, integrity OK, and existing data.
3. Open a workout with two categories and two pending exercises.
4. Edit weight so reps auto-adjust. Leave the field and confirm refresh without a frozen-control error.
5. Manually edit reps and confirm user ownership survives another refresh.
6. Tap Add Set twice quickly. Confirm exactly two rows are added and remain usable.
7. Tap Remove Set. Confirm one trailing row is removed and other drafts are unchanged.
8. Use Copy Previous Set. Confirm weight/reps copy, RPE stays blank, and the correct set is active.
9. Enter RPE 8.5 and complete a set. Confirm the next set becomes active.
10. Complete the final set and confirm the exercise-log action renders.
11. Reopen a completed exercise, revise a value, save, and verify the rebuilt card.
12. Cancel a second revision and confirm original completed rows return.
13. Skip and unskip an exercise. Confirm counts, navigation, and active card update once.
14. Complete one superset round. Confirm the next member and pending set open and scroll into view.
15. Rapidly Add Set, Remove Set, then change categories. Confirm no duplicate canvas, stale card, or crash.
16. Background and resume with a valid pending draft. Confirm persistence and no refresh exception.
17. Force-stop and relaunch. Confirm drafts, ownership sources, and RPE restore.
18. Open History, Generator, Exercise Library, Settings, Backup Manager, and Lifetime Unlock.
19. Create a local backup and run the database integrity check.
20. Review logs. `Frozen controls cannot be updated`, unhandled exceptions, and duplicate refreshes must be absent.
