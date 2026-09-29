# IronCycle 1.98.6

## Exact-commit reproduction build

- Runtime source is recovered directly from commit `4a0d2841bb80cf537651da40c3ba1b3bd0146614`, which produced the physically working 1.95.2 APK.
- Runtime `main.py` is byte-identical to that commit.
- Only the declared app version and test expectations change to 1.98.6.
- Android packaging removes `.git` before Flet build so repository metadata and credentials cannot enter the APK.
- Diagnostic reproduction candidate only; not yet a Google Play upload candidate.
- Schema remains 20.
