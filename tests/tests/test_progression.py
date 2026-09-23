def configure(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path)
 from database import init_and_seed_db,get_db,invalidate_progression_settings_cache
 init_and_seed_db(); name="Dumbbell Lateral Raise (Super ROM)"
 with get_db() as c: c.execute("UPDATE exercise_dict SET progression_mode='custom',progression_step=NULL,reduction_steps=NULL,rep_ceiling=NULL,reduction_threshold=NULL,max_progress_rpe=NULL,max_progression_weight=20 WHERE name=?",(name,)); c.commit()
 invalidate_progression_settings_cache(name); return name
def test_cap_inherits_step(tmp_path,monkeypatch):
 name=configure(tmp_path,monkeypatch)
 from services.progression_service import get_effective_progression_settings,calculate_set_specific_progression
 settings=get_effective_progression_settings(name,"Isolation","Dumbbell",43,0); assert settings["progression_step"]==2.5 and settings["max_progression_weight"]==20
 targets,diag=calculate_set_specific_progression([(20,15,8,20,15,20,15)],20,15,"Isolation",equipment_type="Dumbbell",exercise_name=name)
 assert targets[0]["w"]==20 and diag[0]["reason_code"]=="LOAD_CEILING_REACHED"
def test_protective_reduction(tmp_path,monkeypatch):
 name=configure(tmp_path,monkeypatch)
 from services.progression_service import calculate_set_specific_progression
 targets,_=calculate_set_specific_progression([(20,5,10,20,15,20,15)],20,15,"Isolation",equipment_type="Dumbbell",exercise_name=name); assert targets[0]["w"]<20