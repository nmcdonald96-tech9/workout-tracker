from exercise_catalog import *
def test_cable_flye_catalog_and_angle():
    match=find_catalog_match("Cable Chest Fly")
    assert match["catalog"]["name"]=="Cable Flye"
    assert match["requires_confirmation"] is True
    assert angle_response_required("chest_flye")
    assert "Not specified" in get_angle_options("chest_flye")
def test_ambiguous_name_not_silently_mapped():
    assert find_catalog_match("Cable Squeeze") is None
    candidates=rank_catalog_candidates("Cable Squeeze",category="Chest",family="chest_flye",equipment="Cable")
    assert candidates and candidates[0]["score"]>0
    assert all(c["already_confirmed"] is False for c in candidates)
