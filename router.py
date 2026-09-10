class ViewRouter:
    VALID_VIEWS = {"workout", "history", "generator", "summary", "meso_report", "strength_standards", "dictionary", "settings"}
    def __init__(self, state, refresh_callback=None): self.state=state; self.refresh_callback=refresh_callback
    def show(self, view_name):
        if view_name not in self.VALID_VIEWS: raise ValueError(f"Unknown view: {view_name}")
        self.state.view_mode=view_name
        if self.refresh_callback: self.refresh_callback()
        return view_name
