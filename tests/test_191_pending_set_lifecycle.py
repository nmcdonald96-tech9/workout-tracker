import sqlite3
from services.pending_set_service import (
    PendingSetContext, add_set, copy_previous_set, create_pending_set,
    remove_last_set, restore_drafts, save_pending_sets_atomic,
)

def db():
    c=sqlite3.connect(':memory:')
    c.execute('''CREATE TABLE workout_sets(id INTEGER PRIMARY KEY,session_id INTEGER,set_number INTEGER,weight REAL,reps INTEGER,rpe REAL,rest_seconds INTEGER,target_weight REAL,target_reps INTEGER,normal_target_weight REAL,normal_target_reps INTEGER,completed_at TEXT,is_complete INTEGER,weight_source TEXT,reps_source TEXT)''')
    return c

def context():
    targets=({'w':100,'r':10},{'w':105,'r':8})
    return PendingSetContext(7,targets,targets)

def test_create_add_remove_and_copy():
    first=create_pending_set({'w':100,'r':10}); assert first['w']=='100' and first['r_source']=='target'
    rows=add_set([dict(first,done=True,rpe='8.0')],{'w':105,'r':8})
    copied,index=copy_previous_set(rows); assert index==1 and copied[1]['w']=='100' and copied[1]['rpe']==''
    assert len(remove_last_set(copied))==1

def test_atomic_save_and_restart_restoration_preserve_ownership_and_rpe():
    c=db(); drafts=[{'w':'100','r':'10','rpe':'8.5','done':False,'completed_at':None,'w_source':'user','r_source':'weight_derived'}]
    assert save_pending_sets_atomic(c,context(),drafts,normalize_rpe=lambda x:x if x in ('','8.5') else None,rest_seconds_for=lambda *a:None)
    row=c.execute('SELECT weight,reps,rpe,rest_seconds,completed_at,is_complete,weight_source,reps_source FROM workout_sets').fetchone()
    restored=restore_drafts([row]); assert restored[0]['rpe']=='8.5' and restored[0]['w_source']=='user' and restored[0]['r_source']=='weight_derived'

def test_invalid_partial_input_does_not_destroy_last_durable_draft():
    c=db(); c.execute("INSERT INTO workout_sets(session_id,set_number,weight,reps) VALUES(7,1,90,9)"); c.commit()
    ok=save_pending_sets_atomic(c,context(),[{'w':'1.','r':'bad','rpe':'','done':False}],normalize_rpe=lambda x:x,rest_seconds_for=lambda *a:None)
    assert ok is False
    assert c.execute('SELECT weight,reps FROM workout_sets').fetchone()==(90.0,9)

def test_empty_trailing_draft_is_not_persisted():
    c=db(); rows=[{'w':'100','r':'10','rpe':'','done':False},{'w':'','r':'','rpe':'','done':False}]
    assert save_pending_sets_atomic(c,context(),rows,normalize_rpe=lambda x:None,rest_seconds_for=lambda *a:None)
    assert c.execute('SELECT COUNT(*) FROM workout_sets').fetchone()[0]==1
