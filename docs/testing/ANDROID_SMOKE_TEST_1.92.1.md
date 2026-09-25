# IronCycle 1.92.1 Android smoke test

1. Upgrade over 1.92.0 and confirm the app reports version `1.92.1`.
2. Confirm database schema 20 and run the in-app database integrity check.
3. During an active workout, rapidly add, remove, and copy sets; confirm the card settles without a blank canvas or frozen-control exception.
4. Rapidly expand/collapse a category and switch category navigation; confirm navigation headers and the canvas remain synchronized.
5. Enter valid weight, reps, and RPE, leave the card, return, and confirm the durable pending draft remains intact.
6. Complete a set while another structural refresh is queued; confirm the correct next pending set opens.
7. Exercise one superset round and confirm the next member and pending set open correctly.
8. Background and resume during an active workout; confirm drafts, active position, and navigation remain stable.
9. Review logcat for `[structural_refresh] FAILED`, frozen-control errors, and unhandled task exceptions. The expected result is none.
10. Close and relaunch the app; confirm startup, active workout restoration, and database integrity.
