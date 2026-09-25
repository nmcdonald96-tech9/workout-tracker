# IronCycle 1.91.0 Android smoke test

1. Upgrade over 1.90.1 and confirm schema 20 and database integrity OK.
2. Edit pending weight and reps, leave the card, return, and confirm both remain.
3. Change weight and confirm weight-derived reps. Manually override reps and confirm ownership survives a rebuild.
4. Enter RPE 8.5, navigate away, return, and confirm restoration.
5. Enter invalid partial input, background and resume, and confirm the last valid durable draft was not deleted.
6. Add and remove sets, background and resume, and verify both operations persist.
7. Complete one set, use Copy Previous Set, and confirm weight/reps copy while RPE stays blank.
8. Force-stop after a valid draft edit. Relaunch and confirm values and ownership restore.
9. Resume offline and confirm no cloud action starts and drafts remain.
10. Complete and log the exercise, then run database integrity check.
