from exercise_catalog import CATALOG_VERSION,resolve_exercise_metadata,validate_exercise_values
def test_expanded_runtime_metadata():
 assert CATALOG_VERSION==5
 assert resolve_exercise_metadata("Push-Up")["equipment"]=="Bodyweight"
 assert resolve_exercise_metadata("Cable Crunch")["equipment"]=="Cable"
def test_smith_zero_bar():
 m=resolve_exercise_metadata("Smith Machine Shoulder Press (Seated)");assert m["plate_loaded"] and m["bar_weight"]==0
def test_boundaries():
 assert validate_exercise_values("Dumbbell Press (Flat)",100,10)==(100.0,10)
 for w,r in ((101,10),(20,0),(20,51)):
  try:validate_exercise_values("Dumbbell Press (Flat)",w,r)
  except ValueError:pass
  else:raise AssertionError((w,r))