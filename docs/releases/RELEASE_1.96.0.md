# IronCycle 1.96.0

## Workout View Controller Decomposition

- Adds `controllers/workout_view_controller.py` as the framework-neutral owner of category keys, collapsed-category state, active exercise state, category focus, and category ordering policy.
- Adds `controllers/workout_viewport_controller.py` as the framework-neutral owner of current scroll offset, pending offset preservation, intentional key navigation, reset intent, and post-mount viewport instructions.
- Keeps Flet controls, `ListView.scroll_to()`, card construction, mounted-list child replacement, structural refresh dispatch, and rendering in `main.py`.
- Preserves the Android-verified 1.95.2 Add/Remove Set behavior without changing the mounted-list card replacement path.
- Preserves deliberate superset completion navigation, immediate superset assignment refresh, uneven-set handling, compact skipped cards, completed revision, Billing, OneDrive, and backup behavior.
- Schema remains 20. No migration.
