from constants import COMPOUND_JUMP_STANDARD,ISOLATION_JUMP_STANDARD
_CACHE={}
def invalidate_progression_settings_cache(exercise_name=None):
 if exercise_name is None:_CACHE.clear()
 else:
  for k in list(_CACHE):
   if k[0]==exercise_name:_CACHE.pop(k,None)
def get_effective_progression_settings(exercise_name,movement_type,equipment_type,age=43,profile=0):
 k=(exercise_name,movement_type,equipment_type,age,profile)
 if k in _CACHE:return dict(_CACHE[k])
 effective=profile or (3 if age<35 else 2 if age<45 else 1);v={"progression_step":float(COMPOUND_JUMP_STANDARD if movement_type=="Compound" else ISOLATION_JUMP_STANDARD),"reduction_steps":1,"rep_ceiling":12 if effective==3 else 15 if effective==2 else 18,"reduction_threshold":.70,"max_progress_rpe":9.5,"max_progression_weight":None}
 try:
  from database import get_db
  with get_db() as c:r=c.execute("SELECT progression_mode,progression_step,reduction_steps,rep_ceiling,reduction_threshold,max_progress_rpe,max_progression_weight FROM exercise_dict WHERE name=?",(exercise_name,)).fetchone()
  if r and r[0]=="custom":
   for n,x in zip(("progression_step","reduction_steps","rep_ceiling","reduction_threshold","max_progress_rpe","max_progression_weight"),r[1:]):
    if x is not None:v[n]=x
 except:pass
 _CACHE[k]=dict(v);return v
def classify_set_progression(aw,ar,rpe,tw,tr,nw,nr,s):
 ar=int(ar or 0);tr=max(1,int(tr or 10));eff=float(rpe if rpe is not None else 8)
 if float(tw or 0)<float(nw if nw is not None else tw) or tr<int(nr if nr is not None else tr):return {"decision":"resume_normal","reason_code":"READINESS_RECOVERY","reason":"Temporary readiness reduction completed; resume the normal trajectory."}
 if ar/tr<float(s.get("reduction_threshold",.7)):return {"decision":"reduce","reason_code":"SIGNIFICANT_MISS","reason":"Performance was below the reduction threshold."}
 if eff>float(s.get("max_progress_rpe",9.5)):return {"decision":"hold","reason_code":"RPE_CEILING","reason":"Effort exceeded the progression RPE ceiling."}
 if ar>=tr:return {"decision":"progress","reason_code":"TARGET_MET","reason":"Target reps were completed within the progression RPE ceiling."}
 return {"decision":"hold","reason_code":"BUILD_REPS","reason":"Keep the load and continue building reps."}
def _step(w,eq,step,d=1):
 if eq=="Dumbbell":
  from database import get_next_dumbbell,get_prev_dumbbell
  return get_next_dumbbell(w) if d>0 else get_prev_dumbbell(w)
 return max(0,float(w)+float(step)*d)
def calculate_set_specific_progression(rows,dw,dr,movement_type,readiness_score=15,joint_score=5,equipment_type="Barbell",is_bodyweight=False,bodyweight=0,age=43,profile=0,exercise_name=None):
 s=get_effective_progression_settings(exercise_name,movement_type,equipment_type,age,profile);out=[];diag=[]
 for i,row in enumerate(rows or [(dw,dr,8,dw,dr,dw,dr)]):
  w=float(row[0] if row[0] is not None else dw);reps=int(row[1] if row[1] is not None else dr);eff=float(row[2] if len(row)>2 and row[2] is not None else 8);tw=float(row[3] if len(row)>3 and row[3] is not None else dw);tr=int(row[4] if len(row)>4 and row[4] is not None else dr);nw=float(row[5] if len(row)>5 and row[5] is not None else tw);nr=int(row[6] if len(row)>6 and row[6] is not None else tr);res=classify_set_progression(w,reps,eff,tw,tr,nw,nr,s);dec=res["decision"];nextw=w;nextr=tr
  if dec=="reduce" and not is_bodyweight:
   for _ in range(int(s["reduction_steps"])):nextw=_step(nextw,equipment_type,s["progression_step"],-1)
  elif dec=="progress":
   if equipment_type=="Dumbbell" or is_bodyweight:
    if reps>=int(s["rep_ceiling"]):nextw=w if is_bodyweight else _step(w,equipment_type,s["progression_step"]);nextr=max(1,int(dr or 10))
    else:nextr=reps+(2 if eff<=8 else 1)
   else:nextw=_step(w,equipment_type,s["progression_step"])
  elif dec=="resume_normal":nextw=nw;nextr=nr
  cap=s.get("max_progression_weight")
  if cap is not None and nextw>=float(cap):nextw=min(nextw,float(cap));nextr=max(nextr,reps+1 if dec=="progress" and reps<int(s["rep_ceiling"]) else reps);res={"decision":"progress" if nextr>reps else "hold","reason_code":"LOAD_CEILING_REACHED","reason":f"Load held at {float(cap):g} lb; rep progression remains available."}
  out.append({"w":nextw,"r":max(1,int(nextr))});diag.append({"set_number":i+1,"next_weight":nextw,"next_reps":max(1,int(nextr)),**res})
 return out,diag
def progression_clarity(s,cw,cr,nw,nr,reason_code=None):
 cw=float(cw or 0);nw=float(nw or 0);cr=int(cr or 0);nr=int(nr or 0);cap=s.get("max_progression_weight");return {"load":f"{'Load held' if nw==cw else 'Load increases' if nw>cw else 'Load reduces'}: {nw:g} lb","reps":f"{'Reps held' if nr==cr else 'Reps increase' if nr>cr else 'Reps reset'}: {nr}","at_cap":cap is not None and nw>=float(cap),"reason_code":reason_code}
def simulate_progression(s,w,r,equipment_type="Barbell"):
 w=float(w or 0);r=int(r or 0);ceiling=int(s["rep_ceiling"])
 if r<ceiling:return {"next_weight":w,"next_reps":r+1,"summary":f"Build reps: {w:g} x {r+1}"}
 n=_step(w,equipment_type,s["progression_step"]);cap=s.get("max_progression_weight")
 if cap is not None and n>float(cap):return {"next_weight":float(cap),"next_reps":ceiling,"summary":f"Load cap: hold {float(cap):g} lb and maintain up to {ceiling} reps"}
 return {"next_weight":n,"next_reps":8,"summary":f"Graduate load: {n:g} lb, reps reset for the next climb"}
