from pathlib import Path
from services.accessibility_service import classify_layout, acceptance_matrix, MIN_TOUCH_TARGET_DP
ROOT=Path(__file__).resolve().parents[1]

def test_layout_classification_matrix():
 assert classify_layout(320,700).width_class=='narrow'
 assert classify_layout(411,891).orientation=='portrait'
 assert classify_layout(891,411).orientation=='landscape'
 assert classify_layout(800,1280).width_class=='tablet'
 assert classify_layout(360,600).height_class=='short'

def test_acceptance_matrix_covers_release_gate():
 matrix=' '.join(acceptance_matrix()).lower()
 for marker in ('text scaling','portrait','landscape','narrow','tablet','touch','color','scrollable','keyboard','safe-area','first setup','backup'):
  assert marker in matrix
 assert MIN_TOUCH_TARGET_DP==48

def test_privacy_safe_diagnostics_and_checklist_present():
 main=(ROOT/'main.py').read_text()
 assert 'Accessibility and layout acceptance profile: 1.99.11' in main
 assert 'Accessibility & Layout Acceptance' in main
 assert 'viewport class only; no device identifier' in main
 assert 'Copy Checklist' in main

def test_shell_and_dialog_responsiveness_contracts_remain():
 main=(ROOT/'main.py').read_text()
 assert 'ft.SafeArea' in main
 assert 'scroll="auto"' in main
 assert 'ui_density' in main and 'workout_focus_mode' in main
 assert 'Standard, Focus, Detailed' in main

def test_icon_acceptance_actions_have_text_and_tooltips():
 main=(ROOT/'main.py').read_text()
 assert 'tooltip="Open accessibility and responsive-layout checklist"' in main
 assert 'tooltip="Copy accessibility checklist"' in main
 assert 'tooltip="Close accessibility checklist"' in main

def test_previous_android_verified_gates_promoted():
 main=(ROOT/'main.py').read_text()
 assert 'trial expiration and limited mode: Android verified 1.99.9' in main
 assert 'backup and restore matrix: Android verified 1.99.10' in main

def test_frozen_product_contracts_remain():
 main=(ROOT/'main.py').read_text()
 for marker in ('apply_weight_derived_reps','reps_restore_target_applied','startup_billing_rebuild_coalesced','Entitlement acceptance profile: 1.99.9','Backup recovery acceptance profile: 1.99.10'):
  assert marker in main

def test_release_contract():
 c=(ROOT/'constants.py').read_text(); assert 'APP_VERSION = "1.99.11"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
