# IronCycle 1.99.14

## Packaging reproducibility and 2.0 release-candidate preparation

- Promotes Android accessibility/display-mode acceptance to verified 1.99.13.
- Disables closed-testing entitlement simulation controls in the release-candidate packaging source.
- Captures the immutable source commit, commit date, tracked-file SHA-256 manifest, deterministic `git archive` source bundle, and source archive hash before runner normalization.
- Records APK/AAB version name, version code, package ID, workflow run identity, pinned toolchain, and release-control state.
- Verifies APK package identity, version metadata, Billing permission, permanent signer, packaged Python dependencies, billing extension assets, AAB signature, and bundle structure.
- Generates SHA-256 hashes for verified APK and AAB artifacts and uploads all evidence beside both binaries.
- Leaves workout behavior, display modes, entitlement policy, recovery, Billing, OneDrive, progression, superset order, backup format, and schema 20 unchanged.
