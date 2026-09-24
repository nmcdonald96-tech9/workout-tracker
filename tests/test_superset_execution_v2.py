import importlib


def setup_group(tmp_path, monkeypatch, set_counts=(2,2,2), statuses=None):
    monkeypatch.chdir(tmp_path)
    import database
    database.DB_PATH=str(tmp_path/"group.db")
    database.init_and_seed_db()
    statuses=statuses or [database.STATUS_PENDING]*len(set_counts)
    ids=[]
    with database.get_db() as c:
        for position,(count,status) in enumerate(zip(set_counts,statuses),1):
            sid=c.execute("INSERT INTO workout_sessions(date,exercise,category,day_of_week,week,target_weight,target_reps,status,movement_type,meso_number,exercise_group_id,group_position,workout_order) VALUES('2026-09-21',?,?,?,?,?,?,?,?,?,?,?,?)",(f'Exercise {position}','General','Monday','1',100,10,status,'Compound',1,'G1',position,position)).lastrowid
            ids.append(sid)
            for number in range(1,count+1):
                c.execute("INSERT INTO workout_sets(session_id,set_number,weight,reps,rpe,is_complete) VALUES(?,?,?,?,?,0)",(sid,number,100,10,8))
        c.commit()
    return database,ids


def complete(database,sid,set_number):
    with database.get_db() as c:c.execute("UPDATE workout_sets SET is_complete=1 WHERE session_id=? AND set_number=?",(sid,set_number));c.commit()


def test_three_member_round_order(tmp_path,monkeypatch):
    db,ids=setup_group(tmp_path,monkeypatch)
    complete(db,ids[0],1)
    nxt=db.resolve_next_group_step(1,'1','Monday',ids[0],1)
    assert (nxt['session_id'],nxt['pending_set'],nxt['round_complete'])==(ids[1],1,False)
    complete(db,ids[1],1);complete(db,ids[2],1)
    nxt=db.resolve_next_group_step(1,'1','Monday',ids[2],1)
    assert (nxt['session_id'],nxt['pending_set'],nxt['round_complete'])==(ids[0],2,True)


def test_unequal_sets_do_not_open_missing_set(tmp_path,monkeypatch):
    db,ids=setup_group(tmp_path,monkeypatch,set_counts=(3,2))
    for sid in ids:
        complete(db,sid,1);complete(db,sid,2)
    nxt=db.resolve_next_group_step(1,'1','Monday',ids[1],2)
    assert nxt['session_id']==ids[0] and nxt['pending_set']==3
    complete(db,ids[0],3)
    assert db.resolve_next_group_step(1,'1','Monday',ids[0],3) is None


def test_skipped_member_is_bypassed(tmp_path,monkeypatch):
    db,ids=setup_group(tmp_path,monkeypatch,statuses=['Pending','Skipped','Pending'])
    complete(db,ids[0],1)
    nxt=db.resolve_next_group_step(1,'1','Monday',ids[0],1)
    assert nxt['session_id']==ids[2]
    assert nxt['remaining_members']==2


def test_one_remaining_member_continues_normally(tmp_path,monkeypatch):
    db,ids=setup_group(tmp_path,monkeypatch,statuses=['Pending','Completed'])
    complete(db,ids[0],1)
    nxt=db.resolve_next_group_step(1,'1','Monday',ids[0],1)
    assert nxt['session_id']==ids[0] and nxt['pending_set']==2
    assert nxt['single_member_remaining'] is True
