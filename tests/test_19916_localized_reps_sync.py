from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=(ROOT/'main.py').read_text()
def method(a,b):
 x=S.index(f'    def {a}(');y=S.index(f'    def {b}(',x);return S[x:y]

def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.16"' in c;assert 'DATABASE_SCHEMA_VERSION = 20' in c;assert 'ENTITLEMENT_TEST_CONTROLS = False' in c

def test_blank_reps_blur_is_model_only_and_never_remounts_canvas():
 b=method('make_blur_handler','build_card');r=b[b.index('if key_type == "r":'):b.index('if key_type == "rpe":')]
 assert 'clear_override(set_data, "r", current_target)' in r and 'self.autosave_pending_sets()' in r
 assert 'e.control.value =' not in r and 'e.control.update()' not in r
 assert 'request_structural_refresh' not in r and 'remount_canvas' not in r
 assert 'self._pending_reps_visual_refresh = True' in r

def test_rpe_blur_defers_only_local_card_refresh_after_saving():
 b=method('make_blur_handler','build_card')
 assert b.index('self.autosave_pending_sets()') < b.index('request_local_card_refresh("reps_restore_after_rpe")')

def test_local_refresh_replaces_one_card_and_coalesces():
 b=method('request_local_card_refresh','open_swap_dialog')
 assert 'await asyncio.sleep(0)' in b and '_local_card_refresh_scheduled' in b
 assert 'replace_exercise_card_in_place(self)' in b
 assert 'request_structural_refresh' not in b and 'remount_main_canvas' not in b

def test_weight_feedback_keeps_fast_path_and_local_fallback():
 b=method('refresh_weight_edit_feedback','commit_weight_edit')
 assert 'field.value = str(draft.get("r", ""))' in b and 'field.update()' in b
 assert 'except (RuntimeError, IndexError)' in b
 assert 'request_local_card_refresh("weight_edit_feedback")' in b
 assert 'request_structural_refresh' not in b and 'remount_canvas=True' not in b

def test_in_place_replacement_preserves_listview_identity():
 b=method('replace_exercise_card_in_place','remount_main_canvas')
 assert 'self.main_canvas.controls[index] = replacement' in b and 'self.main_canvas.update()' in b
 assert 'self.main_canvas =' not in b and 'scroll_to(' not in b

def test_workflows_target_hotfix():
 for n in ('main-android-apk-authentic-packaging.yml','main-android-apk-aab-authentic-packaging.yml'):
  t=(ROOT/'.github/workflows'/n).read_text();assert 'test "$APP_VERSION" = "1.99.16"' in t;assert 'flutter-version: 3.44.8' in t
