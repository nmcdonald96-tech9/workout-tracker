# IronCycle 1.99.6

## Reps restore callback hotfix

- Corrects the reps blur callback to use its actual event parameter.
- Prevents the `NameError: name ev is not defined` crash introduced in 1.99.5.
- Retains solid target restoration, blank numeric hints, startup deduplication, weight-derived reps, UI tracing, and schema 20.
