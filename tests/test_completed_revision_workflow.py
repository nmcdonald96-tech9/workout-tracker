def test_revision_cancel_restores_original_completed_rows(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);import database;database.DB_PATH=str(tmp_path/"revision.db");database.init_and_seed_db()
 with database.get_db() as c:
  sid=c.execute("INSERT INTO workout_sessions(date,exercise,category,day_of_week,week,target_weight,target_reps,status,movement_type,meso_number) VALUES('2026-09-21','Bench Press (Medium Grip)','Chest','Monday','1',100,10,'Completed','Compound',1)").lastrowid;c.execute("INSERT INTO workout_sets(session_id,set_number,weight,reps,rpe,target_weight,target_reps,normal_target_weight,normal_target_reps,completed_at,is_complete) VALUES(?,?,?,?,?,?,?,?,?,?,1)",(sid,1,100,10,8.5,100,10,100,10,'2026-09-21T10:00:00'));c.commit()
 snap=database.completed_exercise_revision_snapshot(sid)
 with database.get_db() as c:c.execute("UPDATE workout_sessions SET status='Pending' WHERE id=?",(sid,));c.execute("UPDATE workout_sets SET weight=120,reps=5,rpe=10 WHERE session_id=?",(sid,));c.commit()
 database.restore_completed_exercise_revision(sid,snap)
 with database.get_db() as c:assert c.execute("SELECT status FROM workout_sessions WHERE id=?",(sid,)).fetchone()[0]=='Completed';assert c.execute("SELECT weight,reps,rpe FROM workout_sets WHERE session_id=?",(sid,)).fetchone()==(100.0,10,8.5)
def test_revision_summary():
 from database import revision_change_summary
 o={"sets":[(1,100.0,10,8.0,None,100.0,10,100.0,10,None,1,None,None,None,None)]};x=revision_change_summary(o,[(105.0,9,8.5),(105.0,8,9.0)]);assert "set 1:" in x and "set 2 added" in x