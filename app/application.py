from app.state import WorkoutState
from app.router import ViewRouter
class ApplicationFoundation:
    def __init__(self,refresh=None): self.state=WorkoutState(); self.router=ViewRouter(self.state,refresh)
