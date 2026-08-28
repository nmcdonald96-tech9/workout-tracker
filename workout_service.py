from datetime import datetime
class WorkoutStateService:
 @staticmethod
 def first_incomplete_set(rows): return next((i for i,x in enumerate(rows or []) if not x.get("done")),None)
 @staticmethod
 def active_set_position(rows):
  rows=rows or [];i=WorkoutStateService.first_incomplete_set(rows);return (0,0) if not rows else ((i+1) if i is not None else len(rows),len(rows))
 @staticmethod
 def next_action(rows,exercise_status="Pending"):
  if exercise_status=="Completed":return "Exercise logged. Continue to the next movement."
  i=WorkoutStateService.first_incomplete_set(rows)
  if i is None:return "All sets complete. Log the exercise."
  return f"Enter RPE, then complete Set {i+1}." if not str(rows[i].get("rpe","")).strip() else f"Complete Set {i+1} to continue."
 @staticmethod
 def elapsed_since(ts,now=None):
  try:return max(0,int(((now or datetime.now())-datetime.fromisoformat(str(ts))).total_seconds())) if ts else None
  except:return None
def workout_progress(rows,drafts):
 rows=rows or [];cats={r[6] for r in rows if r[6]};done={c for c in cats if all(r[4]!="Pending" for r in rows if r[6]==c)};sets=[x for r in rows for x in drafts.get(r[0],[])]
 return {"completed_exercises":sum(r[4]=="Completed" for r in rows),"skipped_exercises":sum(r[4]=="Skipped" for r in rows),"total_exercises":len(rows),"completed_sets":sum(bool(x.get("done")) for x in sets),"total_sets":len(sets),"completed_categories":len(done),"total_categories":len(cats)}
