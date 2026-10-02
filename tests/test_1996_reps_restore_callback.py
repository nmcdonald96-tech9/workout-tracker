from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def blur_block():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index("    def make_blur_handler(")
    end = source.index("    def build_card(", start)
    return source[start:end]


def test_restore_uses_actual_event_parameter():
    block = blur_block()
    assert "def blur_handler(e):" in block
    assert 'e.control.value = str(set_data.get("r", ""))' in block
    assert "e.control.update()" in block
    assert "control=e.control" in block
    assert "ev.control" not in block


def test_target_restore_and_blank_hint_remain():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    block = blur_block()
    assert 'clear_override(set_data, "r", current_target)' in block
    assert 'hint_text=""' in source
    assert "startup_billing_rebuild_coalesced" in source


def test_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "1.99.10"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants
