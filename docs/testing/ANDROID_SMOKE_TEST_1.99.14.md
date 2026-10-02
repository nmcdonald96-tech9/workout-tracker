# IronCycle 1.99.14 packaging reproducibility and RC acceptance

1. Run **Build IronCycle Android APK and AAB with authentic packaging** from the exact 1.99.14 commit.
2. Download the artifact bundle and preserve `SOURCE_COMMIT.txt`, tracked-file manifest, deterministic source archive/hash, build identity, APK/AAB hashes, artifact inventory, and packaging verification report.
3. Confirm APK package ID `com.ironcycle.myapp`, version name `1.99.14`, workflow version code, Billing permission, and permanent signer.
4. Confirm AAB signature and required base manifest/dex structure.
5. Confirm packaged evidence for msal, requests, PyJWT, cryptography, billing pubspec, billing extension, and pinned JNI Flutter dependency.
6. Repeat the workflow from the same commit. Confirm source commit, tracked-file manifest, and deterministic source archive hash match exactly. Signed APK/AAB hashes are recorded per run; compare contents and metadata if toolchain signing timestamps prevent byte identity.
7. Install the verified APK as an upgrade. Confirm schema 20, integrity `ok`, existing history, settings, entitlement, OneDrive, and active workout.
8. Confirm Entitlement Acceptance Test is absent while real trial/Lifetime behavior, Backup Manager, Diagnostics, and privacy-safe Support Trace remain available.
9. Recheck Standard/Focus/Detailed transitions and weight-derived reps after each transition.
10. Recheck long titles, portrait Profile Settings, Complete, final logging, Add/Remove Set, normal A1-first superset routing, Jump To, Weeks and days, Billing, OneDrive, backup/restore, background/resume, and force-stop/relaunch.
11. Install through the Google Play testing track using the generated AAB and run the final 2.0 Play-delivered acceptance matrix.
