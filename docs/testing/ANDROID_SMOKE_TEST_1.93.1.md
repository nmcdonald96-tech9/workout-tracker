# IronCycle 1.93.1 Android smoke test

Record device model, Android version, install type, source commit, APK version code, and pass/fail.

1. Upgrade over 1.93.0 and confirm version 1.93.1, schema 20, existing history, and database integrity `ok`.
2. Scroll to a standalone pending exercise near the bottom, change weight, and leave the field. Confirm derived reps and plate feedback update without a flash or jump.
3. Repeat the weight edit on the first and last members of a superset. Confirm the viewport and active exercise remain stable.
4. Edit reps and valid RPE. Confirm neither edit remounts or jumps.
5. Enter `1..` as weight. Confirm completion is blocked and the last valid durable draft is retained. Correct it and confirm normal use resumes.
6. Create a superset from Workout Structure & Supersets. Confirm immediate visible grouping and a success message without leaving Workout.
7. Remove the group. Confirm immediate visible ungrouping and a success message.
8. Complete one grouped set and confirm the established resolver advances to the correct member and set.
9. Exercise Add Set and Remove Set and confirm structural changes still rebuild safely.
10. Regression-check completed revision save/cancel, Return to Pending, Jump To, readiness, backup, Billing, and OneDrive screens.
11. Review logcat for `Frozen controls cannot be updated`, `[structural_refresh] FAILED`, unhandled tasks, blank canvas, and duplicate canvas. Expected result: none.
