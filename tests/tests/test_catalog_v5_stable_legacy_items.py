from exercise_catalog import CATALOG_VERSION, resolve_catalog_exercise, resolve_exercise_metadata

EXPECTED = {
    "Arnold Press": ("arnold_press", "Dumbbell", "vertical_press"),
    "Dumbbell Leaning Lateral Raise": ("dumbbell_leaning_lateral_raise", "Dumbbell", "lateral_raise"),
    "Hip Abduction Machine": ("hip_abduction_machine", "Machine", "hip_abduction"),
    "Hip Squeeze Adduction Machine": ("hip_adduction_machine", "Machine", "hip_adduction"),
    "Overhand EZ Bar Curl": ("overhand_ez_bar_curl", "Barbell", "elbow_flexion"),
    "Single Arm Dumbbell Row": ("single_arm_dumbbell_row", "Dumbbell", "horizontal_row"),
}


def test_catalog_v5_contains_all_six_legacy_movements():
    assert CATALOG_VERSION == 5
    for name, (catalog_id, equipment, family) in EXPECTED.items():
        item = resolve_catalog_exercise(name)
        assert item["id"] == catalog_id
        assert item["equipment"] == equipment
        assert item["family"] == family


def test_useful_aliases_resolve_to_the_same_stable_ids():
    assert resolve_catalog_exercise("Arnold Shoulder Press")["id"] == "arnold_press"
    assert resolve_catalog_exercise("Hip Adduction Machine")["id"] == "hip_adduction_machine"
    assert resolve_catalog_exercise("EZ Bar Reverse Curl")["id"] == "overhand_ez_bar_curl"
    assert resolve_catalog_exercise("One-Arm Dumbbell Row")["id"] == "single_arm_dumbbell_row"


def test_equipment_runtime_behavior_is_correct():
    assert resolve_exercise_metadata("Arnold Press")["equipment"] == "Dumbbell"
    assert resolve_exercise_metadata("Dumbbell Leaning Lateral Raise")["equipment"] == "Dumbbell"
    reverse = resolve_exercise_metadata("Overhand EZ Bar Curl")
    assert reverse["plate_loaded"] is True
    assert reverse["bar_weight"] == 15.0


def test_exact_linking_reaches_all_legacy_rows_without_adding_duplicate_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import database
    database.DB_PATH = str(tmp_path / "catalog-v5.db")
    database.init_and_seed_db()
    legacy_names = list(EXPECTED)
    with database.get_db() as conn:
        conn.execute("DELETE FROM exercise_dict")
        for name in legacy_names:
            conn.execute("INSERT INTO exercise_dict(name, category, movement_family, equipment, is_custom) VALUES(?,?,?,?,0)", (name, "General", "Legacy", "Legacy"))
        conn.commit()
    linked = database.auto_link_exact_uniform_exercises()
    assert set(linked) == set(legacy_names)
    with database.get_db() as conn:
        rows = conn.execute("SELECT name, catalog_id, equipment FROM exercise_dict ORDER BY name").fetchall()
    assert len(rows) == 6
    assert all(catalog_id and equipment != "Legacy" for _, catalog_id, equipment in rows)