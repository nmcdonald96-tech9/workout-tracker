# IronCycle 1.9.1 Architecture Stabilization

Behavioral reference: Android-verified IronCycle 1.9.0. Database schema remains 10.

Production progression policy is owned by `services/progression_service.py`, with compatibility exports in `database.py`. Backup snapshot encoding, decoding, and validation are delegated to `services/backup_service.py`. `ApplicationFoundation` synchronizes active controller state during rebuilds.

Custom progression fields may independently inherit defaults. Maximum progression weight can therefore be configured without overriding the normal movement or equipment step.
