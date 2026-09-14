# IronCycle 1.49.1 Billing Hardening

- Automatic startup and resume ownership reconciliation
- Previously verified access is never revoked by transient or inconclusive checks
- Pending purchase returns promptly and is recovered on a later reconciliation
- Duplicate billing operations return a safe busy state
- Purchase stream events are cached for lifecycle recovery
- Verification tokens do not cross into Python or diagnostics
- Privacy-safe billing attempt/result history added to entitlement storage
- Purchase, restore, cancellation, decline, offline, and timeout statuses distinguished
- Database schema remains 16; product ID and billing dependencies unchanged
