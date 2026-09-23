class WorkoutStateService:
    @staticmethod
    def first_incomplete_set(rows): return next((i for i,v in enumerate(rows or []) if not v.get("done")),None)
    @staticmethod
    def completed_count(rows): return sum(1 for v in rows or [] if v.get("done"))
    @staticmethod
    def exercise_started(rows): return any(v.get("done") for v in rows or [])