from dataclasses import dataclass, field

@dataclass
class WorkoutState:
    current_meso: int = 1
    current_week: str = "1"
    current_day: str = "Monday"
    view_mode: str = "workout"
    sets: dict = field(default_factory=dict)
    active_exercise_by_category: dict = field(default_factory=dict)
    collapsed_categories: dict = field(default_factory=dict)
    pending_scroll_key: object = None

    def sync_from_controller(self, controller):
        for name in ("current_meso", "current_week", "current_day", "view_mode", "sets", "active_exercise_by_category", "collapsed_categories", "pending_scroll_key"):
            if hasattr(controller, name): setattr(self, name, getattr(controller, name))
        return self

    def position(self):
        return self.current_meso, self.current_week, self.current_day
