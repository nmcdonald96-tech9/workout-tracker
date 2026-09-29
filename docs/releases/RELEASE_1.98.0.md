# IronCycle 1.98.0

## Architecture Hardening and Compatibility Retirement

- Retires the legacy `resolve_next_group_step()` adapters from `database.py` and `services/superset_execution_service.py` after migrating active runtime and test callers to typed `resolve_post_set_action()` instructions.
- Migrates Jump To, category toggle, active-exercise selection, and Add Exercise navigation intent to the workout-view and viewport controllers.
- Adds privacy-safe controller and structural-refresh diagnostics without exposing workout values, account data, or tokens.
- Adds architecture guards for Flet/database isolation, policy ownership, mounted-list Add/Remove preservation, and authentic AAB workflow controller compilation.
- Updates the authentic APK/AAB workflow to compile the `controllers/` package explicitly.
- Preserves Android-verified 1.97 behavior and schema 20. No migration.
