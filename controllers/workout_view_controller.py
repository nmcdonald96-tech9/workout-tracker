"""Framework-neutral workout view state coordination."""
from dataclasses import dataclass
@dataclass(frozen=True)
class WorkoutPosition:
    meso:int
    week:str
    day:str
class WorkoutViewController:
    def __init__(self,collapsed=None,active=None):
        self.collapsed=collapsed if collapsed is not None else {}
        self.active=active if active is not None else {}
    @staticmethod
    def category_key(position,category):
        return (position.meso,position.week,position.day,category)
    def is_collapsed(self,position,category):
        return bool(self.collapsed.get(self.category_key(position,category),False))
    def set_collapsed(self,position,category,value):
        self.collapsed[self.category_key(position,category)]=bool(value)
    def active_session(self,position,category):
        return self.active.get(self.category_key(position,category))
    def set_active(self,position,category,session_id):
        self.active[self.category_key(position,category)]=session_id
    def focus_category(self,position,categories,selected,session_id=None):
        for category in categories:
            if category:self.set_collapsed(position,category,category!=selected)
        self.set_collapsed(position,selected,False)
        if session_id is not None:self.set_active(position,selected,session_id)
    def category_sort_key(self,position,category,rows,original_index):
        active_id=self.active_session(position,category)
        pending=[row for row in rows if row[4]=="Pending"]
        has_active=any(row[0]==active_id for row in pending)
        return (0 if has_active else 1,1 if not pending else 0,original_index)

    def diagnostics(self,position):
        prefix=(position.meso,position.week,position.day)
        return {
            "position":f"M{position.meso} W{position.week} {position.day}",
            "active_categories":sum(1 for key,value in self.active.items() if key[:3]==prefix and value is not None),
            "collapsed_categories":sum(1 for key,value in self.collapsed.items() if key[:3]==prefix and value),
        }
