from pathlib import Path


SOURCE = Path("main.py").read_text(encoding="utf-8")


def readiness_display_block():
    start = SOURCE.index("        if self.set_progression_diagnostics:\n")
    end = SOURCE.index(
        '        if self.mov_type == "Compound" '
        'and self.app.current_week != "Deload" '
        'and self.status == STATUS_PENDING:\n',
        start,
    )
    return SOURCE[start:end]


def test_active_readiness_reduction_displays_paused():
    block = readiness_display_block()

    assert 'decision_label = "Paused"' in block
    assert 'self.context.get("readiness_logged")' in block
    assert "self.status == STATUS_PENDING" in block
    assert 'self.app.current_week != "Deload"' in block
    assert "self.normal_set_targets[0] != self.set_targets[0]" in block


def test_active_readiness_reduction_explains_normal_target():
    block = readiness_display_block()

    assert (
        '"Normal target preserved; resumes when readiness clears."'
        in block
    )


def test_non_readiness_progression_labels_are_preserved():
    block = readiness_display_block()

    assert '"progress": "Advanced"' in block
    assert '"hold": "Held"' in block
    assert '"reduce": "Reduced"' in block
    assert '"resume_normal": "Resumed normal"' in block


def test_readiness_display_block_does_not_modify_progression():
    block = readiness_display_block()

    assert "calculate_progression(" not in block
    assert "calculate_set_specific_progression(" not in block
