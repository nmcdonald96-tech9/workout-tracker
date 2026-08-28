from app.state import WorkoutState
from app.router import ViewRouter
class ApplicationFoundation:
    def __init__(self, refresh_callback=None):
        self.state=WorkoutState(); self.router=ViewRouter(self.state, refresh_callback)
    def sync(self, controller): return self.state.sync_from_controller(controller)
