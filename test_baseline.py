from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_source_only_baseline():
    for name in ("main.py","database.py","constants.py"):
        ast.parse((ROOT/name).read_text())
    assert not list(ROOT.rglob("*.pyc"))
    assert not list(ROOT.rglob("__pycache__"))
def test_schema_and_assets():
    c=(ROOT/"constants.py").read_text()
    assert 'DATABASE_SCHEMA_VERSION = 10' in c
    assert (ROOT/"assets/icon.png").is_file()
    assert (ROOT/"assets/ironcycle_splash_animation.webp").is_file()
