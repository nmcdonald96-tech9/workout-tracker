from datetime import datetime, timedelta
from pathlib import Path
from services.workout_service import WorkoutStateService, workout_progress
ROOT=Path(__file__).resolve().parents[1]
def test_active_position_and_action_contract():
 rows=[{"done":True,"rpe":"8"},{"done":False,"rpe":""}]
 assert WorkoutStateService.active_set_position(rows)==(2,2)
 assert WorkoutStateService.next_action(rows)=="Enter RPE, then complete Set 2."
 rows[1]["rpe"]="8.5"; assert WorkoutStateService.next_action(rows)=="Complete Set 2 to continue."
 rows[1]["done"]=True; assert WorkoutStateService.next_action(rows)=="All sets complete. Log the exercise."
 assert WorkoutStateService.next_action(rows,"Completed")=="Exercise logged. Continue to the next movement."
def test_elapsed_and_basic_helpers():
 now=datetime(2026,9,24,12); assert WorkoutStateService.elapsed_since(now-timedelta(seconds=75),now)==75
 values=[{"done":True},{"done":False}]
 assert WorkoutStateService.first_incomplete_set(values)==1 and WorkoutStateService.completed_count(values)==1 and WorkoutStateService.exercise_started(values)
def test_workout_progress_contract():
 rows=[(1,"Bench",100,10,"Completed","Compound","Chest",1),(2,"Flye",25,12,"Skipped","Isolation","Chest",2),(3,"Row",80,10,"Pending","Compound","Back",3)]
 drafts={1:[{"done":True},{"done":True}],2:[{"done":False}],3:[{"done":True}]}
 assert workout_progress(rows,drafts)=={"completed_exercises":1,"skipped_exercises":1,"total_exercises":3,"completed_sets":3,"total_sets":4,"completed_categories":1,"total_categories":2}
def test_release_contract_and_no_duplicate_main_definitions():
 constants=(ROOT/"constants.py").read_text(); main=(ROOT/"main.py").read_text()
 assert 'APP_VERSION = "1.92.2"' in constants and 'DATABASE_SCHEMA_VERSION = 20' in constants
 assert 'from services.workout_service import WorkoutStateService, workout_progress' in main
 assert 'class WorkoutStateService:' not in main and 'def workout_progress(' not in main
 assert (ROOT/'docs/releases/RELEASE_1.90.0.md').exists()