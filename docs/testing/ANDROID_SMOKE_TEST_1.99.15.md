# IronCycle 1.99.15 packaging acceptance continuation

1. Run the APK-only workflow and confirm 241 tests, Flutter 3.44.8, Billing wheel staging, APK signer/package/version/Billing permission checks, artifact hashes, and evidence upload.
2. Upgrade-install the APK and confirm version 1.99.15, schema 20, integrity `ok`, existing history/settings, Lifetime ownership restoration, OneDrive Graph access, backups, and all internal regression checks.
3. Confirm Diagnostics says entitlement test controls are disabled and APK packaging is Android verified 1.99.14.
4. Run the combined APK/AAB workflow from the same commit. Confirm APK signer, AAB signature/structure, package/version, dependencies, Billing wheel, and hashes.
5. Repeat the combined workflow from the same commit. Confirm source commit, tracked-file manifest, source archive, and Billing wheel hashes match. Record any signed-binary hash differences with run metadata.
6. Upload the verified AAB to Google Play testing, install through Play, and run the final 2.0 release-candidate matrix.
