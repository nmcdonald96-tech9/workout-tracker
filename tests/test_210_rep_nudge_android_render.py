from pathlib import Path
import flet as ft

SOURCE = Path("main.py").read_text(encoding="utf-8")


def test_rep_trigger_uses_clickable_container_not_icon_button():
    start = SOURCE.index("    def build_card(")
    end = SOURCE.index("    def _reopen_completed(", start)
    block = SOURCE[start:end]
    assert 'nudge_slot = ft.Container(' in block
    assert 'content=ft.Text("±", size=22, weight="bold", color="cyan200")' in block
    assert 'alignment=ft.Alignment(0, 0)' in block
    assert 'ink=True' in block
    assert 'nudge_slot = ft.IconButton(' not in block
    assert 'icon="exposure"' not in block


def test_flet_accepts_clickable_visible_content_container():
    trigger = ft.Container(
        content=ft.Text("±", size=22, weight="bold", color="cyan200"),
        width=48,
        height=48,
        alignment=ft.Alignment(0, 0),
        border_radius=7,
        ink=True,
        tooltip="Adjust active-set reps by 1",
        on_click=lambda event: None,
    )
    assert trigger.content.value == "±"
    assert trigger.width == 48 and trigger.height == 48
    assert callable(trigger.on_click)
