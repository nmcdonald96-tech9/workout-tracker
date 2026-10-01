# IronCycle 1.99.1

## Android weight commit lifecycle

- Moves the existing weight-derived rep calculation into one idempotent commit helper.
- Uses the same helper for weight-field submit and blur events.
- Pressing Enter or moving focus now commits the derived reps through the same stable target baseline.
- Retains draft-only derived reps and never mutates authoritative target reps.
- Introduces no card replacement, viewport movement, schema change, progression change, or persistence redesign.
- Retains 1.99.0 readiness diagnostics and the Android-verified 1.98.8 interaction baseline.
