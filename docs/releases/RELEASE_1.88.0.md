# IronCycle 1.88.0

## Test-Suite Separation and Repository Cleanup

- Removed the duplicated `tests/tests/` tree that caused pytest import-file mismatch errors.
- Preserved obsolete point-in-time version assertions under `tests/historical_release_contracts/`.
- Excluded historical release contracts from the supported default `pytest` run.
- Added `pytest.ini`, `tests/README.md`, and `docs/TESTING.md` to define the canonical test workflow.
- Active tests now validate current behavior instead of requiring obsolete application version strings.
- Retains the 1.87 stable workout snapshot loader and the 1.86.1 ownership/readiness fixes.
- Simplified the portrait set-entry label to `RPE`; the 1-10 and 0.5-step guidance remains in How RPE Works and validation feedback.

Database schema remains version 20. No migration is required.
