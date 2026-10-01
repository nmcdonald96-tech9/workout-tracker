# IronCycle 2.0 release-readiness matrix

## Existing-user upgrade
- Preserve schema 20 database, history, schedule, drafts, entitlement, and OneDrive state.
- Verify integrity before and after upgrade.

## Clean install
- First Setup opens and completes.
- Equipment profile and starter plan save.
- Workout schedule renders.
- Backup restoration remains available.

## Entitlement
- Fresh trial, active trial, expiration, limited mode, Lifetime purchase, restore purchase, offline stored ownership, transient Billing failure.
- Backup export remains available in every state.

## Recovery
- Current ICBACKUP restore, legacy TXT restore, damaged-backup rejection, entitlement isolation, OneDrive upload/list/download, Graph redirect downloads, interrupted cloud action.

## Lifecycle
- Background/resume, force-stop/relaunch, valid draft durability, invalid partial-input protection, completed-set durability, schedule-position coherence.

## Accessibility and layouts
- Text scaling, touch targets, labels for icon actions, color-independent status, portrait, landscape, narrow phone, large phone/tablet, Focus/Compact/Detailed.

## Packaging and Play
- Deterministic dependencies, permanent signer, package ID, Billing permission, no repository metadata or databases in artifacts, APK acceptance, Play-delivered acceptance.
