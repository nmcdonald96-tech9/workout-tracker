# IronCycle 1.97.0

## Workout Composition and Compatibility Cleanup

- Weeks and days selection now closes its modal before applying the selected workout context, preventing the stale open-dialog interaction seen on Android.
- Centralizes application of typed superset execution instructions: category focus, active exercise selection, intentional viewport navigation, audit recording, and rebuild dispatch now use one composition path.
- Routes execution navigation through the 1.96 workout-view and viewport controllers rather than scattering direct state writes.
- Retains the legacy resolver adapter as an explicit transitional compatibility contract until all supported callers are proven migrated.
- Preserves the Android-verified 1.95.2 mounted-list Add/Remove Set path, 1.96 controller state ownership, immediate grouping, Jump To, uneven-set routing, compact skipped cards, completed revision, Billing, OneDrive, and backups.
- Schema remains 20. No migration.
