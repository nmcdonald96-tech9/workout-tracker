# IronCycle 1.99.0

## 2.0 release-candidate hardening

- Adds a privacy-safe 2.0 Readiness section to Diagnostics.
- Reports database, Billing, OneDrive Graph, onboarding, and exercise-identity gates without workout values, tokens, account identifiers, or backup contents.
- Lists the remaining physical acceptance gates for 2.0.
- Retains the Android-verified 1.98.8 workout interaction and Weeks and days behavior unchanged.
- Retains deterministic Billing dependency locks, including `jni_flutter 1.0.3`.
- Makes no schema, progression, workout-entry, Billing-flow, OneDrive-flow, or backup-format changes.
