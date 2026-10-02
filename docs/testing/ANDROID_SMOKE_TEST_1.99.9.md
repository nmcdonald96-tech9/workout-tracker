# IronCycle 1.99.9 Android entitlement acceptance

## Safety first
Create a current backup. Entitlement simulations are memory-only and restart-cleared. Do not clear app storage during an established-user upgrade test.

## Matrix
For each state in **Entitlement Acceptance Test**, reopen Diagnostics and record the entitlement acceptance lines.

1. **Trial not started:** first premium action starts the trial and allows the action.
2. **Trial active:** workout logging and plan mutation are allowed.
3. **Trial expired:** premium mutation is blocked and Lifetime Unlock opens; History, Diagnostics, Backup Manager, local export, local restore, OneDrive backup/restore, and existing data remain available.
4. **Lifetime unlocked:** premium mutation is allowed; simulated ownership disappears after restart.
5. **Purchase check pending:** with real stored Lifetime/trial access, premium mutation remains allowed.
6. **Temporarily offline:** with real stored Lifetime/trial access, premium mutation remains allowed.
7. Return to **Real stored state** and confirm the original entitlement is unchanged.
8. Force-stop/relaunch and confirm no simulation remains.
9. Confirm Billing restoration, OneDrive Graph verification, schema 20, and integrity `ok`.
10. Recheck the frozen workout regression: repeated weight edits, deleted-reps restoration, manual reps, Complete, final logging, Add/Remove Set, one normal A1-first superset handoff, Jump To, and Weeks and days.
