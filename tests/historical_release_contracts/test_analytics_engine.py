from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_engine_symbols_and_thresholds():
    source=(ROOT/'database.py').read_text()
    for symbol in ('get_comparable_exercise_sessions','analyze_exercise_trend','Insufficient Data','Possible Plateau','Established Recent Trend'):
        assert symbol in source
    ast.parse(source)
def test_version_schema():
    source=(ROOT/'constants.py').read_text()
    assert 'APP_VERSION = "1.12.1"' in source
    assert 'DATABASE_SCHEMA_VERSION = 10' in source