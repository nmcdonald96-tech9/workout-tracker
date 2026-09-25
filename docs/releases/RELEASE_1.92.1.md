# IronCycle 1.92.1

## Structural refresh recovery hardening

- Keeps the 1.92.0 post-callback structural-refresh boundary and coalescing behavior.
- Resets the scheduled state when dispatch fails, so pending structural work is not permanently stranded.
- Re-arms a second drain when a request arrives during an apply callback, even if that callback raises.
- Exposes coordinator running state for deterministic regression tests and diagnostics.
- Logs deferred structural-refresh failures instead of leaving an unobserved asynchronous task exception.
- Retains pending-set persistence, target ownership, RPE validation, progression behavior, navigation helpers, backup compatibility, and billing behavior.
- Database schema remains version 20. No migration is required.
