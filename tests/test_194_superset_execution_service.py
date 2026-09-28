import sqlite3
from services.superset_execution_service import SupersetExecutionAction,resolve_post_set_action
def db():
 c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise_group_id TEXT,group_position INTEGER,status TEXT,exercise TEXT,category TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER);CREATE TABLE workout_sets(session_id INTEGER,set_number INTEGER,is_complete INTEGER);');return c
def add(c,sid,g=None,p=1,status='Pending',sets=(0,0)):
 c.execute('INSERT INTO workout_sessions VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,g,p,status,f'E{sid}','Cat',1,'1','Monday',sid))
 for n,d in enumerate(sets,1):c.execute('INSERT INTO workout_sets VALUES(?,?,?)',(sid,n,d))
def test_standalone():
 c=db();add(c,1,sets=(1,0));x=resolve_post_set_action(c,session_id=1,completed_set_number=1);assert x.action==SupersetExecutionAction.ADVANCE_SET and x.target_set_number==2
def test_group_round():
 c=db();add(c,1,'G',1,sets=(1,0));add(c,2,'G',2,sets=(0,0));x=resolve_post_set_action(c,session_id=1,completed_set_number=1);assert x.target_session_id==2
 c.execute('UPDATE workout_sets SET is_complete=1 WHERE session_id=2 AND set_number=1');x=resolve_post_set_action(c,session_id=2,completed_set_number=1);assert x.target_session_id==1 and x.target_set_number==2 and x.round_complete
def test_unequal_and_skipped():
 c=db();add(c,1,'G',1,sets=(1,1,0));add(c,2,'G',2,'Skipped',sets=(0,0));x=resolve_post_set_action(c,session_id=1,completed_set_number=2);assert x.target_session_id==1 and x.target_set_number==3 and x.single_member_remaining
def test_neutral():
 from pathlib import Path
 s=Path('services/superset_execution_service.py').read_text();assert 'import flet' not in s and '.commit(' not in s
def test_no_action():
 c=db();x=resolve_post_set_action(c,session_id=99,completed_set_number=1);assert x.action==SupersetExecutionAction.NO_ACTION
