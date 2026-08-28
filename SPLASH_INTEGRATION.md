# IronCycle 1.11.1 Splash Integration

- `assets/icon.png` is the static build icon and startup fallback.
- `assets/ironcycle_splash_animation.webp` is the 36-frame in-app splash.
- Splash duration is 1.44 seconds.
- Older Flet environments fall back to the static PNG if the enhanced Image constructor is unavailable.
- Database schema remains 10.
- Workout and progression logic are unchanged from 1.11.0.

## Repository update

Replace `main.py`, `database.py`, and `constants.py`; add both files under `assets/`. Preserve the other repository folders already present (`app`, `components`, `services`, `views`, workflows, requirements, and privacy files).
