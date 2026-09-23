from app.state import WorkoutState
from app.router import ViewRouter
from services.workout_service import WorkoutStateService
def test_state_sync_and_router():
 class C: current_meso=4; current_week="2"; current_day="Thursday"; view_mode="workout"; sets={}; active_exercise_by_category={}; collapsed_categories={}; pending_scroll_key=None
 state=WorkoutState().sync_from_controller(C()); assert state.position()==(4,"2","Thursday"); assert ViewRouter(state).show("history")=="history"
def test_workout_helpers():
 rows=[{"done":True},{"done":False}]; assert WorkoutStateService.first_incomplete_set(rows)==1; assert WorkoutStateService.completed_count(rows)==1