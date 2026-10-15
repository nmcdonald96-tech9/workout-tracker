from pathlib import Path
import flet as ft

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def build_card():
    return method("build_card", "_reopen_completed")


def test_active_row_uses_direct_stacked_plus_minus_controls():
    block = build_card()
    assert 'content=ft.Text("+", size=16, weight="bold", color="cyan100")' in block
    assert 'content=ft.Text("−", size=18, weight="bold", color="cyan100")' in block
    assert 'self.nudge_active_set_reps(set_index, 1)' in block
    assert 'self.nudge_active_set_reps(set_index, -1)' in block
    assert "open_rep_nudge_menu" not in SOURCE


def test_stacked_controls_fit_one_reserved_row_slot():
    block = build_card()
    assert 'nudge_slot = ft.Container(width=44, height=48)' in block
    assert block.count("height=24") == 2
    assert '], spacing=0, tight=True)' in block
    assert '[set_indicator, w_f, r_f, nudge_slot, rpe_f, complete_set_btn]' in block


def test_bold_divider_and_outer_border_are_present():
    block = build_card()
    assert 'border=ft.Border(top=ft.BorderSide(2, "cyan200"))' in block
    assert 'top=ft.BorderSide(1, "cyan700")' in block
    assert 'clip_behavior=ft.ClipBehavior.ANTI_ALIAS' in block


def test_popup_lifecycle_is_completely_removed():
    assert 'title=ft.Text("Adjust reps"' not in SOURCE
    assert "flush_pending_reps_after_nudge_dialog" not in SOURCE
    assert "weight_prepared" not in method("nudge_active_set_reps", "request_local_card_refresh")


def test_flet_constructs_stacked_clickable_controls():
    control = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Text("+"), height=24, ink=True, on_click=lambda e: None),
            ft.Container(
                content=ft.Text("−"), height=24,
                border=ft.Border(top=ft.BorderSide(2, "cyan200")),
                ink=True, on_click=lambda e: None,
            ),
        ], spacing=0, tight=True),
        width=44, height=48,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    assert control.width == 44 and control.height == 48
    assert len(control.content.controls) == 2
    assert all(callable(item.on_click) for item in control.content.controls)


def test_direct_nudge_prepares_weight_then_applies_one_delta():
    block = method("nudge_active_set_reps", "request_local_card_refresh")
    assert "drafts = self.prepare_rep_nudge_weight(set_idx)" in block
    assert block.index("drafts = self.prepare_rep_nudge_weight(set_idx)") < block.index("updated = nudge_pending_reps(")
    assert 'self.request_local_card_refresh("rep_nudge_applied")' in block
