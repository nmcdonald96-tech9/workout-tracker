# IronCycle 2.0 release-candidate checklist

## Immutable identity
- Exact source commit recorded.
- Version name, version code, package ID, workflow run, signer, APK hash, and AAB hash recorded.
- Deterministic source archive and tracked-file manifest preserved.

## Packaging
- APK signer and package metadata verified.
- AAB signature and bundle structure verified.
- Billing permission present.
- Required Python packages and IronCycle Billing extension packaged.
- No database, backup, token cache, keystore, or repository metadata in release artifacts.

## Product gates
- Workout interaction Android verified.
- Entitlement and limited mode Android verified.
- Backup and recovery Android verified.
- Accessibility and display modes Android verified.
- Clean-install First Setup accepted.
- Existing-user upgrade accepted.

## Final Play delivery
- AAB accepted by Google Play testing.
- Play-delivered install/upgrade launches.
- Billing ownership restores.
- OneDrive verifies.
- Database integrity is `ok`.
- Frozen workout regression passes.
