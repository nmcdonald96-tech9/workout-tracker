# IronCycle 1.94.0 Android smoke test

1. Upgrade over Android-verified 1.93.2; confirm version 1.94.0, schema 20, integrity `ok`.
2. Complete A1, A2, and A3 set 1; confirm deterministic handoff and return to A1 set 2.
3. Test unequal member set counts; confirm no nonexistent set opens.
4. Skip one member and complete another; confirm skipped/completed members are bypassed.
5. Leave one pending member; confirm that member continues normally.
6. Complete a standalone nonfinal set, then a final set; confirm next-set and logging behavior.
7. Change weight and confirm derived reps update without a flash or jump.
8. Add and Remove Set near the bottom and confirm viewport retention.
9. Create/remove a superset and confirm immediate synchronization.
10. Regression-check completed revision and Return to Pending.
11. Run integrity and inspect logcat for frozen controls, structural-refresh failures, duplicate progression, and unhandled tasks.
