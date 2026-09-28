"""Framework-neutral post-set and superset execution routing."""
from dataclasses import dataclass
from enum import Enum
class SupersetExecutionAction(str,Enum):
 ADVANCE_SET="advance_set"; ADVANCE_GROUP="advance_group"; READY_TO_LOG_EXERCISE="ready_to_log_exercise"; READY_TO_LOG_GROUP="ready_to_log_group"; NO_ACTION="no_action"
@dataclass(frozen=True)
class SupersetExecutionInstruction:
 action:SupersetExecutionAction; source_session_id:int; completed_set_number:int; target_session_id:int|None=None; target_set_number:int|None=None; target_exercise:str|None=None; target_category:str|None=None; group_id:str|None=None; round_complete:bool=False; group_complete:bool=False; single_member_remaining:bool=False; remaining_member_count:int=0; reason_code:str=""
 def as_legacy_group_step(self):
  if self.action not in (SupersetExecutionAction.ADVANCE_SET,SupersetExecutionAction.ADVANCE_GROUP):return None
  return {"session_id":self.target_session_id,"exercise":self.target_exercise,"category":self.target_category,"pending_set":self.target_set_number,"round_complete":self.round_complete,"group_complete":self.group_complete,"remaining_members":self.remaining_member_count,"single_member_remaining":self.single_member_remaining,"group_id":self.group_id}
def _pending(conn,sid):
 rows=conn.execute("SELECT set_number,is_complete FROM workout_sets WHERE session_id=? ORDER BY set_number",(sid,)).fetchall()
 return 1 if not rows else next((int(n) for n,d in rows if not d),None)
def resolve_post_set_action(conn,*,session_id,completed_set_number):
 sid=int(session_id);done=int(completed_set_number or 0);src=conn.execute("SELECT exercise_group_id,COALESCE(group_position,999),status,exercise,category,meso_number,week,day_of_week FROM workout_sessions WHERE id=?",(sid,)).fetchone()
 if not src:return SupersetExecutionInstruction(SupersetExecutionAction.NO_ACTION,sid,done,reason_code="SOURCE_MISSING")
 gid,pos,status,exercise,category,meso,week,day=src
 if status!="Pending":return SupersetExecutionInstruction(SupersetExecutionAction.NO_ACTION,sid,done,group_id=gid,reason_code="SOURCE_NOT_PENDING")
 if not gid:
  pending=_pending(conn,sid)
  return SupersetExecutionInstruction(SupersetExecutionAction.READY_TO_LOG_EXERCISE if pending is None else SupersetExecutionAction.ADVANCE_SET,sid,done,sid,pending,exercise,category,None,False,pending is None,False,1,"STANDALONE")
 members=conn.execute("SELECT id,exercise,category,status,COALESCE(group_position,999) FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id=? ORDER BY COALESCE(group_position,999),COALESCE(workout_order,id),id",(meso,str(week),day,gid)).fetchall();c=[]
 for mid,mex,mcat,mstatus,mpos in members:
  pending=_pending(conn,mid) if mstatus=="Pending" else None
  if pending is not None:c.append((int(mid),mex,mcat,int(mpos),pending))
 if not c:return SupersetExecutionInstruction(SupersetExecutionAction.READY_TO_LOG_GROUP,sid,done,group_id=gid,group_complete=True,reason_code="GROUP_COMPLETE")
 key=(done,int(pos));ordered=sorted(c,key=lambda x:(x[4],x[3],x[0]));t=next((x for x in ordered if (x[4],x[3])>key),ordered[0]);tid,tex,tcat,tpos,tset=t;tk=(tset,tpos);count=len(c)
 return SupersetExecutionInstruction(SupersetExecutionAction.ADVANCE_SET if tid==sid else SupersetExecutionAction.ADVANCE_GROUP,sid,done,tid,tset,tex,tcat,gid,tk<=key or tset>done,False,count==1,count,"GROUP_NEXT")
def resolve_next_group_step(conn,session_id,completed_set):
 """Compatibility adapter retained for database.py and card-render callers."""
 return resolve_post_set_action(conn,session_id=session_id,completed_set_number=completed_set).as_legacy_group_step()
