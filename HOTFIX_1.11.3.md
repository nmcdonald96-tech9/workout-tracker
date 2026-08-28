# IronCycle 1.11.3 self-contained Android hotfix

The progression policy now lives in `database.py`; workout display helpers live in `main.py`. No runtime import from `services.progression_service` or `services.workout_service` remains. This avoids stale packaged `.pyc` modules. Splash assets remain bundled and schema remains 10.

Replace `main.py`, `database.py`, and `constants.py`; replace/add both files under `assets/`. No service-file replacement is required for this hotfix.
