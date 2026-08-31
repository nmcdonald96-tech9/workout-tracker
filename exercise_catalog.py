"""IronCycle built-in exercise knowledge catalog.

Catalog identity is separate from a user's display name. This module contains
static, deterministic data only and has no UI, database, or network dependency.
"""

ANGLE_NOT_SPECIFIED = "Not specified"
ANGLE_OPTIONS = {
    "chest_flye": ["Flat / Mid", "Low-to-High", "High-to-Low", "Other", ANGLE_NOT_SPECIFIED],
    "horizontal_press": ["Flat / Mid", "Low Incline", "High Incline", "Decline", "Other", ANGLE_NOT_SPECIFIED],
    "vertical_press": ["Upright", "High Incline", "Other", ANGLE_NOT_SPECIFIED],
}

# Required catalog fields: id, name, category, family, movement_type, equipment.
# Angle is conditional. When applicable, Not specified is always valid.
BUILTIN_EXERCISE_CATALOG = [
    {"id":"bench_press_barbell_flat","name":"Barbell Bench Press","aliases":["Flat Barbell Bench Press","Bench Press (Medium Grip)"],"category":"Chest","family":"horizontal_press","pattern":"Horizontal Press","movement_type":"Compound","equipment":"Barbell","angle":"Flat / Mid"},
    {"id":"bench_press_barbell_incline","name":"Incline Barbell Bench Press","aliases":[],"category":"Chest","family":"horizontal_press","pattern":"Incline Press","movement_type":"Compound","equipment":"Barbell","angle":"Low Incline"},
    {"id":"chest_press_dumbbell_flat","name":"Dumbbell Press (Flat)","aliases":["Flat Dumbbell Press"],"category":"Chest","family":"horizontal_press","pattern":"Horizontal Press","movement_type":"Compound","equipment":"Dumbbell","angle":"Flat / Mid"},
    {"id":"chest_press_dumbbell_low_incline","name":"Dumbbell Press (Low Incline)","aliases":[],"category":"Chest","family":"horizontal_press","pattern":"Incline Press","movement_type":"Compound","equipment":"Dumbbell","angle":"Low Incline"},
    {"id":"chest_press_dumbbell_high_incline","name":"Dumbbell Press (High Incline)","aliases":[],"category":"Chest","family":"horizontal_press","pattern":"Incline Press","movement_type":"Compound","equipment":"Dumbbell","angle":"High Incline"},
    {"id":"chest_flye_dumbbell_flat","name":"Dumbbell Flye (Flat)","aliases":["Flat Dumbbell Flye","Dumbbell Chest Fly"],"category":"Chest","family":"chest_flye","pattern":"Chest Isolation","movement_type":"Isolation","equipment":"Dumbbell","angle":"Flat / Mid"},
    {"id":"chest_flye_cable_mid","name":"Cable Flye","aliases":["Cable Chest Fly","Standing Cable Fly","Cable Pec Fly"],"category":"Chest","family":"chest_flye","pattern":"Chest Isolation","movement_type":"Isolation","equipment":"Cable","angle":"Flat / Mid"},
    {"id":"chest_flye_cable_low_high","name":"Low-to-High Cable Flye","aliases":["Low Cable Fly"],"category":"Chest","family":"chest_flye","pattern":"Chest Isolation","movement_type":"Isolation","equipment":"Cable","angle":"Low-to-High"},
    {"id":"chest_flye_cable_high_low","name":"High-to-Low Cable Flye","aliases":["High Cable Fly"],"category":"Chest","family":"chest_flye","pattern":"Chest Isolation","movement_type":"Isolation","equipment":"Cable","angle":"High-to-Low"},
    {"id":"chest_flye_machine","name":"Machine Chest Fly","aliases":["Pec Deck","Pec Fly Machine"],"category":"Chest","family":"chest_flye","pattern":"Chest Isolation","movement_type":"Isolation","equipment":"Machine","angle":"Not specified"},
    {"id":"row_dumbbell_bilateral","name":"Dumbbell Row (2-Arm)","aliases":[],"category":"Back","family":"horizontal_row","pattern":"Horizontal Row","movement_type":"Compound","equipment":"Dumbbell"},
    {"id":"row_dumbbell_incline_supported","name":"Dumbbell Row (2-Arm, Incline)","aliases":["Chest-Supported Dumbbell Row"],"category":"Back","family":"horizontal_row","pattern":"Horizontal Row","movement_type":"Compound","equipment":"Dumbbell"},
    {"id":"row_cable_flexion","name":"Cable Flexion Row","aliases":[],"category":"Back","family":"horizontal_row","pattern":"Horizontal Row","movement_type":"Compound","equipment":"Cable"},
    {"id":"row_cable_seated","name":"Seated Cable Row","aliases":["Cable Row"],"category":"Back","family":"horizontal_row","pattern":"Horizontal Row","movement_type":"Compound","equipment":"Cable"},
    {"id":"pulldown_cable_standard","name":"Pulldown (Normal Grip)","aliases":["Lat Pulldown"],"category":"Back","family":"vertical_pull","pattern":"Vertical Pull","movement_type":"Compound","equipment":"Cable"},
    {"id":"pulldown_straight_arm","name":"Pulldown (Straight Arm)","aliases":["Straight-Arm Pulldown"],"category":"Back","family":"pullover","pattern":"Pullover","movement_type":"Isolation","equipment":"Cable"},
    {"id":"pullup_wide","name":"Pullup (Wide Grip)","aliases":["Wide-Grip Pull-Up"],"category":"Back","family":"vertical_pull","pattern":"Vertical Pull","movement_type":"Compound","equipment":"Bodyweight"},
    {"id":"lateral_raise_dumbbell","name":"Dumbbell Lateral Raise","aliases":["Dumbbell Lateral Raise (Super ROM)"],"category":"Shoulders","family":"lateral_raise","pattern":"Lateral Isolation","movement_type":"Isolation","equipment":"Dumbbell"},
    {"id":"lateral_raise_cable","name":"Cable Lateral Raise","aliases":["Cable Leaning Lateral Raise"],"category":"Shoulders","family":"lateral_raise","pattern":"Lateral Isolation","movement_type":"Isolation","equipment":"Cable"},
    {"id":"facepull_cable_rope","name":"Cable Rope Facepull","aliases":["Rope Face Pull"],"category":"Shoulders","family":"rear_delt","pattern":"Rear Delt","movement_type":"Isolation","equipment":"Cable"},
    {"id":"rear_delt_cable","name":"Cable Rear Delt Flye","aliases":["Freemotion Rear Delt Flyes (Paused)"],"category":"Shoulders","family":"rear_delt","pattern":"Rear Delt","movement_type":"Isolation","equipment":"Cable"},
    {"id":"shoulder_press_smith_seated","name":"Smith Machine Shoulder Press (Seated)","aliases":[],"category":"Shoulders","family":"vertical_press","pattern":"Vertical Press","movement_type":"Compound","equipment":"Machine","angle":"Upright"},
    {"id":"shrug_smith","name":"Smith Machine Shrug","aliases":[],"category":"Shoulders","family":"shrug","pattern":"Upper Trap","movement_type":"Isolation","equipment":"Machine"},
    {"id":"shrug_dumbbell","name":"Dumbbell Shrug","aliases":[],"category":"Shoulders","family":"shrug","pattern":"Upper Trap","movement_type":"Isolation","equipment":"Dumbbell"},
    {"id":"squat_barbell_high_bar","name":"Barbell Squat (High Bar)","aliases":["High-Bar Squat"],"category":"Quads","family":"squat","pattern":"Squat Pattern","movement_type":"Compound","equipment":"Barbell"},
    {"id":"deadlift_barbell_conventional","name":"Deadlift","aliases":["Conventional Deadlift"],"category":"Hamstrings","family":"hinge","pattern":"Hinge","movement_type":"Compound","equipment":"Barbell"},
    {"id":"deadlift_dumbbell_stiff_leg","name":"Dumbbell Stiff Legged Deadlift","aliases":["Dumbbell Stiff-Leg Deadlift"],"category":"Hamstrings","family":"hinge","pattern":"Hinge","movement_type":"Compound","equipment":"Dumbbell"},
    {"id":"hack_squat_machine","name":"Hack Squat","aliases":[],"category":"Quads","family":"squat","pattern":"Squat Pattern","movement_type":"Compound","equipment":"Machine"},
    {"id":"leg_press_machine","name":"Leg Press","aliases":[],"category":"Quads","family":"squat","pattern":"Squat Pattern","movement_type":"Compound","equipment":"Machine"},
    {"id":"leg_extension_machine","name":"Leg Extension","aliases":[],"category":"Quads","family":"knee_extension","pattern":"Quad Isolation","movement_type":"Isolation","equipment":"Machine"},
    {"id":"leg_curl_single_machine","name":"Single-Leg Leg Curl","aliases":[],"category":"Hamstrings","family":"knee_flexion","pattern":"Hamstring Isolation","movement_type":"Isolation","equipment":"Machine"},
    {"id":"reverse_hyper","name":"Reverse Hyper","aliases":["Reverse Hyperextension"],"category":"Glutes","family":"hip_extension","pattern":"Glute Isolation","movement_type":"Isolation","equipment":"Machine"},
    {"id":"walking_lunge_glute","name":"Walking Lunges (Glute-Focused)","aliases":["Walking Lunge"],"category":"Glutes","family":"lunge","pattern":"Lunge","movement_type":"Compound","equipment":"Dumbbell"},
    {"id":"bodyweight_squat_partial","name":"Bodyweight Squat (2/3)","aliases":[],"category":"Quads","family":"squat","pattern":"Squat Pattern","movement_type":"Isolation","equipment":"Bodyweight"},
    {"id":"calf_raise_stair_single","name":"Stair Calves (Single Leg)","aliases":["Single-Leg Stair Calf Raise"],"category":"Calves","family":"calf_raise","pattern":"Calf Isolation","movement_type":"Isolation","equipment":"Bodyweight"},
    {"id":"calf_raise_machine","name":"Calf Machine","aliases":["Machine Calf Raise"],"category":"Calves","family":"calf_raise","pattern":"Calf Isolation","movement_type":"Isolation","equipment":"Machine"},
    {"id":"curl_cable_ez","name":"Cable Curl (EZ Bar)","aliases":[],"category":"Biceps","family":"elbow_flexion","pattern":"Elbow Flexion","movement_type":"Isolation","equipment":"Cable"},
    {"id":"curl_ez_wide","name":"EZ Bar Curl (Wide Grip)","aliases":[],"category":"Biceps","family":"elbow_flexion","pattern":"Elbow Flexion","movement_type":"Isolation","equipment":"Barbell"},
    {"id":"curl_concentration","name":"Concentration Curl","aliases":[],"category":"Biceps","family":"elbow_flexion","pattern":"Elbow Flexion","movement_type":"Isolation","equipment":"Dumbbell"},
    {"id":"triceps_pushdown_bar","name":"Cable Triceps Pushdown (Bar)","aliases":["Cable Pushdown"],"category":"Triceps","family":"triceps_pushdown","pattern":"Elbow Extension","movement_type":"Isolation","equipment":"Cable"},
    {"id":"triceps_extension_cable_overhead","name":"Cable Overhead Triceps Extension","aliases":[],"category":"Triceps","family":"overhead_triceps_extension","pattern":"Elbow Extension","movement_type":"Isolation","equipment":"Cable"},
    {"id":"triceps_extension_dumbbell_overhead","name":"Dumbbell Overhead Extension","aliases":[],"category":"Triceps","family":"overhead_triceps_extension","pattern":"Elbow Extension","movement_type":"Isolation","equipment":"Dumbbell"},
    {"id":"triceps_kickback_cable","name":"Cable Tricep Kickback","aliases":[],"category":"Triceps","family":"triceps_kickback","pattern":"Elbow Extension","movement_type":"Isolation","equipment":"Cable"},
    {"id":"wrist_curl_barbell_standing","name":"Barbell Standing Wrist Curl","aliases":[],"category":"Forearms","family":"wrist_flexion","pattern":"Wrist Flexion","movement_type":"Isolation","equipment":"Barbell"},
    {"id":"candlestick_modified","name":"Modified Candlestick","aliases":[],"category":"Abs","family":"trunk_flexion","pattern":"Trunk Flexion","movement_type":"Isolation","equipment":"Bodyweight"},
]

