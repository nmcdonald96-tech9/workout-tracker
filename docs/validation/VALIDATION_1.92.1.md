# IronCycle 1.92.1 validation report

## Result

- Python compilation: **PASS**.
- Supported pytest suite: **PASS, 90 passed in 3.97 seconds**.
- Application version: **1.92.1**.
- Database schema: **20, unchanged**.
- Structural-refresh recovery regression tests: **PASS**.

## Verified behavior

- A dispatch exception resets the scheduled flag and leaves pending work retryable.
- A request arriving during an apply callback schedules a second drain even if the first apply raises.
- Coordinator running and scheduled state returns to a consistent value after failure.
- Deferred Flet-task exceptions are logged with a structural-refresh diagnostic marker.
- Existing pending-set, progression, ownership, RPE, backup, navigation, billing, and release tests remain green.

## Not executed in this environment

- APK or AAB packaging and signing.
- Packaged Flet Android UI interaction.
- Google Play Billing and OneDrive interactive flows.
- Physical-device lifecycle and logcat verification.

Use `docs/testing/ANDROID_SMOKE_TEST_1.92.1.md` as the device gate.
