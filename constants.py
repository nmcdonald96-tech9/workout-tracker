import os

APP_VERSION = "1.28.0"
DATABASE_SCHEMA_VERSION = 12
DEBUG_PERFORMANCE = False
COLOR_SUCCESS = "green300"
COLOR_WARNING = "amber300"
COLOR_DANGER = "red300"
COLOR_INFO = "cyan300"
COLOR_MUTED = "white54"
COLOR_ACTIVE = "cyan700"
COLOR_COMPLETE = "green700"
SESSION_TAG_OPTIONS = ["Strength", "Hypertrophy", "Technique", "Recovery", "PR Attempt", "Short Session"]

# ==========================================
# --- APP CONFIGURATION & CONSTANTS ---
# ==========================================

PLATE_WEIGHTS = [45, 35, 25, 10, 5, 2.5]
BAR_WEIGHT_STANDARD = 45.0
BAR_WEIGHT_EZ = 15.0

COMPOUND_JUMP_HEAVY = 10.0
COMPOUND_JUMP_STANDARD = 5.0
ISOLATION_JUMP_HEAVY = 5.0
ISOLATION_JUMP_STANDARD = 2.5

HEAVY_THRESHOLD_COMPOUND = 150.0
HEAVY_THRESHOLD_ISOLATION = 50.0

DELOAD_PERCENTAGE = 0.65
WARMUP_PERCENT_1 = 0.50
WARMUP_PERCENT_2 = 0.75

STATUS_PENDING = "Pending"
STATUS_COMPLETED = "Completed"
STATUS_SKIPPED = "Skipped"

if os.environ.get("FLET_PLATFORM") in ["android", "ios"]:
    DB_PATH = os.path.join(os.environ.get("HOME", "."), "workout_tracker.db")
else:
    DB_PATH = "workout_tracker.db"

# ==========================================
# --- RICH EXERCISE METADATA SCHEMA ---
# ==========================================

