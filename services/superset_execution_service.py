"""Framework-neutral post-set and cyclic superset execution routing."""
from dataclasses import dataclass
from enum import Enum


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
    target_session_id: int | None = None
    target_set_number: int | None = None
    target_exercise: str | None = None
    target_category: str | None = None
    group_id: str | None = None
    round_complete: bool = False
    group_complete: bool = False
    single_member_remaining: bool = False
    remaining_member_count: int = 0
    reason_code: str = ""

    def as_legacy_group_step(self):
        if self.action not in (
            SupersetExecutionAction.ADVANCE_SET,
            SupersetExecutionAction.ADVANCE_GROUP,
        ):
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


def _pending(conn, session_id):
    rows = conn.execute(
        "SELECT set_number,is_complete FROM workout_sets "
        "WHERE session_id=? ORDER BY set_number",
        (session_id,),
    ).fetchall()
    return 1 if not rows else next((int(number) for number, done in rows if not done), None)


def select_cyclic_target(candidates, *, source_position, completed_set_number):
    """Choose the next eligible member in cyclic position order.

    Candidates are tuples of (session_id, exercise, category, position, pending_set).
    Same-round or lagging work is preferred before the cycle advances to the
    lowest available next round. This lets execution begin at A2/A3 without
    resetting to A1 while keeping unequal set counts safe.
    """
    if not candidates:
        return None
    ordered = sorted(candidates, key=lambda item: (item[3], item[0]))
    after = [item for item in ordered if item[3] > int(source_position)]
    wrapped = [item for item in ordered if item[3] <= int(source_position)]
    cyclic = after + wrapped
    same_round = [item for item in cyclic if item[4] <= int(completed_set_number)]
    if same_round:
        return same_round[0]
    next_round = min(item[4] for item in cyclic)
    return next(item for item in cyclic if item[4] == next_round)


def resolve_post_set_action(conn, *, session_id, completed_set_number):
    session_id = int(session_id)
    completed_set_number = int(completed_set_number or 0)
    source = conn.execute(
        "SELECT exercise_group_id,COALESCE(group_position,999),status,"
        "exercise,category,meso_number,week,day_of_week "
        "FROM workout_sessions WHERE id=?",
        (session_id,),
    ).fetchone()
    if not source:
        return SupersetExecutionInstruction(
            SupersetExecutionAction.NO_ACTION,
            session_id,
            completed_set_number,
            reason_code="SOURCE_MISSING",
        )
    group_id, position, status, exercise, category, meso, week, day = source
    if status != "Pending":
        return SupersetExecutionInstruction(
            SupersetExecutionAction.NO_ACTION,
            session_id,
            completed_set_number,
            group_id=group_id,
            reason_code="SOURCE_NOT_PENDING",
        )
    if not group_id:
        pending = _pending(conn, session_id)
        return SupersetExecutionInstruction(
            SupersetExecutionAction.READY_TO_LOG_EXERCISE
            if pending is None
            else SupersetExecutionAction.ADVANCE_SET,
            session_id,
            completed_set_number,
            session_id,
            pending,
            exercise,
            category,
            None,
            False,
            pending is None,
            False,
            1,
            "STANDALONE",
        )

    members = conn.execute(
        "SELECT id,exercise,category,status,COALESCE(group_position,999) "
        "FROM workout_sessions WHERE meso_number=? AND week=? "
        "AND day_of_week=? AND exercise_group_id=? "
        "ORDER BY COALESCE(group_position,999),COALESCE(workout_order,id),id",
        (meso, str(week), day, group_id),
    ).fetchall()
    candidates = []
    for member_id, member_exercise, member_category, member_status, member_position in members:
        pending = _pending(conn, member_id) if member_status == "Pending" else None
        if pending is not None:
            candidates.append(
                (
                    int(member_id),
                    member_exercise,
                    member_category,
                    int(member_position),
                    pending,
                )
            )
    if not candidates:
        return SupersetExecutionInstruction(
            SupersetExecutionAction.READY_TO_LOG_GROUP,
            session_id,
            completed_set_number,
            group_id=group_id,
            group_complete=True,
            reason_code="GROUP_COMPLETE",
        )

    target = select_cyclic_target(
        candidates,
        source_position=position,
        completed_set_number=completed_set_number,
    )
    target_id, target_exercise, target_category, target_position, target_set = target
    remaining_count = len(candidates)
    wrapped = target_position <= int(position)
    round_complete = wrapped or target_set > completed_set_number
    return SupersetExecutionInstruction(
        SupersetExecutionAction.ADVANCE_SET
        if target_id == session_id
        else SupersetExecutionAction.ADVANCE_GROUP,
        session_id,
        completed_set_number,
        target_id,
        target_set,
        target_exercise,
        target_category,
        group_id,
        round_complete,
        False,
        remaining_count == 1,
        remaining_count,
        "GROUP_NEXT_CYCLIC",
    )


def resolve_next_group_step(conn, session_id, completed_set):
    """Compatibility adapter retained for database.py and legacy callers."""
    return resolve_post_set_action(
        conn,
        session_id=session_id,
        completed_set_number=completed_set,
    ).as_legacy_group_step()
