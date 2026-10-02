# IronCycle 1.99.9

## Trial expiration and limited-mode acceptance

- Adds a privacy-safe entitlement acceptance report to Diagnostics.
- Enables closed-testing, memory-only entitlement simulations for Not Started, Trial Active, Trial Expired, Lifetime Unlocked, Purchase Check Pending, and Temporarily Offline.
- Simulations disappear on restart and cannot persist Lifetime ownership or change real trial dates.
- Formalizes the access matrix: history, diagnostics, local backup export/restore, cloud backup/restore, and workout data preservation remain available in every entitlement state.
- Premium mutation is blocked only in true limited mode; transient states preserve access when the real stored state was already entitled.
- Freezes workout interaction, progression, startup render lifecycle, OneDrive implementation, backup formats, and schema 20.
