from pathlib import Path
from controllers.workout_view_controller import WorkoutPosition,WorkoutViewController
from controllers.workout_viewport_controller import ViewportAction,WorkoutViewportController
ROOT=Path(__file__).resolve().parents[1]
def test_viewport_intents_are_deterministic():
 c=WorkoutViewportController();c.record_scroll(412.5);x=c.preserve_current();assert x.action==ViewportAction.PRESERVE_OFFSET and x.offset==412.5
 consumed=c.consume();assert consumed.offset==412.5 and c.consume().action==ViewportAction.NONE
 c.navigate_to_key('exercise-42');assert c.consume().key=='exercise-42'
def test_viewport_intents_are_mutually_exclusive():
 c=WorkoutViewportController();c.record_scroll(100);c.preserve_current();c.navigate_to_key('exercise-9');x=c.consume();assert x.action==ViewportAction.SCROLL_TO_KEY and x.offset is None
 c.record_scroll(-10);assert c.current_offset==0.0
def test_workout_view_state_and_sorting():
 c=WorkoutViewController();p=WorkoutPosition(1,'2','Monday');c.focus_category(p,['Chest','Back'],'Back',22)
 assert c.is_collapsed(p,'Chest') and not c.is_collapsed(p,'Back') and c.active_session(p,'Back')==22
 pending=(22,'Row',0,0,'Pending','Compound','Back',2);complete=(23,'Pulldown',0,0,'Completed','Compound','Back',1)
 assert c.category_sort_key(p,'Back',[pending,complete],3)==(0,0,3)
def test_controllers_are_framework_and_persistence_neutral():
 for rel in ('controllers/workout_view_controller.py','controllers/workout_viewport_controller.py'):
  source=(ROOT/rel).read_text();assert 'import flet' not in source and 'from database' not in source and '.commit(' not in source
def test_main_composes_controllers_and_preserves_1952_card_path():
 s=(ROOT/'main.py').read_text();assert 'WorkoutViewController()' in s and 'WorkoutViewportController()' in s
 assert 'workout_viewport_controller.consume()' in s and 'category_sort_key(' in s
 assert 'replace_exercise_card_in_place(self)' in s and 'self.main_canvas.controls[index] = replacement' in s
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.98.4"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
