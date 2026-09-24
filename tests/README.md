# IronCycle test layout

- `tests/test_*.py`: active behavioral, integration, migration, and release tests collected by default.
- `tests/historical_release_contracts/`: preserved point-in-time release contracts. These intentionally assert obsolete version strings and are excluded from normal collection.
- The former duplicate `tests/tests/` tree was removed.

Run the supported suite with `pytest`. Historical contracts are reference fixtures, not current-release gates.
