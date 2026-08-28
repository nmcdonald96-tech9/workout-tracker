class ViewRouter:
    VALID_VIEWS={"workout","history","generator","summary","meso_report","strength_standards","dictionary","settings"}
    def __init__(self,state,refresh=None): self.state=state; self.refresh=refresh
    def show(self,name):
        if name not in self.VALID_VIEWS: raise ValueError(name)
        self.state.view_mode=name
        if self.refresh: self.refresh()
        return name
