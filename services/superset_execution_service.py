"""Framework-neutral post-set and superset execution routing for IronCycle 1.94."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional

PENDING = "Pending"

class SupersetExecutionAction(str, Enum):
    ADVANCE_SET = "advance_set"
    ADVANCE_GROUP = "advance_group"
    READY_TO_LOG_EXERCISE = "ready_to_log_exercise"
    READY_TO_LOG_GROUP = "ready_to_log_group"
    NO_ACTION = "no_action"

@dataclass(frozen=True)
class SupersetExecutionInstruction:
    action: SupersetExecutionAction
    source_session_id: int
    completed_set_number: int
    target_session_id: Optional[int] = None
    target_set_number: Optional[int] = None
    target_exercise: Optional[str] = None
    target_category: Optional[str] = None
    group_id: Optional[str] = None
    round_complete: bool = False
    group_complete: bool = False
    single_member_remaining: bool = False
    remaining_member_count: int = 0
    reason_code: str = ""
    message: Optional[str] = None

    def as_legacy_group_step(self):
        if self.action not in (SupersetExecutionAction.ADVANCE_SET, SupersetExecutionAction.ADVANCE_GROUP):
            return None
        return {
            "session_id": self.target_session_id,
            "exercise": self.target_exercise,
            "category": self.target_category,
            "pending_set": self.target_set_number,
            "round_complete": self.round_complete,
            "group_complete": self.group_complete,
            "remaining_members": self.remaining_member_count,
            "single_member_remaining": self.single_member_remaining,
            "group_id": self.group_id,
        }

def _pending_set(conn, session_id):
    rows=conn.execute("SELECT set_number,is_complete FROM workout_sets WHERE session_id=? ORDER BY set_number",(int(session_id),)).fetchall()
    if not rows:
        return 1
    return next((int(number) for number,done in rows if not done),None)

def resolve_post_set_action(conn, *, session_id: int, completed_set_number: int) -> SupersetExecutionInstruction:
    """Return one deterministic UI-neutral instruction without committing or mutating controls."""
    sid=int(session_id); completed=int(completed_set_number or 0)
    source=conn.execute("""SELECT exercise_group_id,COALESCE(group_position,999),status,exercise,category,
                                  meso_number,week,day_of_week
                           FROM workout_sessions WHERE id=?""",(sid,)).fetchone()
    if not source:
        return SupersetExecutionInstruction(SupersetExecutionAction.NO_ACTION,sid,completed,reason_code="SOURCE_MISSING")
    group_id,source_position,status,exercise,category,meso,week,day=source
    if status != PENDING:
        return SupersetExecutionInstruction(SupersetExecutionAction.NO_ACTION,sid,completed,group_id=group_id,reason_code="SOURCE_NOT_PENDING")
    if not group_id:
        pending=_pending_set(conn,sid)
        if pending is None:
            return SupersetExecutionInstruction(SupersetExecutionAction.READY_TO_LOG_EXERCISE,sid,completed,target_session_id=sid,group_complete=True,reason_code="STANDALONE_COMPLETE")
        return SupersetExecutionInstruction(SupersetExecutionAction.ADVANCE_SET,sid,completed,target_session_id=sid,target_set_number=pending,target_exercise=exercise,target_category=category,reason_code="STANDALONE_NEXT_SET")
    members=conn.execute("""SELECT id,exercise,category,status,COALESCE(group_position,999)
                            FROM workout_sessions
                            WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id=?
                            ORDER BY COALESCE(group_position,999),COALESCE(workout_order,id),id""",
                         (meso,str(week),day,group_id)).fetchall()
    candidates=[]
    for member_id,member_exercise,member_category,member_status,position in members:
        if member_status != PENDING:
            continue
        pending=_pending_set(conn,member_id)
        if pending is not None:
            candidates.append((int(member_id),member_exercise,member_category,int(position),pending))
    if not candidates:
        return SupersetExecutionInstruction(SupersetExecutionAction.READY_TO_LOG_GROUP,sid,completed,group_id=group_id,group_complete=True,reason_code="GROUP_COMPLETE")
    completed_key=(completed,int(source_position))
    ordered=sorted(candidates,key=lambda item:(item[4],item[3],item[0]))
    target=next((item for item in ordered if (item[4],item[3])>completed_key),ordered[0])
    target_id,target_exercise,target_category,target_position,target_set=target
    target_key=(target_set,target_position)
    round_complete=target_key<=completed_key or target_set>completed
    remaining=len(candidates)
    action=SupersetExecutionAction.ADVANCE_SET if target_id==sid else SupersetExecutionAction.ADVANCE_GROUP
    return SupersetExecutionInstruction(action,sid,completed,target_id,target_set,target_exercise,target_category,group_id,round_complete,False,remaining==1,remaining,"GROUP_NEXT_SET")

def resolve_next_group_step(conn, session_id, completed_set):
    """Compatibility result for resolver-v2 callers; policy remains single-sourced here."""
    instruction=resolve_post_set_action(conn,session_id=session_id,completed_set_number=completed_set)
    return instruction.as_legacy_group_step()
