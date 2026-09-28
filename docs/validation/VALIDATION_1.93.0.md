# IronCycle 1.93.0 validation report

Automated results are recorded in `VALIDATION_RESULTS_1.93.0.txt`.

## Covered

- Baseline and post-change Python compilation.
- Focused completed-revision service tests.
- Complete supported pytest suite.
- Clean ZIP extraction, compilation, and complete-suite rerun.
- ZIP integrity and SHA-256 verification.
- Version 1.93.0 and unchanged schema 20.

## Not tested in this environment

- Physical Android/Flet behavior, lifecycle, force-stop recovery, and logcat.
- APK/AAB build, signing, installation, or upgrade behavior.
- Google Play Billing purchase, restore, or ownership reconciliation.
- Interactive OneDrive sign-in, Graph operations, or network failure behavior.

Use `docs/testing/ANDROID_SMOKE_TEST_1.93.0.md` as the physical-device acceptance gate.
