# IronCycle 1.99.13 Android display-mode stabilization

1. Force-stop and launch in Standard. Change Set 1 weight and confirm reps repaint.
2. Change Standard to Focus. Confirm one visual rebuild, then change Set 2 weight and confirm reps repaint.
3. Change Focus to Detailed. Change Set 3 weight and confirm reps repaint.
4. Change Detailed to Standard. Repeat Set 1 and Set 2 edits.
5. Confirm no `reps_update_exception` appears after any mode change.
6. Copy Support Trace. For each mode change confirm request, dialog closed, scheduled or coalesced, rebuild started, and rebuild finished. Confirm one new card pair per visible session per completed rebuild.
7. Change mode through Profile Settings and confirm one rebuild, selector synchronization, portrait scrolling, and no duplicate persistence/rebuild.
8. Force-stop/relaunch and confirm mode persistence.
9. Recheck long title/actions lane, enlarged text, rotation, frozen workout behavior, A1-first superset flow, Billing, OneDrive, backup, and integrity `ok`.
