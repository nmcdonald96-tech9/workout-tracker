"""Completed-exercise revision persistence authority for IronCycle 1.93.

Framework-neutral by design: this module owns SQLite state transitions and never
imports Flet.  UI drafts remain owned by ``main.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from typing import Any, Callable, Iterable, Optional

from services.rpe_service import normalize_rpe
from services.target_ownership_service import (
    VALID_REPS_SOURCES, VALID_WEIGHT_SOURCES, normalize_reps_source,
    normalize_weight_source,
)
from services.progression_service import recalculate_after_completed_revision

COMPLETED = "Completed"
PENDING = "Pending"

class CompletedRevisionError(RuntimeError):
    """Structured, privacy-safe operation failure."""
    def __init__(self, stage: str, code: str, message: str):
        super().__init__(message)
        self.stage, self.code = stage, code

@dataclass(frozen=True)
class CompletedSetSnapshot:
    id: Optional[int]
    session_id: int
    set_number: int
    weight: float
    reps: int
    rpe: float
    raw_rest_seconds: Optional[int]
    target_weight: float
    target_reps: int
    normal_target_weight: float
    normal_target_reps: int
    completed_at: str
    is_complete: bool
    progression_decision: Optional[str]
    progression_reason_code: Optional[str]
    progression_reason: Optional[str]
    progression_settings_snapshot: Optional[str]
    weight_source: str
    reps_source: str

@dataclass(frozen=True)
class CompletedRevisionSnapshot:
    session_id: int
    exercise: str
    movement_type: str
    session_status: str
    date: Optional[str]
    meso_number: Optional[int]
    week: Optional[str]
    day_of_week: Optional[str]
    workout_order: Optional[int]
    historical_bodyweight_snapshot: Optional[float]
    completed_sets: tuple[CompletedSetSnapshot, ...]
    revision_fingerprint: str

@dataclass(frozen=True)
class RevisedCompletedSet:
    id: Optional[int]
    session_id: int
    set_number: int
    weight: float
    reps: int
    rpe: float
    raw_rest_seconds: Optional[int]
    target_weight: float
    target_reps: int
    normal_target_weight: float
    normal_target_reps: int
    completed_at: str
    is_complete: bool
    progression_decision: Optional[str]
    progression_reason_code: Optional[str]
    progression_reason: Optional[str]
    progression_settings_snapshot: Optional[str]
    weight_source: str
    reps_source: str

@dataclass(frozen=True)
class RevisionCommitResult:
    session_id: int
    sets_added_count: int
    sets_removed_count: int
    sets_modified_count: int
    future_session_ids_updated: tuple[int, ...]
    user_owned_future_sessions_skipped: tuple[int, ...]
    progression_recalculation_result: dict
    audit_outcome: str

@dataclass(frozen=True)
class ReturnToPendingResult:
    session_id: int
    draft_rows_preserved: int
    progression_reconciliation_status: str
    future_session_ids_updated: tuple[int, ...]
    user_owned_future_sessions_skipped: tuple[int, ...]

_SET_COLUMNS = (
    "id", "session_id", "set_number", "weight", "reps", "rpe",
    "rest_seconds", "target_weight", "target_reps", "normal_target_weight",
    "normal_target_reps", "completed_at", "is_complete",
    "progression_decision", "progression_reason_code", "progression_reason",
    "progression_settings_snapshot", "weight_source", "reps_source",
)
_SESSION_SELECT = """SELECT id,exercise,COALESCE(movement_type,'Isolation'),status,date,meso_number,week,day_of_week,
 COALESCE(workout_order,id),bodyweight_snapshot FROM workout_sessions WHERE id=?"""

def _finite(value: Any, label: str, *, integer: bool = False, nonnegative: bool = True):
    if isinstance(value, bool):
        raise ValueError(f"{label} is invalid.")
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label} must be numeric.")
    if not math.isfinite(float(number)) or (nonnegative and number < 0):
        raise ValueError(f"{label} is invalid.")
    if integer and float(value) != number:
        raise ValueError(f"{label} must be a whole number.")
    return number

def _timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Completion timestamp is required.")
    try: datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError): raise ValueError("Completion timestamp is invalid.")
    return raw

def _canonical_set(row: CompletedSetSnapshot) -> dict:
    return {name: getattr(row, "raw_rest_seconds" if name == "rest_seconds" else name) for name in _SET_COLUMNS}

def _fingerprint(session_row, sets: Iterable[CompletedSetSnapshot]) -> str:
    payload = {
        "session": list(session_row),
        "sets": [_canonical_set(row) for row in sets],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def _read_snapshot(conn, session_id: int, *, require_completed: bool = True) -> CompletedRevisionSnapshot:
    sid = int(session_id)
    session = conn.execute(_SESSION_SELECT, (sid,)).fetchone()
    if not session:
        raise CompletedRevisionError("snapshot", "session_missing", "The exercise session no longer exists.")
    if require_completed and session[3] != COMPLETED:
        raise CompletedRevisionError("snapshot", "session_not_completed", "The exercise is no longer completed.")
    columns = ",".join(_SET_COLUMNS)
    raw = conn.execute(f"SELECT {columns} FROM workout_sets WHERE session_id=? ORDER BY set_number,id", (sid,)).fetchall()
    sets = tuple(CompletedSetSnapshot(
        id=r[0], session_id=r[1], set_number=r[2], weight=r[3], reps=r[4], rpe=r[5],
        raw_rest_seconds=r[6], target_weight=r[7], target_reps=r[8],
        normal_target_weight=r[9], normal_target_reps=r[10], completed_at=r[11],
        is_complete=bool(r[12]), progression_decision=r[13], progression_reason_code=r[14],
        progression_reason=r[15], progression_settings_snapshot=r[16],
        weight_source=normalize_weight_source(r[17]), reps_source=normalize_reps_source(r[18]),
    ) for r in raw)
    return CompletedRevisionSnapshot(
        sid, session[1], session[2], session[3], session[4], session[5], session[6], session[7],
        session[8], session[9], sets, _fingerprint(session, sets),
    )

def capture_revision_snapshot(conn, session_id: int) -> CompletedRevisionSnapshot:
    """Capture complete schema-20 revision state without changing durable data."""
    return _read_snapshot(conn, session_id, require_completed=True)

def editable_copies(snapshot: CompletedRevisionSnapshot) -> list[dict]:
    """Return plain in-memory UI drafts; this function performs no I/O."""
    return [{
        "id": s.id, "session_id": s.session_id, "w": str(s.weight), "r": str(s.reps),
        "rpe": str(s.rpe), "rest": s.raw_rest_seconds, "completed_at": s.completed_at,
        "done": True, "target_weight": s.target_weight, "target_reps": s.target_reps,
        "normal_target_weight": s.normal_target_weight, "normal_target_reps": s.normal_target_reps,
        "w_source": s.weight_source, "r_source": s.reps_source,
    } for s in snapshot.completed_sets]

def _supported_source(value, valid, label):
    raw = str(value or "").strip().lower()
    if raw not in valid: raise ValueError(f"Unsupported {label} ownership.")
    return raw

def normalize_revised_rows(snapshot: CompletedRevisionSnapshot, rows: Iterable[Any]) -> tuple[RevisedCompletedSet, ...]:
    prepared=[]; seen_ids=set(); seen_numbers=set(); original={x.id:x for x in snapshot.completed_sets if x.id is not None}
    for position, item in enumerate(rows or (), start=1):
        d = dict(item) if isinstance(item, dict) else item.__dict__.copy()
        sid = int(d.get("session_id", snapshot.session_id))
        if sid != snapshot.session_id: raise ValueError("A revised row belongs to another session.")
        row_id = d.get("id"); row_id = int(row_id) if row_id not in (None, "") else None
        if row_id is not None:
            if row_id in seen_ids or row_id not in original: raise ValueError("Duplicate or unknown completed-set row.")
            seen_ids.add(row_id)
        number = _finite(d.get("set_number", position), "Set number", integer=True)
        if number != position or number in seen_numbers: raise ValueError("Set numbers must be unique and sequential.")
        seen_numbers.add(number)
        # Reject unsupported partial values rather than coercing them.
        for key in ("w", "r", "rpe"):
            value=d.get(key, d.get({"w":"weight","r":"reps","rpe":"rpe"}[key]))
            if value is None or str(value).strip()=="": raise ValueError(f"Set {position} is incomplete.")
        weight=_finite(d.get("w",d.get("weight")),"Weight")
        reps=_finite(d.get("r",d.get("reps")),"Reps",integer=True)
        if reps < 1: raise ValueError("Reps must be at least 1.")
        nrpe=normalize_rpe(d.get("rpe"))
        if nrpe is None: raise ValueError("RPE must be 1 to 10 in 0.5 steps.")
        old=original.get(row_id)
        def value(name, alias=None):
            v=d.get(name, d.get(alias))
            return v if v is not None else (getattr(old,name) if old else None)
        tw=_finite(value("target_weight"),"Target weight")
        tr=_finite(value("target_reps"),"Target reps",integer=True)
        ntw=_finite(value("normal_target_weight"),"Normal target weight")
        ntr=_finite(value("normal_target_reps"),"Normal target reps",integer=True)
        if tr<1 or ntr<1: raise ValueError("Target reps must be at least 1.")
        stamp=_timestamp(value("completed_at"))
        rest=value("raw_rest_seconds","rest")
        rest=None if rest is None else _finite(rest,"Rest seconds",integer=True)
        ws=_supported_source(d.get("w_source",d.get("weight_source",old.weight_source if old else "target")),VALID_WEIGHT_SOURCES,"weight")
        rs=_supported_source(d.get("r_source",d.get("reps_source",old.reps_source if old else "target")),VALID_REPS_SOURCES,"reps")
        # Same value keeps ownership; direct changes become user-owned. A UI-marked
        # weight-derived rep remains derived.
        if old:
            if weight != old.weight: ws="user"
            else: ws=old.weight_source
            if reps != old.reps:
                rs="weight_derived" if rs=="weight_derived" else "user"
            else: rs=old.reps_source
        prepared.append(RevisedCompletedSet(row_id,sid,number,weight,reps,float(nrpe),rest,tw,tr,ntw,ntr,stamp,True,
            old.progression_decision if old else None, old.progression_reason_code if old else None,
            old.progression_reason if old else None, old.progression_settings_snapshot if old else None,ws,rs))
    if not prepared: raise ValueError("At least one completed set is required.")
    return tuple(prepared)

def _settings(row: RevisedCompletedSet) -> dict:
    try:
        parsed=json.loads(row.progression_settings_snapshot or "{}")
        if isinstance(parsed,dict) and parsed: return parsed
    except Exception: pass
    return {"max_progress_rpe":9.5,"reduction_threshold":0.7,"max_progression_weight":None,
            "progression_step":5.0,"reduction_steps":1,"rep_ceiling":15,"custom_active":False}

def _audit(conn, event_type: str, metadata: dict, audit_writer: Optional[Callable]=None):
    safe={k:v for k,v in metadata.items() if k in {
        "session_id","sets_added_count","sets_removed_count","sets_modified_count",
        "progression_recalculated","future_sessions_updated","user_owned_sessions_skipped","result_code"}}
    if audit_writer: audit_writer(conn,event_type,safe)
    else: conn.execute("INSERT INTO app_audit(created_at,action,details) VALUES(?,?,?)",
        (datetime.now().isoformat(timespec="seconds"),event_type,json.dumps(safe,sort_keys=True,separators=(",",":"))))

def _later_key(week, day, order, sid):
    days={"Monday":1,"Tuesday":2,"Wednesday":3,"Thursday":4,"Friday":5,"Saturday":6,"Sunday":7}
    w=10**6 if str(week)=="Deload" else int(week) if str(week).isdigit() else 10**6-1
    return (w,days.get(str(day),99),int(order or sid),int(sid))

def _sync_future(conn, snapshot, next_weight, next_reps, *, restore=False):
    rows=conn.execute("""SELECT id,week,day_of_week,COALESCE(workout_order,id),target_weight,target_reps
      FROM workout_sessions WHERE exercise=? AND meso_number=? AND status='Pending' AND id<>?""",
      (snapshot.exercise,snapshot.meso_number,snapshot.session_id)).fetchall()
    origin=_later_key(snapshot.week,snapshot.day_of_week,snapshot.workout_order,snapshot.session_id)
    eligible=[r for r in rows if _later_key(r[1],r[2],r[3],r[0])>origin]
    updated=[]; skipped=[]
    for sid,week,day,order,tw,tr in eligible:
        set_rows=conn.execute("SELECT weight_source,reps_source FROM workout_sets WHERE session_id=? ORDER BY set_number",(sid,)).fetchall()
        weight_owned=all(normalize_weight_source(x[0])=="target" for x in set_rows) if set_rows else True
        reps_owned=all(normalize_reps_source(x[1])=="target" for x in set_rows) if set_rows else True
        if not weight_owned or not reps_owned:
            skipped.append(sid); continue
        conn.execute("UPDATE workout_sessions SET target_weight=?,target_reps=? WHERE id=?",(next_weight,next_reps,sid))
        conn.execute("UPDATE workout_sets SET weight=CASE WHEN COALESCE(weight_source,'target')='target' THEN ? ELSE weight END, reps=CASE WHEN COALESCE(reps_source,'target')='target' THEN ? ELSE reps END, target_weight=?,target_reps=?,normal_target_weight=?,normal_target_reps=? WHERE session_id=?",
            (next_weight,next_reps,next_weight,next_reps,next_weight,next_reps,sid))
        updated.append(sid)
    return tuple(updated),tuple(skipped)

def commit_completed_revision(conn, snapshot, revised_rows, *, audit_writer=None) -> RevisionCommitResult:
    try: prepared=normalize_revised_rows(snapshot,revised_rows)
    except Exception as exc: raise CompletedRevisionError("validation","invalid_revision",str(exc)) from exc
    existing={x.id:x for x in snapshot.completed_sets}; revised_ids={x.id for x in prepared if x.id is not None}
    added=sum(x.id is None for x in prepared); removed=len(set(existing)-revised_ids)
    modified=sum(1 for x in prepared if x.id in existing and any((x.weight!=existing[x.id].weight,x.reps!=existing[x.id].reps,x.rpe!=existing[x.id].rpe,x.completed_at!=existing[x.id].completed_at,x.weight_source!=existing[x.id].weight_source,x.reps_source!=existing[x.id].reps_source)))
    stage="begin"
    try:
        conn.execute("BEGIN IMMEDIATE")
        stage="concurrent_check"; current=_read_snapshot(conn,snapshot.session_id,require_completed=True)
        if current.revision_fingerprint!=snapshot.revision_fingerprint:
            raise CompletedRevisionError(stage,"revision_conflict","The completed result changed after revision mode opened.")
        stage="reconcile"
        for row in prepared:
            if row.id is not None:
                conn.execute("""UPDATE workout_sets SET set_number=?,weight=?,reps=?,rpe=?,rest_seconds=?,target_weight=?,target_reps=?,normal_target_weight=?,normal_target_reps=?,completed_at=?,is_complete=1,weight_source=?,reps_source=? WHERE id=? AND session_id=?""",
                    (row.set_number,row.weight,row.reps,row.rpe,row.raw_rest_seconds,row.target_weight,row.target_reps,row.normal_target_weight,row.normal_target_reps,row.completed_at,row.weight_source,row.reps_source,row.id,snapshot.session_id))
            else:
                cur=conn.execute("""INSERT INTO workout_sets(session_id,set_number,weight,reps,rpe,rest_seconds,target_weight,target_reps,normal_target_weight,normal_target_reps,completed_at,is_complete,progression_decision,progression_reason_code,progression_reason,progression_settings_snapshot,weight_source,reps_source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (snapshot.session_id,row.set_number,row.weight,row.reps,row.rpe,row.raw_rest_seconds,row.target_weight,row.target_reps,row.normal_target_weight,row.normal_target_reps,row.completed_at,1,row.progression_decision,row.progression_reason_code,row.progression_reason,row.progression_settings_snapshot,row.weight_source,row.reps_source))
                object.__setattr__(row,"id",cur.lastrowid)
        for row_id in set(existing)-revised_ids: conn.execute("DELETE FROM workout_sets WHERE id=? AND session_id=?",(row_id,snapshot.session_id))
        # Two phase renumber avoids collisions if a future unique constraint is added.
        ids=[r[0] for r in conn.execute("SELECT id FROM workout_sets WHERE session_id=? ORDER BY set_number,id",(snapshot.session_id,))]
        for n,row_id in enumerate(ids,1): conn.execute("UPDATE workout_sets SET set_number=? WHERE id=?",(-n,row_id))
        for n,row_id in enumerate(ids,1): conn.execute("UPDATE workout_sets SET set_number=? WHERE id=?",(n,row_id))
        stage="progression"; persisted=tuple(RevisedCompletedSet(**{**r.__dict__,"set_number":i}) for i,r in enumerate(prepared,1))
        progression=recalculate_after_completed_revision(
            conn,snapshot.session_id,persisted,exercise_name=snapshot.exercise,
            movement_type=snapshot.movement_type,bodyweight=snapshot.historical_bodyweight_snapshot or 0.0,
        )
        first_target=progression["next_targets"][0]
        next_w,next_r=float(first_target["w"]),int(first_target["r"])
        stage="future_sync"; updated,skipped=_sync_future(conn,snapshot,next_w,next_r)
        stage="audit"; _audit(conn,"completed_exercise_revision_saved",{
            "session_id":snapshot.session_id,"sets_added_count":added,"sets_removed_count":removed,
            "sets_modified_count":modified,"progression_recalculated":True,
            "future_sessions_updated":len(updated),"user_owned_sessions_skipped":len(skipped),"result_code":"committed"},audit_writer)
        stage="integrity"; count=conn.execute("SELECT COUNT(*) FROM workout_sets WHERE session_id=? AND is_complete=1",(snapshot.session_id,)).fetchone()[0]
        if count!=len(prepared): raise RuntimeError("Completed-session row integrity check failed.")
        if conn.execute("SELECT status FROM workout_sessions WHERE id=?",(snapshot.session_id,)).fetchone()[0]!=COMPLETED: raise RuntimeError("Completed-session status integrity check failed.")
        conn.commit()
        return RevisionCommitResult(snapshot.session_id,added,removed,modified,updated,skipped,progression,"committed")
    except Exception as exc:
        conn.rollback()
        if isinstance(exc,CompletedRevisionError): raise
        raise CompletedRevisionError(stage,"revision_failed",f"Completed revision failed during {stage}.") from exc

