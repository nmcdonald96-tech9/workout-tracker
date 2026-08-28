def compatible_checkbox(ft, label, value=False, on_change=None):
    control=ft.Checkbox(label=label, value=value); control.on_change=on_change; return control

def safe_page_open(page, control):
    if hasattr(page, "open"): page.open(control)
    else:
        if control not in page.overlay: page.overlay.append(control)
        control.open=True; page.update()

def safe_page_close(page, control):
    if control is None: return
    try:
        control.open=False; page.update()
        if hasattr(page, "close"): page.close(control)
    except Exception: pass
