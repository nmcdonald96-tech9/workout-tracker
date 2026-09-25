# IronCycle 1.92.0 validation report
## Result
- Python compilation: **PASS**.
- Supported pytest suite: **PASS, 87 passed in 3.86 seconds**.
- Application version: **1.92.0**.
- Database schema: **20, unchanged**.
- Structural-refresh regression tests: **PASS**.
## Verified behavior
- Refresh requests coalesce while the active callback is still running.
- Merged requests promote navigation rebuild and canvas remount requirements.
- Requests arriving during a refresh schedule a second safe drain.
- ExerciseCard structure-changing callbacks no longer call the full rebuild inline.
- Existing pending-set, progression, ownership, RPE, backup, navigation, and release tests remain green.
## Not executed in this environment
- APK or AAB packaging and signing.
- Packaged Flet Android UI interaction.
- Google Play Billing and OneDrive interactive flows.
- Physical-device lifecycle and logcat verification.
Use `docs/testing/ANDROID_SMOKE_TEST_1.92.0.md` as the device gate.
