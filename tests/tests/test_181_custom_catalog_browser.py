from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def setup_db(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    import database
    database.DB_PATH=str(tmp_path/'catalog-browser.db')
    database.init_and_seed_db()
    return database

def test_version_schema_and_catalog():
    constants=(ROOT/'constants.py').read_text(encoding='utf-8')
    assert 'APP_VERSION = "1.81.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 19' in constants
    from exercise_catalog import CATALOG_VERSION
    assert CATALOG_VERSION == 5

def test_custom_exercise_is_in_unified_browser(tmp_path,monkeypatch):
    database=setup_db(tmp_path,monkeypatch)
    database.create_classified_exercise('Big Buster','Abs','trunk_flexion','Bodyweight')
    entries=database.exercise_catalog_browser_entries()
    row=next(x for x in entries if x['stable_name']=='Big Buster')
    assert row['name']=='Big Buster'
    assert row['source']=='custom'
    assert row['catalog_id'] is None
    assert row['category']=='Abs'

def test_custom_display_name_is_searchable_without_changing_key(tmp_path,monkeypatch):
    database=setup_db(tmp_path,monkeypatch)
    database.create_classified_exercise('Big Buster','Abs','trunk_flexion','Bodyweight')
    database.set_exercise_display_name('Big Buster','Big Buster Deluxe')
    row=next(x for x in database.exercise_catalog_browser_entries() if x['stable_name']=='Big Buster')
    assert row['name']=='Big Buster Deluxe'
    assert row['stable_name']=='Big Buster'
    assert row['source']=='custom'

def test_browser_uses_unified_entries_and_labels_custom_source():
    source=(ROOT/'main.py').read_text(encoding='utf-8')
    assert 'database.exercise_catalog_browser_entries()' in source
    assert 'source_label="My Exercise"' in source
    assert 'No matching built-in or custom exercises.' in source
