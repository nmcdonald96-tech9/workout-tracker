from services.progression_service import progression_clarity,simulate_progression,invalidate_progression_settings_cache,get_effective_progression_settings,classify_set_progression,calculate_set_specific_progression
from services.workout_service import WorkoutStateService,workout_progress
def test_contract(): assert callable(progression_clarity) and callable(workout_progress) and WorkoutStateService.active_set_position([{"done":False}])==(1,1)
