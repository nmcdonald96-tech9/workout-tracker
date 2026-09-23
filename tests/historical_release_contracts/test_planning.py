import database
def test_blueprint_validation_and_rest_day(monkeypatch):
    monkeypatch.setattr(database,"exercise_exists",lambda name: True)
    monkeypatch.setattr(database,"get_recent_exercise_set_count",lambda name,fallback=2: 2)
    result=database.validate_meso_blueprint({"Monday":["Dumbbell Flye (Flat)"],"Friday":[]},["Monday","Friday"],4)
    assert result["can_stamp"]
    assert result["estimated_weekly_sets"]==2
    assert any(x["code"]=="PLANNED_REST_DAY" for x in result["notices"])
def test_unknown_is_blocking(monkeypatch):
    original=database._planner_exercise_details
    monkeypatch.setattr(database,"_planner_exercise_details",lambda name: None if name=="Unknown Thing" else original(name))
    monkeypatch.setattr(database,"get_recent_exercise_set_count",lambda name,fallback=2: 2)
    result=database.validate_meso_blueprint({"Monday":["Unknown Thing"]},["Monday"],4)
    assert not result["can_stamp"]
    assert any(x["code"]=="UNKNOWN_EXERCISE" for x in result["errors"])
def test_custom_definition_accepts_not_specified():
    result=database.validate_custom_exercise_definition("Cable Squeeze","Chest","chest_flye","Cable","Not specified")
    assert result["valid"] and result["angle_required_response"]