CATALOG_BY_ID = {item["id"]: item for item in BUILTIN_EXERCISE_CATALOG}

def normalize_exercise_name(value):
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value or "")).split())

CATALOG_NAME_INDEX = {}
for _item in BUILTIN_EXERCISE_CATALOG:
    CATALOG_NAME_INDEX[normalize_exercise_name(_item["name"])] = (_item["id"], "canonical")
    for _alias in _item.get("aliases", []):
        CATALOG_NAME_INDEX[normalize_exercise_name(_alias)] = (_item["id"], "curated_alias")

def get_angle_options(family):
    return list(ANGLE_OPTIONS.get(family, []))

def angle_response_required(family):
    return family in ANGLE_OPTIONS

def find_catalog_match(name):
    found = CATALOG_NAME_INDEX.get(normalize_exercise_name(name))
    if not found:
        return None
    catalog_id, source = found
    return {"catalog": dict(CATALOG_BY_ID[catalog_id]), "match_source": source, "requires_confirmation": source != "canonical"}

def rank_catalog_candidates(name, category=None, family=None, equipment=None, angle=ANGLE_NOT_SPECIFIED, limit=8):
    """Rank possible definitions. Never confirms an ambiguous identity."""
    normalized = normalize_exercise_name(name)
    tokens = set(normalized.split())
    ranked=[]
    for item in BUILTIN_EXERCISE_CATALOG:
        score=0; reasons=[]
        candidate_tokens=set(normalize_exercise_name(item["name"]).split())
        alias_tokens=set().union(*(set(normalize_exercise_name(a).split()) for a in item.get("aliases",[]))) if item.get("aliases") else set()
        overlap=len(tokens & (candidate_tokens | alias_tokens))
        if overlap: score += min(20, overlap*7); reasons.append("name terms overlap")
        if category and item["category"]==category: score+=20; reasons.append("same category")
        if family and item["family"]==family: score+=40; reasons.append("same movement family")
        if equipment and item["equipment"]==equipment: score+=15; reasons.append("same equipment")
        if angle and angle!=ANGLE_NOT_SPECIFIED and item.get("angle")==angle: score+=15; reasons.append("same angle")
        if score:
            ranked.append({"catalog_id":item["id"],"name":item["name"],"score":score,"reasons":reasons,"already_confirmed":False})
    ranked.sort(key=lambda x:(-x["score"],x["name"]))
    return ranked[:max(1,int(limit or 8))]
