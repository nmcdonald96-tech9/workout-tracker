from pathlib import Path
from services.intra_session_autoregulation_service import *

def row(w=100,r=10,rpe='',done=False,ws='target',rs='target'):
 return {'w':str(w),'r':str(r),'rpe':str(rpe),'done':done,'w_source':ws,'r_source':rs}

def test_trigger_and_readiness_isolation():
 rows=[row(rpe=9.5,done=True),row(),row()];targets=[{'w':100,'r':10}]*3
 assert evaluate_fatigue_advisory(rows=rows,trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell')
 regulated=[{'w':95,'r':10}]*3
 assert evaluate_fatigue_advisory(rows=rows,trigger_index=0,targets=regulated,normal_targets=targets,reduction_threshold=.7,equipment='Barbell') is None

def test_load_reduction_real_step_and_never_increases_reps():
 rows=[row(done=True,rpe=10),row(165,6,rs='weight_derived'),row(50,10)]
 out,_,changed=apply_action(rows,action='reduce_load',trigger_index=0,targets=[{'w':135,'r':12}]*3,equipment='Barbell')
 assert float(out[1]['w']) < 165 and int(out[1]['r']) == 6 and out[1]['r_source']=='user'
 assert float(out[2]['w']) == 45 and changed==(1,2)

def test_dumbbell_and_noop_load_rules():
 assert reduced_weight(30,'Dumbbell')==25
 assert reduced_weight(0,'Bodyweight') is None
 assert reduced_weight(5,'Barbell',min_weight=5) is None

def test_rep_reduction_and_scratch_safety():
 rows=[row(done=True,rpe=10),row(),row()]
 out,_,_=apply_action(rows,action='reduce_reps',trigger_index=0,targets=[{'w':100,'r':10}]*3,equipment='Barbell')
 assert [x['r'] for x in out[1:]]==['9','9'] and all(x['r_source']=='user' for x in out[1:])
 adv=evaluate_fatigue_advisory(rows=rows,trigger_index=0,targets=[{'w':100,'r':10}]*3,normal_targets=[{'w':100,'r':10}]*3,reduction_threshold=.7,equipment='Barbell')
 assert 'scratch_final' in adv.actions
 assert 'scratch_final' not in evaluate_fatigue_advisory(rows=rows[:2],trigger_index=0,targets=[{'w':100,'r':10}]*2,normal_targets=[{'w':100,'r':10}]*2,reduction_threshold=.7,equipment='Barbell').actions

def test_main_wiring_focus_sync_revision_and_reopen():
 s=Path('main.py').read_text()
 for token in ('_fatigue_advisories','_fatigue_handled_triggers','_fatigue_undo_snapshots','_committed_weight_values[key]=str','_reps_focus_sync_targets.discard(key)','_reps_field_sync_rev[key]','discard((self.db_id, set_idx))','self.db_id in self.app.completed_revision_sessions'): assert token in s
 assert 'calculate_e1rm' not in Path('services/intra_session_autoregulation_service.py').read_text()

def test_version_schema_unchanged():
 c=Path('constants.py').read_text();assert 'APP_VERSION = "2.1.0"' in c and 'DATABASE_SCHEMA_VERSION = 20' in c


def test_noop_rep_action_and_keep_only_advisory_are_omitted():
 rows=[row(done=True,rpe=10),row(w=0,r=1)]
 adv=evaluate_fatigue_advisory(rows=rows,trigger_index=0,targets=[{'w':0,'r':10},{'w':0,'r':1}],normal_targets=[{'w':0,'r':10},{'w':0,'r':1}],reduction_threshold=.7,equipment='Bodyweight')
 assert adv is None

def test_reason_includes_one_based_set_number_and_trigger_matrix():
 targets=[{'w':100,'r':10}]*3
 assert evaluate_fatigue_advisory(rows=[row(rpe=9.5,done=True),row(),row()],trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell').reason.startswith('Set 1')
 assert evaluate_fatigue_advisory(rows=[row(rpe=10,done=True),row(),row()],trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell')
 assert evaluate_fatigue_advisory(rows=[row(rpe=9,done=True),row(),row()],trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell') is None
 assert evaluate_fatigue_advisory(rows=[row(r=5,rpe=8,done=True),row(),row()],trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell')
 assert evaluate_fatigue_advisory(rows=[row(r=9,rpe=8,done=True),row(),row()],trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell') is None

def test_deload_revision_final_and_duplicate_suppression():
 rows=[row(rpe=10,done=True),row()];targets=[{'w':100,'r':10}]*2
 base=dict(rows=rows,trigger_index=0,targets=targets,normal_targets=targets,reduction_threshold=.7,equipment='Barbell')
 assert evaluate_fatigue_advisory(**base,deload=True) is None
 assert evaluate_fatigue_advisory(**base,revision=True) is None
 assert evaluate_fatigue_advisory(**base,handled=True) is None
 assert evaluate_fatigue_advisory(rows=[row(rpe=10,done=True)],trigger_index=0,targets=targets[:1],normal_targets=targets[:1],reduction_threshold=.7,equipment='Barbell') is None

def test_reconcile_pending_draft_preserves_clamped_user_reps_after_rebuild():
 from services.target_ownership_service import reconcile_pending_draft
 rows=[row(done=True,rpe=10),row(165,6,rs='weight_derived')]
 out,original,_=apply_action(rows,action='reduce_load',trigger_index=0,targets=[{'w':135,'r':12}]*2,equipment='Barbell')
 rebuilt=reconcile_pending_draft(out[1],{'w':135,'r':12},is_complete=False)
 assert rebuilt['r']=='6' and rebuilt['r_source']=='user'
 restored=[dict(x) for x in original]
 assert restored[1]['w']=='165' and restored[1]['r']=='6' and restored[1]['r_source']=='weight_derived'

def test_metadata_cleanup_and_stale_focus_contracts():
 s=Path('main.py').read_text()
 for token in ('resolve_exercise_metadata(self.exercise)','get_user_age(), get_user_progression_profile()','def clear_fatigue_session_state','_committed_weight_values.pop(key, None)','def repeat_previous_set','def confirm_delete'): assert token in s


def test_next_completion_dismisses_prior_advisory_before_reevaluation():
    source = Path("main.py").read_text()
    start = source.index("            if requested_value and autosaved:")
    end = source.index("            elif not requested_value:", start)
    completion_block = source[start:end]

    dismiss = "self.app._fatigue_advisories.pop(self.db_id, None)"
    reevaluate = "self.evaluate_fatigue_after_save(set_idx)"

    assert dismiss in completion_block
    assert reevaluate in completion_block
    assert completion_block.index(dismiss) < completion_block.index(reevaluate)
