import json
import sqlite3
from pathlib import Path
import pytest

from services.completed_revision_service import (
    CompletedRevisionError, capture_revision_snapshot, commit_completed_revision,
    editable_copies, normalize_revised_rows, return_to_pending,
)

ROOT=Path(__file__).resolve().parents[1]

def db():
    c=sqlite3.connect(":memory:")
    c.executescript("""
    CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise TEXT,movement_type TEXT,status TEXT,date TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER,bodyweight_snapshot REAL,target_weight REAL,target_reps INTEGER);
    CREATE TABLE workout_sets(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id INTEGER,set_number INTEGER,weight REAL,reps INTEGER,rpe REAL,rest_seconds INTEGER,target_weight REAL,target_reps INTEGER,normal_target_weight REAL,normal_target_reps INTEGER,completed_at TEXT,is_complete INTEGER,progression_decision TEXT,progression_reason_code TEXT,progression_reason TEXT,progression_settings_snapshot TEXT,weight_source TEXT,reps_source TEXT);
    CREATE TABLE app_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT,action TEXT,details TEXT);
    """)
    return c

def seed(c,status="Completed"):
    c.execute("INSERT INTO workout_sessions VALUES(1,'Bench','Compound',?,'2026-09-25',1,'1','Monday',1,181,100,10)",(status,))
    settings=json.dumps({"max_progress_rpe":9.5,"reduction_threshold":.7,"max_progression_weight":None,"progression_step":5,"reduction_steps":1,"rep_ceiling":15,"custom_active":False})
    rows=[(1,1,100,10,8.0,0,100,10,100,10,'2026-09-25T10:00:00',1,'hold','SMALL_MISS','held',settings,'target','weight_derived'),(1,2,105,9,8.5,83,105,9,105,9,'2026-09-25T10:01:23',1,'progress','TARGET_ACHIEVED','ok',settings,'user','user')]
    c.executemany("INSERT INTO workout_sets(session_id,set_number,weight,reps,rpe,rest_seconds,target_weight,target_reps,normal_target_weight,normal_target_reps,completed_at,is_complete,progression_decision,progression_reason_code,progression_reason,progression_settings_snapshot,weight_source,reps_source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
    c.commit()

def snap(c): seed(c); return capture_revision_snapshot(c,1)

def test_snapshot_rejects_missing_and_non_completed():
    c=db()
    with pytest.raises(CompletedRevisionError): capture_revision_snapshot(c,999)
    seed(c,"Pending")
    with pytest.raises(CompletedRevisionError): capture_revision_snapshot(c,1)

def test_snapshot_preserves_schema20_fields_and_is_read_only():
    c=db(); s=snap(c); before=c.total_changes
    assert s.historical_bodyweight_snapshot==181 and s.completed_sets[1].raw_rest_seconds==83
    assert s.completed_sets[1].progression_reason_code=="TARGET_ACHIEVED"
    assert s.completed_sets[0].reps_source=="weight_derived"
    assert c.total_changes==before

def test_begin_and_cancel_are_memory_only():
    c=db(); s=snap(c); before=c.execute("SELECT * FROM workout_sets").fetchall()
    drafts=editable_copies(s); drafts[0]["w"]="999"; del drafts
    assert c.execute("SELECT * FROM workout_sets").fetchall()==before

def test_invalid_rpe_and_partial_data_are_rejected():
    c=db(); s=snap(c); rows=editable_copies(s)
    for invalid in ("8.3","85","10.5","text"):
        trial=[dict(x) for x in rows];trial[0]["rpe"]=invalid
        with pytest.raises(ValueError): normalize_revised_rows(s,trial)
    rows[0]["r"]=""
    with pytest.raises(ValueError): normalize_revised_rows(s,rows)

def test_valid_revision_updates_in_place_preserves_metadata_bodyweight_and_ownership():
    c=db(); s=snap(c); ids=[x.id for x in s.completed_sets]; rows=editable_copies(s)
    rows[0]["rpe"]="9"; result=commit_completed_revision(c,s,rows)
    after=c.execute("SELECT id,set_number,weight_source,reps_source,rest_seconds FROM workout_sets ORDER BY set_number").fetchall()
    assert [x[0] for x in after]==ids and after[0][2:]==('target','weight_derived',0)
    assert c.execute("SELECT bodyweight_snapshot FROM workout_sessions WHERE id=1").fetchone()[0]==181
    assert result.sets_modified_count==1 and result.progression_recalculation_result["count"]==2

def test_direct_edits_and_weight_derived_ownership():
    c=db(); s=snap(c); rows=editable_copies(s)
    rows[0]["w"]="110";rows[0]["r"]="8";rows[0]["r_source"]="weight_derived"
    commit_completed_revision(c,s,rows)
    assert c.execute("SELECT weight_source,reps_source FROM workout_sets WHERE set_number=1").fetchone()==('user','weight_derived')
    c2=db();s2=snap(c2);rows=editable_copies(s2);rows[1]["r"]="8";commit_completed_revision(c2,s2,rows)
    assert c2.execute("SELECT reps_source FROM workout_sets WHERE set_number=2").fetchone()[0]=='user'

def test_add_remove_and_deterministic_renumber_are_bounded():
    c=db(); s=snap(c); rows=editable_copies(s); removed_id=rows.pop(0)["id"]
    rows.append({"session_id":1,"w":"90","r":"12","rpe":"8","rest":20,"completed_at":"2026-09-25T10:03:00","done":True,"target_weight":90,"target_reps":12,"normal_target_weight":90,"normal_target_reps":12,"w_source":"target","r_source":"target"})
    result=commit_completed_revision(c,s,rows)
    got=c.execute("SELECT id,set_number,progression_settings_snapshot FROM workout_sets ORDER BY set_number").fetchall()
    assert [x[1] for x in got]==[1,2] and all(x[2] for x in got)
    assert c.execute("SELECT 1 FROM workout_sets WHERE id=?",(removed_id,)).fetchone() is None
    assert result.sets_added_count==1 and result.sets_removed_count==1

def test_fingerprint_detects_concurrent_change_without_overwrite():
    c=db(); s=snap(c); rows=editable_copies(s); rows[0]["w"]="120"
    c.execute("UPDATE workout_sets SET rpe=9.5 WHERE id=?",(s.completed_sets[0].id,));c.commit()
    with pytest.raises(CompletedRevisionError) as e: commit_completed_revision(c,s,rows)
    assert e.value.code=='revision_conflict'
    assert c.execute("SELECT weight,rpe FROM workout_sets WHERE id=?",(s.completed_sets[0].id,)).fetchone()==(100.0,9.5)

def test_future_target_owned_updates_and_user_owned_skips_deload_is_later():
    c=db(); s=snap(c)
    c.execute("INSERT INTO workout_sessions VALUES(2,'Bench','Compound','Pending',NULL,1,'2','Monday',1,NULL,100,10)")
    c.execute("INSERT INTO workout_sessions VALUES(3,'Bench','Compound','Pending',NULL,1,'Deload','Monday',1,NULL,100,10)")
    c.execute("INSERT INTO workout_sets(session_id,set_number,weight,reps,weight_source,reps_source) VALUES(2,1,100,10,'target','target')")
    c.execute("INSERT INTO workout_sets(session_id,set_number,weight,reps,weight_source,reps_source) VALUES(3,1,100,10,'user','target')");c.commit()
    result=commit_completed_revision(c,s,editable_copies(s))
    assert result.future_session_ids_updated==(2,) and result.user_owned_future_sessions_skipped==(3,)

def test_audit_same_transaction_privacy_and_failure_rolls_back_everything():
    c=db(); s=snap(c); calls=[]
    def writer(conn,event,meta):
        assert conn is c; calls.append(meta); conn.execute("INSERT INTO app_audit VALUES(NULL,'now',?,?)",(event,json.dumps(meta)))
    commit_completed_revision(c,s,editable_copies(s),audit_writer=writer)
    detail=c.execute("SELECT details FROM app_audit").fetchone()[0]
    assert 'weight' not in detail and 'rpe' not in detail and calls
    c2=db();s2=snap(c2);before=c2.execute("SELECT * FROM workout_sets").fetchall()
    def fail(conn,event,meta): raise RuntimeError('audit failure')
    with pytest.raises(CompletedRevisionError): commit_completed_revision(c2,s2,editable_copies(s2),audit_writer=fail)
    assert c2.execute("SELECT * FROM workout_sets").fetchall()==before and c2.execute("SELECT COUNT(*) FROM app_audit").fetchone()[0]==0

def test_return_to_pending_retains_drafts_clears_completed_only_and_reconciles():
    c=db(); s=snap(c)
    c.execute("INSERT INTO workout_sessions VALUES(2,'Bench','Compound','Pending',NULL,1,'2','Monday',1,NULL,150,20)");c.commit()
    result=return_to_pending(c,1)
    assert result.draft_rows_preserved==2 and result.progression_reconciliation_status=='reconciled'
    assert c.execute("SELECT status,bodyweight_snapshot FROM workout_sessions WHERE id=1").fetchone()==('Pending',181.0)
    rows=c.execute("SELECT weight,reps,is_complete,completed_at,progression_decision FROM workout_sets WHERE session_id=1 ORDER BY set_number").fetchall()
    assert rows[0][:2]==(100.0,10) and all(x[2:]==(0,None,None) for x in rows)

def test_release_contract_and_architectural_boundary():
    constants=(ROOT/'constants.py').read_text(); service=(ROOT/'services/completed_revision_service.py').read_text(); main=(ROOT/'main.py').read_text()
    assert 'APP_VERSION = "1.99.2"' in constants and 'DATABASE_SCHEMA_VERSION = 20' in constants
    assert 'import flet' not in service and 'from services.completed_revision_service import' in main
    assert 'UPDATE workout_sessions SET status=? WHERE id=?' not in main[main.index('    def _reopen_completed'):main.index('    def confirm_revise_completed')]
