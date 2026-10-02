# IronCycle 1.99.10 Android backup and recovery acceptance

## Safety
Use a disposable recovery installation or preserve the original APK data. Record the real entitlement and OneDrive state before each restore.

1. Create a current local ICBACKUP and confirm it appears newest first.
2. Restore that ICBACKUP; confirm automatic `__pre-restore.icbackup`, schema 20, integrity `ok`, history, schedule, drafts, and settings.
3. Restore a known-good legacy TXT backup; confirm pre-migration verification, migration to schema 20, post-migration integrity, and retained history.
4. Try empty, malformed, truncated, wrong-database, and oversized test inputs. Confirm clear rejection and unchanged live data.
5. Confirm entitlement remains the real stored entitlement after every workout backup restore.
6. Upload to OneDrive, refresh/list the manifest, download, and restore. Confirm SHA-256 and manifest verification.
7. Confirm Graph redirect download succeeds through the explicit 302 Location path.
8. Interrupt or disable network during cloud backup and cloud restore. Confirm controls recover, `_cloud_restore_running` clears, live data remains intact, and retry works.
9. Force-stop between download and confirmation, then relaunch. Confirm no partial restore is applied.
10. Restore the automatic pre-restore rollback point in the disposable installation.
11. Confirm Backup Manager remains available in Trial Expired simulation.
12. Return to Real stored entitlement; confirm Billing and OneDrive verification.
13. Recheck frozen workout behavior and normal A1-first superset flow.
14. Run integrity after every successful restore.
