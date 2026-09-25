from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def method_block(name, next_name):
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index(f"    def {name}(")
    end = source.index(f"    def {next_name}(", start)
    return source[start:end]


def test_jump_uses_tuple_scoped_category_keys_and_deferred_refresh():
    block = method_block("jump_to_category", "advance_group_flow")
    assert "jump_to_category_state(" not in block
    assert "self.collapsed_categories[self.category_key(category)]" in block
    assert "self.collapsed_categories[self.category_key(selected)] = False" in block
    assert "self.pending_scroll_key = category_anchor_key(selected)" in block
    assert 'self.request_structural_refresh(' in block
    assert '"category_jump"' in block
    assert "remount_canvas=True" in block
    assert "self.rebuild_entire_display()" not in block


def test_add_exercise_rebuilds_navigation_once_through_coordinator():
    block = method_block("save_wizard_addition", "rebuild_navigation_headers")
    assert "INSERT INTO workout_sessions" in block
    assert "self.pending_scroll_key = category_anchor_key(cat)" in block
    assert '"add_exercise"' in block
    assert "rebuild_navigation=True" in block
    assert "remount_canvas=True" in block
    assert "self.rebuild_navigation_headers()" not in block
    assert "self.rebuild_entire_display()" not in block


def test_post_mount_scroll_contract_is_retained():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    rebuild = source[source.index("    def rebuild_entire_display("):]
    update = rebuild.index("self.page.update()")
    pending = rebuild.index("if self.pending_scroll_key:")
    scroll = rebuild.index("self.scroll_to_workout_key(focus_key)")
    assert update < pending < scroll


def test_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.92.3"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants
    assert (ROOT / "docs/releases/RELEASE_1.92.3.md").exists()
    assert (ROOT / "docs/testing/ANDROID_SMOKE_TEST_1.92.3.md").exists()
    assert (ROOT / "docs/validation/VALIDATION_1.92.3.md").exists()
