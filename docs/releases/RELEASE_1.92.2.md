# IronCycle 1.92.2

## Structural refresh fault containment

- Preserves a structural-refresh request when its apply callback fails.
- Merges failed work with later refresh requests without losing promoted flags.
- Adds an explicit bounded retry path for preserved structural work.
- Prevents repeated apply failures from creating an uncontrolled retry loop.
- Expands coordinator diagnostics for pending, scheduled, and running state.
- Retains post-callback workout-tree replacement and refresh coalescing.
- Leaves pending-set persistence, progression, target ownership, RPE, completed-exercise revision, backup, billing, navigation policy, and exercise identity unchanged.
- Database schema remains version 20. No migration is required.
