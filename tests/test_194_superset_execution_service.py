import sqlite3
from pathlib import Path
from services.superset_execution_service import SupersetExecutionAction, resolve_post_set_action, resolve_next_group_step
ROOT=Path(__file__).resolve().parents[1]
def db():
 c=sqlite3.connect(':memory:');c.executescript("""CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise_group_id TEXT,group_position INTEGER,status TEXT,exercise TEXT,category TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER);CREATE TABLE workout_sets(session_id INTEGER,set_number INTEGER,is_complete INTEGER);""");return c
def session(c,sid,group=None,pos=1,status='Pending',sets=(0,0),exercise=None):
 c.execute("INSERT INTO workout_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",(sid,group,pos,status,exercise or f'E{sid}','Cat',1,'1','Monday',sid))
 for n,done in enumerate(sets,1):c.execute("INSERT INTO workout_sets VALUES(?,?,?)",(sid,n,done))
def test_standalone_next_and_complete():
 c=db();session(c,1,sets=(1,0));x=resolve_post_set_action(c,session_id=1,completed_set_number=1);assert x.action==SupersetExecutionAction.ADVANCE_SET and x.target_set_number==2
 c.execute('UPDATE workout_sets SET is_complete=1');x=resolve_post_set_action(c,session_id=1,completed_set_number=2);assert x.action==SupersetExecutionAction.READY_TO_LOG_EXERCISE
def test_three_member_round_and_legacy_shape():
 c=db();session(c,1,'G',1,sets=(1,0));session(c,2,'G',2,sets=(0,0));session(c,3,'G',3,sets=(0,0))
 x=resolve_post_set_action(c,session_id=1,completed_set_number=1);assert x.action==SupersetExecutionAction.ADVANCE_GROUP and x.target_session_id==2 and not x.round_complete
 c.execute('UPDATE workout_sets SET is_complete=1 WHERE session_id IN (2,3) AND set_number=1')
 x=resolve_post_set_action(c,session_id=3,completed_set_number=1);assert x.target_session_id==1 and x.target_set_number==2 and x.round_complete
 assert resolve_next_group_step(c,3,1)['pending_set']==2
def test_unequal_sets_never_targets_missing_set():
 c=db();session(c,1,'G',1,sets=(1,1,0));session(c,2,'G',2,sets=(1,1))
 x=resolve_post_set_action(c,session_id=2,completed_set_number=2);assert x.target_session_id==1 and x.target_set_number==3
def test_skipped_completed_bypassed_and_single_remaining():
 c=db();session(c,1,'G',1,sets=(1,0));session(c,2,'G',2,'Skipped',sets=(0,0));session(c,3,'G',3,'Completed',sets=(1,1))
 x=resolve_post_set_action(c,session_id=1,completed_set_number=1);assert x.action==SupersetExecutionAction.ADVANCE_SET and x.target_session_id==1 and x.single_member_remaining
def test_group_complete_and_no_action():
 c=db();session(c,1,'G',1,sets=(1,));x=resolve_post_set_action(c,session_id=1,completed_set_number=1);assert x.action==SupersetExecutionAction.READY_TO_LOG_GROUP and x.group_complete
 y=resolve_post_set_action(c,session_id=99,completed_set_number=1);assert y.action==SupersetExecutionAction.NO_ACTION
def test_service_is_ui_and_transaction_neutral():
 source=(ROOT/'services/superset_execution_service.py').read_text();assert 'import flet' not in source and '.commit(' not in source and '.rollback(' not in source
def test_database_is_compatibility_wrapper_and_main_uses_typed_service():
 d=(ROOT/'database.py').read_text();m=(ROOT/'main.py').read_text();assert 'Compatibility wrapper over the 1.94' in d
 assert 'resolve_post_set_action' in m and 'SupersetExecutionAction.ADVANCE_GROUP' in m
def test_193_refresh_fixes_retained():
 m=(ROOT/'main.py').read_text();assert 'refresh_weight_edit_feedback' in m and 'request_set_structure_refresh("add_set")' in m and 'superset_assignment_changed' in m
def test_release_contract():
 c=(ROOT/'constants.py').read_text();assert 'APP_VERSION = "1.94.0"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c
