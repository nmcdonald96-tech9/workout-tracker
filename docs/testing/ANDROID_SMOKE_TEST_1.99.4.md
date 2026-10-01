# IronCycle 1.99.4 Android test

1. Force-stop and launch with stored Lifetime ownership.
2. Before visiting History, open Diagnostics and confirm the trace shows one `card_created` and one `card_built` per visible session.
3. Edit Set 1, Set 2, and Set 3 weights and confirm reps update immediately in the same rows.
4. Confirm `reps_update_returned` and no `reps_update_exception` entries.
5. Confirm `startup_billing_rebuild_coalesced` appears.
6. Recheck Complete, next-set activation, final logging, Add/Remove Set, supersets, Jump To, Weeks and days, Billing, OneDrive, and integrity.