EXERCISE_METADATA = {
    "Bench Press (Medium Grip)": {"category": "Chest", "pattern": "Horizontal Press", "movement_type": "Compound", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 45.0},
    "Flat Barbell Bench Press": {"category": "Chest", "pattern": "Horizontal Press", "movement_type": "Compound", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 45.0},
    "Incline Barbell Bench Press": {"category": "Chest", "pattern": "Incline Press", "movement_type": "Compound", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 45.0},
    "Dumbbell Press (Flat)": {"category": "Chest", "pattern": "Horizontal Press", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Press (Low Incline)": {"category": "Chest", "pattern": "Incline Press", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Press (High Incline)": {"category": "Chest", "pattern": "Incline Press", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Flye (Flat)": {"category": "Chest", "pattern": "Chest Isolation", "movement_type": "Isolation", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Row (2-Arm)": {"category": "Back", "pattern": "Horizontal Row", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Row (2-Arm, Incline)": {"category": "Back", "pattern": "Horizontal Row", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Cable Flexion Row": {"category": "Back", "pattern": "Horizontal Row", "movement_type": "Compound", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Pulldown (Normal Grip)": {"category": "Back", "pattern": "Vertical Pull", "movement_type": "Compound", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Pulldown (Straight Arm)": {"category": "Back", "pattern": "Pullover", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Pullup (Wide Grip)": {"category": "Back", "pattern": "Vertical Pull", "movement_type": "Compound", "equipment": "Bodyweight", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Lateral Raise (Super ROM)": {"category": "Shoulders", "pattern": "Lateral Isolation", "movement_type": "Isolation", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Cable Leaning Lateral Raise": {"category": "Shoulders", "pattern": "Lateral Isolation", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Cable Rope Facepull": {"category": "Shoulders", "pattern": "Rear Delt", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Freemotion Rear Delt Flyes (Paused)": {"category": "Shoulders", "pattern": "Rear Delt", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Smith Machine Shoulder Press (Seated)": {"category": "Shoulders", "pattern": "Vertical Press", "movement_type": "Compound", "equipment": "Machine", "plate_loaded": True, "bar_weight": 0.0},
    "Smith Machine Shrug": {"category": "Shoulders", "pattern": "Upper Trap", "movement_type": "Isolation", "equipment": "Machine", "plate_loaded": True, "bar_weight": 45.0},
    "Dumbbell Shrug": {"category": "Shoulders", "pattern": "Upper Trap", "movement_type": "Isolation", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Barbell Squat (High Bar)": {"category": "Quads", "pattern": "Squat Pattern", "movement_type": "Compound", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 45.0},
    "Deadlift": {"category": "Hamstrings", "pattern": "Hinge", "movement_type": "Compound", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 45.0},
    "Hack Squat": {"category": "Quads", "pattern": "Squat Pattern", "movement_type": "Compound", "equipment": "Machine", "plate_loaded": True, "bar_weight": 0},
    "Leg Press": {"category": "Quads", "pattern": "Squat Pattern", "movement_type": "Compound", "equipment": "Machine", "plate_loaded": True, "bar_weight": 0, "plate_mode": "leg_press_total", "plate_weights": [100, 45, 35, 25, 10, 5, 2.5]},
    "Leg Extension": {"category": "Quads", "pattern": "Quad Isolation", "movement_type": "Isolation", "equipment": "Machine", "plate_loaded": False, "bar_weight": 0},
    "Single-Leg Leg Curl": {"category": "Hamstrings", "pattern": "Hamstring Isolation", "movement_type": "Isolation", "equipment": "Machine", "plate_loaded": False, "bar_weight": 0},
    "Reverse Hyper": {"category": "Glutes", "pattern": "Glute Isolation", "movement_type": "Isolation", "equipment": "Plate", "plate_loaded": True, "bar_weight": 0, "plate_mode": "held_total"},
    "Walking Lunges (Glute-Focused)": {"category": "Glutes", "pattern": "Lunge", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Bodyweight Squat (2/3)": {"category": "Quads", "pattern": "Squat Pattern", "movement_type": "Isolation", "equipment": "Bodyweight", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Stiff Legged Deadlift": {"category": "Hamstrings", "pattern": "Hinge", "movement_type": "Compound", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Stair Calves (Single Leg)": {"category": "Calves", "pattern": "Calf Isolation", "movement_type": "Isolation", "equipment": "Bodyweight", "plate_loaded": False, "bar_weight": 0},
    "Calf Machine": {"category": "Calves", "pattern": "Calf Isolation", "movement_type": "Isolation", "equipment": "Machine", "plate_loaded": False, "bar_weight": 0},
    "Cable Curl (EZ Bar)": {"category": "Biceps", "pattern": "Elbow Flexion", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "EZ Bar Curl (Wide Grip)": {"category": "Biceps", "pattern": "Elbow Flexion", "movement_type": "Isolation", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 15.0},
    "Concentration Curl": {"category": "Biceps", "pattern": "Elbow Flexion", "movement_type": "Isolation", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Cable Triceps Pushdown (Bar)": {"category": "Triceps", "pattern": "Elbow Extension", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Cable Overhead Triceps Extension": {"category": "Triceps", "pattern": "Elbow Extension", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Dumbbell Overhead Extension": {"category": "Triceps", "pattern": "Elbow Extension", "movement_type": "Isolation", "equipment": "Dumbbell", "plate_loaded": False, "bar_weight": 0},
    "Cable Tricep Kickback": {"category": "Triceps", "pattern": "Elbow Extension", "movement_type": "Isolation", "equipment": "Cable", "plate_loaded": False, "bar_weight": 0},
    "Barbell Standing Wrist Curl": {"category": "Forearms", "pattern": "Wrist Flexion", "movement_type": "Isolation", "equipment": "Barbell", "plate_loaded": True, "bar_weight": 45.0},
    "Modified Candlestick": {"category": "Abs", "pattern": "Trunk Flexion", "movement_type": "Isolation", "equipment": "Bodyweight", "plate_loaded": False, "bar_weight": 0}
}

# =======================================
# --- STRENGTH STANDARDS (Percentile Comparison Feature) ---
# =======================================
# Bodyweight-ratio strength standards (1RM as a multiple of bodyweight).
# Approximated from converged values across major lifting-data aggregators
# and classic reference tables (StrengthLevel-style data, ExRx/Kilgore-style
# tables). Treat as directional, not exact -- different sources disagree by
# 5-10% at every tier, and these are built from self-reported trained lifters,
# not the general population.
STRENGTH_STANDARDS_MALE = {
    "bench_press": {"beginner": 0.50, "novice": 0.75, "intermediate": 1.00, "advanced": 1.50, "elite": 1.75},
    "squat":       {"beginner": 0.75, "novice": 1.00, "intermediate": 1.50, "advanced": 2.00, "elite": 2.50},
    "deadlift":    {"beginner": 1.00, "novice": 1.25, "intermediate": 1.75, "advanced": 2.25, "elite": 2.75},
}
STRENGTH_STANDARDS_FEMALE = {
    "bench_press": {"beginner": 0.27, "novice": 0.45, "intermediate": 0.65, "advanced": 0.85, "elite": 1.00},
    "squat":       {"beginner": 0.50, "novice": 0.75, "intermediate": 1.00, "advanced": 1.50, "elite": 1.75},
    "deadlift":    {"beginner": 0.65, "novice": 0.85, "intermediate": 1.15, "advanced": 1.50, "elite": 1.75},
}

# Anchor percentile for each tier label -- used to interpolate a continuous
# percentile-like number rather than just returning a discrete tier.
PERCENTILE_ANCHORS = {"beginner": 5, "novice": 20, "intermediate": 50, "advanced": 80, "elite": 95}

# Only free-bar / bodyweight-stabilized lifts qualify for comparison --
# standards assume the stabilization demand of an unassisted barbell lift,
# so machine and smith-machine variants are intentionally excluded.
STRENGTH_STANDARD_LIFT_MAP = {
    "Bench Press (Medium Grip)": "bench_press",
    "Flat Barbell Bench Press": "bench_press",
    "Barbell Squat (High Bar)": "squat",
    "Deadlift": "deadlift",
}

# McCulloch age coefficients (USA Powerlifting Masters formula), sourced from
# the official USAPL age coefficients table. Used to scale a 40+ lifter's raw
# number up to its "prime-age equivalent" before comparing against standards
# tables, which are mostly calibrated on lifters in their 20s-30s.
MCCULLOCH_AGE_COEFFICIENTS = {
    40: 1.000, 41: 1.010, 42: 1.020, 43: 1.031, 44: 1.043, 45: 1.055,
    46: 1.068, 47: 1.082, 48: 1.097, 49: 1.113, 50: 1.130, 51: 1.147,
    52: 1.165, 53: 1.184, 54: 1.204, 55: 1.225, 56: 1.246, 57: 1.268,
    66: 1.511, 67: 1.543, 68: 1.576, 69: 1.610, 70: 1.645,
    # 58-65 weren't in the official source table -- linear-filled as an
    # approximation between the published 57 and 66 values. Fine for a
    # motivational feature; swap in official values if you want it exact.
    58: 1.290, 59: 1.313, 60: 1.336, 61: 1.360, 62: 1.385,
    63: 1.410, 64: 1.436, 65: 1.463,
}

# =======================================
# --- SESSION-LEVEL PROGRESSION THRESHOLDS ---
# =======================================
# Used by evaluate_straight_set_session() / calculate_session_progression()
# in database.py to gate progression on the WHOLE session's performance
# (all logged sets) rather than only the first set. Tune to taste -- these
# are reasoned starting values, not empirically fixed.

# How close a set's weight must be to the session's detected "working weight"
# to count as a same-weight set (5% tolerance for plate-rounding, etc).
STRAIGHT_SET_WEIGHT_TOLERANCE = 0.05

# Average weighted rep-completion ratio required across all sets to progress.
STRAIGHT_SET_PROGRESS_REP_COMPLETION = 0.95

# Fraction of sets that must individually hit the rep target (at working
# weight) to progress. 1.0 = every prescribed set must hit target, matching
# classic double-progression doctrine.
STRAIGHT_SET_PROGRESS_SET_COMPLETION = 1.0

# The single WORST set's ratio can't fall below this or progression is
# blocked, even if the average looks fine.
STRAIGHT_SET_PROGRESS_MIN_SET_RATIO = 0.85

# A peak (hardest-felt) RPE at or above this blocks progression even if
# every rep target was technically hit -- no room left to add more.
STRAIGHT_SET_MAX_PROGRESS_RPE = 9.5

# Below this average rep-completion, force a weight step DOWN rather than
# just holding at the same weight.
STRAIGHT_SET_REDUCE_REP_COMPLETION = 0.70

# If the worst single set's ratio falls below this, force a reduce
# regardless of how the other sets went (a genuinely collapsed set).
STRAIGHT_SET_REDUCE_MIN_SET_RATIO = 0.60
