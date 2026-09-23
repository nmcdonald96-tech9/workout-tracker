from services.target_ownership_service import TARGET, USER, WEIGHT_DERIVED, apply_direct_edit, apply_weight_derived_reps, clear_override, ownership_summary, reconcile_pending_draft

def test_target_fields_follow_current_target():
 d={"w":"145","r":"16","w_source":TARGET,"r_source":TARGET};x=reconcile_pending_draft(d,{"w":130,"r":12});assert (x["w"],x["r"])==("130","12")

def test_user_and_derived_survive():
 d={"w":"200","r":"8","w_source":USER,"r_source":WEIGHT_DERIVED};x=reconcile_pending_draft(d,{"w":130,"r":12});assert (x["w"],x["r"],x["r_source"])==("200","8",WEIGHT_DERIVED)

def test_same_number_direct_edit_is_user():
 assert apply_direct_edit({"w":"145","w_source":TARGET},"w","145")["w_source"]==USER

def test_derived_then_manual():
 x=apply_weight_derived_reps({},200,8);assert x["r_source"]==WEIGHT_DERIVED;x=apply_direct_edit(x,"r","9");assert x["r_source"]==USER

def test_clear_restores_target():
 x=clear_override({"w":"200","w_source":USER},"w",{"w":145,"r":16});assert (x["w"],x["w_source"])==("145",TARGET)

def test_completed_not_reconciled():
 d={"w":"200","r":"8","w_source":TARGET,"r_source":TARGET};x=reconcile_pending_draft(d,{"w":130,"r":12},is_complete=True);assert (x["w"],x["r"])==("200","8")

def test_explanations():
 n={"w":145,"r":16};t={"w":130,"r":12};assert "Readiness-adjusted" in ownership_summary({"w_source":TARGET,"r_source":TARGET},t,n);assert "User override" in ownership_summary({"w_source":USER},t,n)