from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def method_block(name, *, next_name):
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    start = source.index(f"    def {name}(")
    end = source.index(f"    def {next_name}(", start)
    return source[start:end]


def test_structural_refresh_diagnostics_use_real_coordinator_attribute():
    block = method_block(
        "structural_refresh_status",
        next_name="open_diagnostics_dialog",
    )

    assert '"_structural_refresh_coordinator"' in block
    assert 'return "idle"' in block
    assert "coordinator.running" in block
    assert "coordinator.scheduled" in block
    assert "coordinator.pending" in block
    assert "self.structural_refresh." not in block


def test_diagnostics_dialog_uses_safe_status_helper():
    source = (ROOT / "main.py").read_text(encoding="utf-8")

    assert "self.structural_refresh_status()" in source
    assert "self.structural_refresh.running" not in source
    assert "self.structural_refresh.scheduled" not in source
    assert "self.structural_refresh.pending" not in source


def test_uninitialized_coordinator_reports_idle_by_contract():
    block = method_block(
        "structural_refresh_status",
        next_name="open_diagnostics_dialog",
    )

    assert "getattr(" in block
    assert '"_structural_refresh_coordinator"' in block
    assert "if coordinator is None:" in block
    assert 'return "idle"' in block


def test_release_contract():
    constants = (ROOT / "constants.py").read_text(encoding="utf-8")

    assert 'APP_VERSION = "1.98.1"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants