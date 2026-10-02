# IronCycle 1.99.5

## Reps input clarity and target restoration

- Removes the numeric ghost hint from reps fields so an empty input cannot appear to contain a second conflicting value.
- Restores a deleted reps value to the authoritative prescribed target when the field loses focus.
- Returns the field to target ownership and displays the restored value as a normal solid value.
- Leaves nonblank manual and weight-derived reps unchanged.
- Retains startup render deduplication, privacy-safe UI tracing, weight-derived calculations, Complete behavior, and schema 20.
