from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def block(name,next_name):
 s=(ROOT/'main.py').read_text(); a=s.index(f"    def {name}("); b=s.index(f"    def {next_name}(",a); return s[a:b]
def test_release():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.94.0"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
def test_helper_preserves_card_and_anchor():
 b=block('request_set_structure_refresh','on_add_set')
 assert 'active_exercise_by_category[category_key] = self.db_id' in b
 assert 'pending_scroll_key = exercise_anchor_key(self.db_id)' in b
 assert 'rebuild_navigation=False' in b and 'remount_canvas=True' in b
 assert b.count('request_structural_refresh(')==1
def test_add_uses_one_anchored_refresh():
 b=block('on_add_set','on_remove_set'); assert 'add_set(' in b and 'autosave_pending_sets()' in b
 assert 'request_set_structure_refresh("add_set")' in b
 assert 'request_structural_refresh(' not in b
def test_remove_uses_one_anchored_refresh_and_keeps_minimum():
 b=block('on_remove_set','trigger_delete_warning'); assert 'len(self.app.sets[self.db_id]) <= 1' in b
 assert 'remove_last_set(' in b and 'autosave_pending_sets()' in b
 assert 'request_set_structure_refresh("remove_set")' in b
 assert 'request_structural_refresh(' not in b
def test_weight_fix_retained():
 b=block('make_blur_handler','build_card'); assert 'refresh_weight_edit_feedback(set_idx)' in b
 assert 'request_structural_refresh("exercise_card_structure"' not in b
def test_superset_refresh_retained():
 s=(ROOT/'main.py').read_text(); assert 'superset_assignment_changed' in s and 'Superset group created.' in s
def test_release_docs_present():
 for x in ('docs/releases/RELEASE_1.93.2.md','docs/testing/ANDROID_SMOKE_TEST_1.93.2.md','docs/validation/VALIDATION_1.93.2.md'): assert (ROOT/x).exists()
