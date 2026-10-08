from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def method_block(name):
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    match = re.search(
        rf"^    def {re.escape(name)}\(.*?(?=^    def |^class |\Z)",
        source,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"method not found: {name}"
    return match.group(0)


def structure_editor_block():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index("    def open_structure_editor(")
    end = source.index("    def restore_future_schedule(", start)
    return source[start:end]


def test_card_replacement_keeps_main_list_mounted():
    block = method_block("replace_exercise_card_in_place")

    assert "self.main_canvas.controls[index] = replacement" in block
    assert "self.main_canvas.update()" in block

    assert "remount_main_canvas" not in block
    assert "rebuild_entire_display" not in block
    assert "scroll_to_workout_key" not in block
    assert "pending_scroll_key" not in block


def test_set_structure_uses_parent_replacement_only():
    block = method_block("request_set_structure_refresh")

    assert "replace_exercise_card_in_place(self)" in block

    assert "self.build_card()" not in block
    assert "self.update()" not in block
    assert "request_structural_refresh" not in block
    assert "preserve_workout_viewport" not in block
    assert "pending_scroll_key" not in block


def test_add_and_remove_call_set_structure_refresh():
    add_block = method_block("on_add_set")
    remove_block = method_block("on_remove_set")

    assert 'request_set_structure_refresh("add_set")' in add_block
    assert 'request_set_structure_refresh("remove_set")' in remove_block

    assert "advance_group_flow" not in add_block
    assert "advance_group_flow" not in remove_block


def test_superset_assignment_requests_immediate_refresh():
    block = structure_editor_block()

    assert "superset_assignment_changed" in block
    assert "Superset group created." in block
    assert "Superset group removed." in block
    assert "request_structural_refresh(" in block


def test_resolver_compatibility_retained():
    from services.superset_execution_service import (
        resolve_next_group_step,
        resolve_post_set_action,
    )

    assert callable(resolve_next_group_step)
    assert callable(resolve_post_set_action)


def test_compact_skipped_card_retained():
    source = (ROOT / "main.py").read_text(encoding="utf-8")

    assert "ExerciseCardMode.SKIPPED_COMPACT" in source
    assert 'ft.Text("SKIPPED"' in source
    assert 'ft.TextButton("Unskip"' in source


def test_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")

    assert 'APP_VERSION = "2.0.0"' in constants
    assert 'DATABASE_SCHEMA_VERSION = 20' in constants
