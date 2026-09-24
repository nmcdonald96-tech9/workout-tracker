# IronCycle 1.89.2

## Complete source regeneration

- Regenerated the complete source tree from the supplied IronCycle 1.89.1 Repomix bundle.
- Advanced the application version to `1.89.2`.
- Preserved database schema version 20, so no migration is required.
- Retained the 1.89.1 pure workout-helper extraction and all prior workout, progression, ownership, RPE, backup, billing, and Android packaging behavior.
- Restored the supplied application icon and splash animation binary assets.
- Synchronized active release-contract tests with the 1.89.2 patch version.

## Validation

The regenerated tree is intended to be validated with `pytest` and the existing authenticated Android APK/AAB workflow. Physical-device billing, OneDrive sign-in, and lifecycle behavior remain device-level checks.
