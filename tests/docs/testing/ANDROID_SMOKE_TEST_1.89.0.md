# IronCycle 1.89.0 Android smoke test

1. Build the APK from the 1.89.0 source with the existing authentic Android workflow.
2. Confirm the installed app reports version `1.89.0` and launches without a Python import error.
3. On a fresh install, complete First Setup and verify the workout screen renders.
4. On an upgrade install over 1.88.0, confirm the existing active mesocycle, completed history, custom exercises, and settings remain present.
5. Open a workout day containing at least two categories and two exercises.
6. Tap each category quick-navigation entry. Confirm the correct category header is shown and no blank canvas appears.
7. Expand and collapse a category. Confirm reopening scrolls to the category and preserves the active exercise.
8. Complete one set without entering RPE. Confirm the prompt directs entry of RPE for the active set.
9. Enter a valid RPE, complete the set, and confirm the active-set position advances.
10. Complete all sets for an exercise. Confirm the UI offers to log the exercise and then advances normally.
11. Verify bodyweight, weighted-bodyweight, and normal weighted targets display correctly, including `BW`, `BW + N lbs`, and `N lbs`.
12. Exercise superset navigation for one round and confirm the next member and correct pending set open.
13. Background and resume the app during a workout. Confirm the same day, exercise, and drafts remain selected.
14. Open History, Generator, Exercise Library, Settings, Backup Manager, and Lifetime Unlock. Confirm every route opens without an exception.
15. Create a local backup, restore it in a disposable test install, and run the in-app database integrity check.
16. Close and relaunch the app. Confirm startup, navigation, and the active workout still work.

Record device model, Android version, install type, source commit, APK version code, and pass or fail for every step.
