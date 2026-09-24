from pathlib import Path
import ast
ROOT=Path(__file__).parents[1]
def test_version_schema_assets():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.11.1"' in c; assert 'DATABASE_SCHEMA_VERSION = 10' in c
 assert (ROOT/'assets/icon.png').stat().st_size>0; assert (ROOT/'assets/ironcycle_splash_animation.webp').stat().st_size>0
def test_splash_wiring():
 s=(ROOT/'main.py').read_text()
 for x in ('build_startup_splash','ironcycle_splash_animation.webp','await asyncio.sleep(1.44)','assets_dir="assets"','except (TypeError, AttributeError)'): assert x in s
 ast.parse(s)
