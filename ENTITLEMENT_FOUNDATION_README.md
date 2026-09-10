# IronCycle 1.48.0 Entitlement Foundation

This package adds a 14-day trial and data-safe limited-mode foundation. The lifetime product ID is `ironcycle_lifetime_unlock`.

Important: Google Play Billing is not connected in this build. Purchase and restore-purchase controls do not grant ownership or charge users. Do not mark the Play listing free yet.

Licensing data is stored in `ironcycle_entitlement.json` beside the app database, not inside `workout_tracker.db`. Normal IronCycle backups therefore cannot reset the trial or grant lifetime access.

Core premium gates currently cover workout logging, set prescription editing, adding exercises, creating/cloning mesocycles, and advancing a plan. Viewing history and all backup/restore paths remain available.
