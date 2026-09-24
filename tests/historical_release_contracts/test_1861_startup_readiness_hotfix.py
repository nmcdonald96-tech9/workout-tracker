from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_version_and_schema():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.86.1"' in c; assert 'DATABASE_SCHEMA_VERSION = 20' in c

def test_batched_saved_sets_include_ownership():
 m=(ROOT/'main.py').read_text()
 assert "COALESCE(weight_source,'target'), COALESCE(reps_source,'target') FROM workout_sets" in m
 assert 'is_complete, weight_source, reps_source in cursor.fetchall()' in m
 assert 'is_complete, weight_source, reps_source))' in m

def test_card_load_is_legacy_compatible_and_atomic():
 m=(ROOT/'main.py').read_text()
 assert 'if len(saved_row) == 10:' in m
 assert 'saved_row = (*saved_row, "target", "target")' in m
 assert 'loaded_drafts = []' in m
 assert 'self.app.sets[self.db_id] = loaded_drafts' in m

def test_186_contract_retained():
 m=(ROOT/'main.py').read_text()
 assert 'from services.rpe_service import RPE_ERROR, normalize_rpe' in m
 assert 'ownership_summary(draft, today, normal)' in m
