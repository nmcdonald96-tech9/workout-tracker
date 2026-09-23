# Testing IronCycle

Run `pytest` from the repository root. `pytest.ini` collects the active suite and excludes preserved historical release contracts that assert old application versions. New behavior belongs in the active suite. Point-in-time packaging assertions belong in `tests/historical_release_contracts/` only when retained for archaeology. Duplicate test modules are not permitted.
