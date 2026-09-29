from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def method(name,next_name):
 s=(ROOT/'main.py').read_text();a=s.index(f'    def {name}(');b=s.index(f'    def {next_name}(',a);return s[a:b]
def test_replacement_lookup_uses_db_id_and_revisioned_key():
 b=method('replace_exercise_card_in_place','remount_main_canvas')
 assert 'getattr(control, "db_id", None) == session_id' in b
 assert 'exercise_card_revisions.get(session_id, 0)) + 1' in b
 assert 'replacement.key = self.exercise_card_render_key(session_id)' in b
 assert 'self.main_canvas.controls[index] = replacement' in b
def test_initial_render_uses_current_revision_key():
 s=(ROOT/'main.py').read_text();assert 'card.key = self.exercise_card_render_key(db_id)' in s
def test_stable_exercise_anchor_resolves_to_current_render_key():
 b=method('resolve_workout_render_key','replace_exercise_card_in_place')
 assert '"-render-" not in text' in b
 assert 'return self.exercise_card_render_key(int(raw_id))' in b
 scroll=method('scroll_to_workout_key','jump_to_category')
 assert 'key = self.resolve_workout_render_key(key)' in scroll
def test_weight_and_completion_use_forced_replacement():
 assert 'replace_exercise_card_in_place(self)' in method('refresh_weight_edit_feedback','make_blur_handler')
 done=method('make_set_done_handler','make_live_updater')
 assert 'self.app.replace_exercise_card_in_place(self)' in done
def test_listview_remains_mounted_for_local_replacement():
 b=method('replace_exercise_card_in_place','remount_main_canvas')
 assert 'remount_main_canvas' not in b and 'rebuild_entire_display' not in b
 assert 'self.main_canvas.update()' in b
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.3"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
