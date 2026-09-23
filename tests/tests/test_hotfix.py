from pathlib import Path
import ast
R=Path(__file__).parents[1]
def test_hotfix():
 m=(R/'main.py').read_text();d=(R/'database.py').read_text();c=(R/'constants.py').read_text()
 assert 'ft.alignment.center' not in m and 'ft.Alignment(0,0)' in m
 assert 'services.progression_service' not in m+d and 'services.workout_service' not in m+d
 assert 'APP_VERSION = "1.11.4"' in c and 'DATABASE_SCHEMA_VERSION = 10' in c
 ast.parse(m);ast.parse(d)