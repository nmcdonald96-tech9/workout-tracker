from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def block(start,end):
 s=(ROOT/'main.py').read_text();a=s.index(start);b=s.index(end,a);return s[a:b]
def test_mode_change_closes_dialog_before_deferred_refresh():
 b=block('    def open_display_mode(', '    async def maybe_open_first_setup_wizard')
 assert b.index('self.safe_close(dialog)') < b.index('self.apply_display_mode(')
 assert 'schedule_refresh=True' in b
 assert 'self.rebuild_entire_display()' not in b
def test_apply_mode_uses_coalesced_structural_refresh_not_inline_rebuild():
 b=block('    def apply_display_mode(', '    def open_display_mode(')
 assert 'request_structural_refresh("display_mode_changed",rebuild_navigation=True,remount_canvas=True)' in b
 assert 'self.rebuild_entire_display()' not in b
 assert 'display_mode_rebuild_scheduled' in b and 'display_mode_rebuild_coalesced' in b
def test_profile_settings_saves_mode_once_and_schedules_one_refresh():
 b=block('    def open_settings_dialog(', '    def trigger_delete_double_check(')
 assert b.count('apply_display_mode(new_display_mode,schedule_refresh=True,source="profile_settings")')==1
 assert "VALUES ('workout_focus_mode'" not in b
 assert "VALUES ('ui_density'" not in b
 assert 'self.rebuild_entire_display()' not in b
def test_structural_refresh_traces_display_mode_boundary():
 b=block('    def _apply_structural_refresh(', '    def request_structural_refresh(')
 assert 'display_mode_rebuild_started' in b and 'display_mode_rebuild_finished' in b
 assert 'display_mode_changed' in b
def test_portrait_fixes_remain():
 s=(ROOT/'main.py').read_text()
 for marker in ('ft.TextOverflow.ELLIPSIS','tooltip="Exercise actions"','View: {self.current_display_mode().title()} ▾','label="Display mode"','scroll="auto"'):
  assert marker in s
def test_weight_repaint_path_remains_direct_and_non_structural():
 b=block('    def refresh_weight_edit_feedback(', '    def make_blur_handler(')
 assert 'field.update()' in b
 assert 'reps_update_exception' in b
 assert 'request_structural_refresh' not in b
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.13"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
