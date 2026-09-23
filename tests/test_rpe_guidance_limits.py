from exercise_catalog import validate_exercise_values

def test_limits_accept_valid_and_reject_invalid():
 assert validate_exercise_values("Push-Up",0,10)==(0.0,10)
 for weight,reps in ((-1,10),(0,0),(0,51)):
  try: validate_exercise_values("Push-Up",weight,reps)
  except ValueError: pass
  else: raise AssertionError((weight,reps))

def test_rpe_copy_is_present():
 text=open("main.py",encoding="utf-8").read()
 assert "How RPE Works" in text and "rpe_guide_seen" in text
 assert "REPS AUTO-ADJUSTED FROM WEIGHT" in text