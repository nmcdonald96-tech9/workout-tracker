from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_version_schema_and_runtime_compatibility():
    c=(ROOT/"constants.py").read_text();m=(ROOT/"main.py").read_text();d=(ROOT/"database.py").read_text()
    assert 'APP_VERSION = "1.13.0"' in c
    assert 'DATABASE_SCHEMA_VERSION = 11' in c
    assert 'ft.alignment.center' not in m
    assert 'services.progression_service' not in m+d
    assert 'services.workout_service' not in m+d
    for name in ("main.py","database.py","constants.py","exercise_catalog.py"):ast.parse((ROOT/name).read_text())