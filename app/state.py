from dataclasses import dataclass, field
@dataclass
class WorkoutState:
    current_meso:int=1; current_week:str="1"; current_day:str="Monday"; view_mode:str="workout"
    sets:dict=field(default_factory=dict); active_exercise_by_category:dict=field(default_factory=dict); collapsed_categories:dict=field(default_factory=dict)
    pending_scroll_key:object=None
    def position(self): return self.current_meso,self.current_week,self.current_day
    def set_position(self,meso,week,day): self.current_meso=int(meso); self.current_week=str(week); self.current_day=str(day)
