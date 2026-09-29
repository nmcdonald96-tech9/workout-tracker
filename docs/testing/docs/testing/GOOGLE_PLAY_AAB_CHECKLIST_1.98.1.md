# IronCycle 1.98.0 Google Play AAB checklist

Before upload:
1. Complete the 1.98 Android smoke test on the signed APK.
2. Run the authentic APK/AAB workflow from `release/ironcycle-1.98.0`.
3. Confirm workflow version is 1.98.0 and the generated version code is greater than the last Play Console upload.
4. Confirm APK permanent signer, package `com.ironcycle.myapp`, Billing permission, packaged MSAL/requests/PyJWT/cryptography, billing extension assets, AAB JAR signature, manifest, and dex checks pass.
5. Download `IronCycle-1.98.0-google-play.aab` and the verification report from the same workflow run.
6. Upload first to the intended Google Play testing track, not production.
7. Review Play Console automated checks, device compatibility, permission changes, and release notes before rollout.
8. Install from Play testing and verify entitlement restoration, startup, database integrity, Add/Remove Set, supersets, Jump To, Weeks and days, Backup Manager, and OneDrive screen.
9. Keep staged rollout or tester-only availability until Play-delivered acceptance passes.
