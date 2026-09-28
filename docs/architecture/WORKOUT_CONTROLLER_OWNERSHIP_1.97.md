# Workout controller ownership after 1.97

- `services/superset_execution_service.py` decides the next eligible session and set.
- `controllers/workout_view_controller.py` owns category keys, collapse state, active exercise state, and category focus policy.
- `controllers/workout_viewport_controller.py` owns preserve-offset, scroll-to-key, reset-top, and no-op viewport intent.
- `main.py` remains the Flet composition root and applies typed instructions to mounted controls.
- Add/Remove Set remains a mounted-list child replacement and does not invoke execution navigation.
- Database transactions remain in persistence services and `database.py`; controllers open no connections and commit no transactions.
- The legacy `resolve_next_group_step` adapter remains temporarily for supported callers and will be removed only after import/call-site proof.
