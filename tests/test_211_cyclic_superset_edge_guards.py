import sqlite3
from pathlib import Path
from services.superset_execution_service import resolve_post_set_action, select_cyclic_target
SOURCE=Path("main.py").read_text(encoding="utf-8")
def db():
 c=sqlite3.connect(":memory:");c.executescript("CREATE TABLE workout_sessions(id INTEGER PRIMARY KEY,exercise_group_id TEXT,group_position INTEGER,status TEXT,exercise TEXT,category TEXT,meso_number INTEGER,week TEXT,day_of_week TEXT,workout_order INTEGER);CREATE TABLE workout_sets(session_id INTEGER,set_number INTEGER,is_complete INTEGER);");return c
def add(c,sid,pos,completed=(),total=3,status="Pending"):
 c.execute("INSERT INTO workout_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",(sid,"G",pos,status,f"A{pos}","Group",1,"1","Monday",pos))
 for n in range(1,total+1):c.execute("INSERT INTO workout_sets VALUES(?,?,?)",(sid,n,int(n in completed)))
def block(a,b):
 i=SOURCE.index(a);return SOURCE[i:SOURCE.index(b,i)]
def test_preview_treats_source_set_as_hypothetically_complete():
 c=db();add(c,1,1,completed=(1,));add(c,2,2,completed=(1,));add(c,3,3);x=resolve_post_set_action(c,session_id=3,completed_set_number=1);assert (x.target_session_id,x.target_set_number)==(1,2)
def test_random_order_catches_up_earliest_incomplete_round():
 x=select_cyclic_target([(1,"A1","G",1,2),(2,"A2","G",2,1),(3,"A3","G",3,3)],source_position=3,completed_set_number=2);assert (x[0],x[4])==(2,1)
def test_normal_a2_cycle_is_unchanged():
 x=select_cyclic_target([(1,"A1","G",1,1),(2,"A2","G",2,2),(3,"A3","G",3,1)],source_position=2,completed_set_number=1);assert x[0]==3
def test_completion_resolves_before_log_then_applies_once():
 b=block("    def make_set_done_handler(","    def make_live_updater(");assert "group_instruction = self.app.resolve_group_flow" in b;assert "self.on_save(None, suppress_refresh=execution_available)" in b;assert b.index("group_instruction =")<b.index("self.on_save(None, suppress_refresh=execution_available)")
def test_on_save_can_suppress_competing_structural_refresh():
 b=block("    def on_save(self, ev, suppress_refresh=False):","    def __init__(self, page: ft.Page):");assert "if not suppress_refresh:" in b
def test_group_flow_resolution_and_application_are_separate():
 b=block("    def resolve_group_flow(","    def activate_exercise(");assert "def apply_group_flow_instruction" in b;assert "self.pending_scroll_key = exercise_anchor_key" in b;assert b.count("self.rebuild_entire_display()") == 1
