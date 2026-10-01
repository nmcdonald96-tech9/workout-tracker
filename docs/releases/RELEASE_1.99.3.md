# IronCycle 1.99.3

## Privacy-safe workout UI trace

- Adds a bounded in-memory trace for card construction, weight events, derived-draft updates, and mounted reps-field updates.
- Adds Copy UI Trace and Clear UI Trace actions to Diagnostics.
- Trace excludes actual weights, reps, RPE, exercise names, account identifiers, tokens, and backup contents.
- Preserves the 1.99.2 event-value authority logic without adding card replacement or structural refresh.
- Schema remains 20. No migration.
