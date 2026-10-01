# IronCycle 1.99.4

## Startup workout-render deduplication

- Prevents successful startup Billing reconciliation from rebuilding the workout when Lifetime ownership was already stored before the initial render.
- Preserves a rebuild when Billing creates a real entitlement transition or when reconciliation happens outside startup.
- Retains the privacy-safe 1.99.3 UI trace to verify one card construction per visible session and direct reps-field update behavior.
- Makes no changes to weight calculations, target ownership, card replacement, structural refresh, viewport behavior, database schema, OneDrive, or backup formats.