def return_to_pending(conn, session_id: int, *, audit_writer=None) -> ReturnToPendingResult:
    stage="begin"
    try:
        conn.execute("BEGIN IMMEDIATE"); stage="snapshot"; snap=_read_snapshot(conn,session_id,require_completed=True)
        stage="drafts"
        conn.execute("UPDATE workout_sets SET is_complete=0,completed_at=NULL,rest_seconds=NULL,progression_decision=NULL,progression_reason_code=NULL,progression_reason=NULL,progression_settings_snapshot=NULL WHERE session_id=?",(snap.session_id,))
        conn.execute("UPDATE workout_sessions SET status=? WHERE id=?",(PENDING,snap.session_id))
        # Deterministically restore target-owned future rows to the completed
        # session's pre-progression target snapshot; user-owned drafts are skipped.
        first=snap.completed_sets[0] if snap.completed_sets else None
        stage="progression_reconcile"
        updated,skipped=_sync_future(conn,snap,first.normal_target_weight if first else 0,first.normal_target_reps if first else 1,restore=True)
        stage="audit"; _audit(conn,"completed_exercise_returned_to_pending",{
            "session_id":snap.session_id,"sets_added_count":0,"sets_removed_count":0,"sets_modified_count":len(snap.completed_sets),
            "progression_recalculated":True,"future_sessions_updated":len(updated),"user_owned_sessions_skipped":len(skipped),"result_code":"pending"},audit_writer)
        conn.commit(); return ReturnToPendingResult(snap.session_id,len(snap.completed_sets),"reconciled",updated,skipped)
    except Exception as exc:
        conn.rollback()
        if isinstance(exc,CompletedRevisionError): raise
        raise CompletedRevisionError(stage,"return_to_pending_failed",f"Return to Pending failed during {stage}.") from exc
