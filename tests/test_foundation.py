from app.state import WorkoutState
from app.router import ViewRouter
from components.exercise_card import active_set_index
def test_state_router_and_card():
 s=WorkoutState(); assert ViewRouter(s).show('dictionary')=='dictionary'; assert active_set_index([{'done':True},{'done':False}])==1
