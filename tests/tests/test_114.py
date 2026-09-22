from pathlib import Path
import ast
from exercise_catalog import *
R=Path(__file__).parents[1]
def test_catalog():
 assert len(BUILTIN_EXERCISE_CATALOG)>=60
 assert movement_family_label('chest_flye')=='Chest Flye'
 assert 'Not specified' in get_angle_options('chest_flye')
 assert catalog_match('Cable Chest Fly')['item']['name']=='Cable Flye'
def test_ui_and_schema():
 m=(R/'main.py').read_text();d=(R/'database.py').read_text();c=(R/'constants.py').read_text()
 assert 'APP_VERSION = "1.14.0"' in c and 'DATABASE_SCHEMA_VERSION = 11' in c
 assert 'open_guided_exercise_creation(ex_name,cat,m_type' in m
 assert 'movement_family_label(x)' in m and 'open_catalog_browser' in m
 for x in ('catalog_id','movement_family','exercise_aliases','probable_dictionary_duplicates'):assert x in d
 ast.parse(m);ast.parse(d)
