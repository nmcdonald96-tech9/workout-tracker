def test_ceiling(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path)
 from database import init_and_seed_db,get_db,invalidate_progression_settings_cache,calculate_set_specific_progression
 init_and_seed_db(); n='Dumbbell Lateral Raise (Super ROM)'
 with get_db() as c:c.execute("UPDATE exercise_dict SET progression_mode='custom',progression_step=2.5,reduction_steps=1,rep_ceiling=15,reduction_threshold=.7,max_progress_rpe=9.5,max_progression_weight=20 WHERE name=?",(n,));c.commit()
 invalidate_progression_settings_cache(n)
 t,d=calculate_set_specific_progression([(20,15,8,20,15,20,15)],20,15,'Isolation',equipment_type='Dumbbell',exercise_name=n)
 assert t[0]['w']==20 and d[0]['reason_code']=='LOAD_CEILING_REACHED'
