from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def method(name, next_name):
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index(f"    def {name}(")
    end = source.index(f"    def {next_name}(", start)
    return source[start:end]

def test_reps_field_has_no_numeric_ghost_hint():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index('            r_f = ft.TextField(')
    end = source.index('            r_f.on_change', start)
    block = source[start:end]
    assert 'hint_text=""' in block
    assert 'hint_text=str(r_hint)' not in block

def test_blank_reps_restore_authoritative_target_on_blur():
    block = method("make_blur_handler", "build_card")
    assert 'if key_type == "r":' in block
    assert 'if raw_reps == "" and set_idx < len(self.set_targets):' in block
    assert 'clear_override(set_data, "r", current_target)' in block
    assert 'e.control.value = str(set_data.get("r", ""))' not in block
    assert 'self._pending_reps_visual_refresh = True' in block
    assert 'self.autosave_pending_sets()' in block

def test_nonblank_reps_are_not_replaced_by_blur():
    block = method("make_blur_handler", "build_card")
    restore = block[block.index('if key_type == "r":'):block.index('if key_type == "rpe":')]
    assert 'raw_reps == ""' in restore
    assert 'apply_weight_derived_reps' not in restore

def test_restore_is_traced_without_exposing_values():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'reps_restore_target_applied' in source
    assert 'reps_restore_update_exception' not in source
    assert 'reps_restore_target_applied' in source

def test_startup_deduplication_and_weight_logic_remain_active():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'startup_billing_rebuild_coalesced' in source
    assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in source
    assert 'self.set_targets[set_idx]["r"] = new_target_r' not in source

def test_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "2.0.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
