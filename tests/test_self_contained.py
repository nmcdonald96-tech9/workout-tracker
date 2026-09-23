from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_no_progression_or_workout_service_dependency():
 m=(ROOT/'main.py').read_text();d=(ROOT/'database.py').read_text()
 assert 'services.progression_service' not in m+d
 assert 'services.workout_service' not in m+d
 for name in ('progression_clarity','simulate_progression','calculate_set_specific_progression','WorkoutStateService','workout_progress'): assert name in m+d
 ast.parse(m);ast.parse(d)
def test_version_schema_and_assets():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.11.3"' in c;assert 'DATABASE_SCHEMA_VERSION = 10' in c
 assert (ROOT/'assets/icon.png').is_file();assert (ROOT/'assets/ironcycle_splash_animation.webp').is_file()