from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def block(start,end):
 s=(ROOT/'main.py').read_text();a=s.index(start);b=s.index(end,a);return s[a:b]

def test_exercise_header_reserves_action_lane_and_ellipsizes_title():
 s=(ROOT/'main.py').read_text();b=block('        exercise_title = ft.Text(', '        completed_times = [')
 assert 'max_lines=2' in b and 'ft.TextOverflow.ELLIPSIS' in b
 assert 'tooltip=database.exercise_display_name(self.exercise)' in b
 assert 'width=44' in b and 'tooltip="Exercise actions"' in b
 assert 'wrap=True' in b

def test_main_workout_screen_has_visible_current_display_mode():
 s=(ROOT/'main.py').read_text()
 assert 'View: {self.current_display_mode().title()} ▾' in s
 assert 'tooltip="Change workout display mode"' in s
 assert '[self.nav_collapse_button, self.display_mode_button]' in s

def test_display_mode_has_one_authoritative_mapping():
 b=block('    def apply_display_mode(', '    async def maybe_open_first_setup_wizard')
 for mode in ('STANDARD','FOCUS','DETAILED'):assert mode in b
 assert "save_setting('workout_focus_mode'" in b and "save_setting('ui_density'" in b
 assert 'display_mode_button.content.value' in b

def test_profile_settings_uses_scrollable_unified_selector():
 b=block('    def open_settings_dialog(', '    def trigger_delete_double_check(')
 assert 'self.display_mode_dropdown = ft.Dropdown(' in b
 assert 'label="Display mode"' in b
 assert 'ft.ResponsiveRow' in b
 assert 'scroll="auto"' in b
 assert 'float(getattr(self.page, "height", 720) or 720) - 180' in b
 assert 'ft.Container(height=32)' in b
 assert 'self.focus_mode_switch' not in b and 'self.density_dropdown' not in b

def test_frozen_contracts_remain():
 s=(ROOT/'main.py').read_text()
 for marker in ('apply_weight_derived_reps','reps_restore_target_applied','startup_billing_rebuild_coalesced','Entitlement acceptance profile: 1.99.9','Backup recovery acceptance profile: 1.99.10'):
  assert marker in s

def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.99.13"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
