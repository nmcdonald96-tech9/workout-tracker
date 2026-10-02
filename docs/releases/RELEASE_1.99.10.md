# IronCycle 1.99.10

## Backup and recovery acceptance

- Adds one privacy-safe backup/recovery acceptance report and checklist.
- Adds non-destructive ICBACKUP inspection for integrity and version metadata.
- Verifies current ICBACKUP, legacy TXT eligibility, invalid-backup rejection, pre-restore rollback snapshots, restore-before-migration validation, and post-migration integrity.
- Verifies entitlement isolation from workout backups.
- Verifies OneDrive upload/list/download contracts, explicit Graph 302 Location downloads, SHA-256 manifest checks, and interrupted restore guards.
- Keeps backup contents out of Diagnostics and acceptance reports.
- Freezes workout interaction, entitlement policy, superset ordering, progression, backup format, OneDrive authentication, and schema 20.
