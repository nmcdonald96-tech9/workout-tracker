from pathlib import Path
import ast
R=Path(__file__).parents[1]
def test_unified_library_ui():
 s=(R/'main.py').read_text()
 assert '📚 Exercise Library' in s
 assert 'MY EXERCISES' in s and 'BROWSE CATALOG' in s and 'REVIEW MATCHES' in s
 assert 'Add to My Exercises' in s and 'Link Definition' in s and 'Unlink Definition' in s
 assert 'ft.ElevatedButton("Catalog", on_click=self.open_catalog_browser' not in s
 assert 'ft.ElevatedButton("📖 Dictionary"' not in s
 assert 'not self.exercise_exists_locally(ex_name)' in s
 assert 'not exercise_exists(ex_name)' not in s
 ast.parse(s)
def test_library_database_contract():
 s=(R/'database.py').read_text()
 for fn in ('get_library_exercises','add_catalog_to_library','update_library_classification','get_match_review_items','safe_link_library_exercise','safe_unlink_library_exercise'):
  assert f'def {fn}(' in s
 ast.parse(s)
def test_version_schema():
 s=(R/'constants.py').read_text();assert 'APP_VERSION = "1.15.0"' in s and 'DATABASE_SCHEMA_VERSION = 11' in s
