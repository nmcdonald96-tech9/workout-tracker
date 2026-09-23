from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def setup_db(tmp_path,monkeypatch):
    import database
    monkeypatch.setattr(database,'DB_PATH',str(tmp_path/'unified.db'))
    database.init_and_seed_db()
    return database

def test_release_contract():
    c=(ROOT/'constants.py').read_text()
    assert 'APP_VERSION = "1.82.0"' in c
    assert 'DATABASE_SCHEMA_VERSION = 19' in c

def test_custom_exercise_is_in_single_catalog_source(tmp_path,monkeypatch):
    database=setup_db(tmp_path,monkeypatch)
    database.create_classified_exercise('Big Buster','Abs','trunk_flexion','Bodyweight')
    entries=database.exercise_catalog_browser_entries()
    row=next(x for x in entries if x['stable_name']=='Big Buster')
    assert row['source']=='custom'
    assert row['catalog_id'] is None
    assert database.exercise_catalog_summary(entries)=='71 built-in definitions • 1 custom exercise'

def test_both_browsers_use_same_source_and_scrollable_list():
    source=(ROOT/'main.py').read_text()
    assert source.count('entries=database.exercise_catalog_browser_entries()') >= 2
    assert source.count('ft.ListView(expand=True') >= 2
    assert source.count('clip_behavior=ft.ClipBehavior.HARD_EDGE') >= 2
    assert 'page_height=float(getattr(self.page' in source

def test_standard_browser_searches_stable_and_display_names():
    source=(ROOT/'main.py').read_text()
    assert "('name','stable_name','category','family_label','pattern','equipment')" in source
    assert "source='My Exercise' if x['source']=='custom' else 'Built-in'" in source