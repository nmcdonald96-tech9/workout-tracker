import sqlite3
import os
import contextlib
import json
from datetime import datetime

from constants import *

if os.environ.get("FLET_PLATFORM") in ["android", "ios"]:
    DB_PATH = os.path.join(os.environ.get("HOME", "."), "workout_tracker.db")
else:
    DB_PATH = "workout_tracker.db"

@contextlib.contextmanager
def get_db():
    """Context manager for safe, short-lived mobile DB connections."""
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        conn.close()

# --- DATABASE INIT ---
def init_and_seed_db():
    with get_db() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        cursor = conn.cursor()
        
        cursor.execute("CREATE TABLE IF NOT EXISTS exercise_dict (name TEXT PRIMARY KEY, category TEXT, movement_pattern TEXT DEFAULT 'General', setup_notes TEXT DEFAULT '')")
        
        cursor.execute("CREATE TABLE IF NOT EXISTS user_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)")
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('bodyweight', '178.0')")
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('age', '43')")
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('progression_profile', '0')") # 0 = Auto
        
        # --- SAFE MIGRATIONS FOR EXERCISE DICT ---
        cursor.execute("PRAGMA table_info(exercise_dict)")
        columns = [info[1] for info in cursor.fetchall()]
        if "movement_pattern" not in columns:
            cursor.execute("ALTER TABLE exercise_dict ADD COLUMN movement_pattern TEXT DEFAULT 'General'")
            conn.commit()
            
            for ex_name, ex_data in EXERCISE_METADATA.items():
                cursor.execute("UPDATE exercise_dict SET movement_pattern = ? WHERE name = ?", (ex_data["pattern"], ex_name))
            conn.commit()
            
        if "setup_notes" not in columns:
            cursor.execute("ALTER TABLE exercise_dict ADD COLUMN setup_notes TEXT DEFAULT ''")
            conn.commit()
        
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS workout_sessions ("
            f"id INTEGER PRIMARY KEY AUTOINCREMENT, "
            f"date TEXT, exercise TEXT, category TEXT DEFAULT 'General', "
            f"day_of_week TEXT, week TEXT, target_weight REAL, target_reps INTEGER, "
            f"status TEXT DEFAULT '{STATUS_PENDING}', movement_type TEXT DEFAULT 'Isolation', "
            f"meso_number INTEGER DEFAULT 1, bodyweight_snapshot REAL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS workout_sets ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id INTEGER, set_number INTEGER, weight REAL, reps INTEGER, rpe REAL, "
            "rest_seconds INTEGER, target_weight REAL, target_reps INTEGER, "
            "completed_at TEXT, is_complete INTEGER DEFAULT 0, "
            "FOREIGN KEY(session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE)"
        )
        cursor.execute("CREATE TABLE IF NOT EXISTS meso_names (meso_number INTEGER PRIMARY KEY, meso_label TEXT)")
        
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS readiness_logs ("
            "date TEXT PRIMARY KEY, sleep INTEGER, joints INTEGER, drive INTEGER, pump INTEGER DEFAULT 0, "
            "meso_number INTEGER, week TEXT, day_of_week TEXT)"
        )

        # --- SAFE MIGRATION FOR READINESS LOGS ---
        cursor.execute("PRAGMA table_info(readiness_logs)")
        rl_columns = [info[1] for info in cursor.fetchall()]
        if "pump" not in rl_columns:
            cursor.execute("ALTER TABLE readiness_logs ADD COLUMN pump INTEGER DEFAULT 0")
            conn.commit()
        if "diet" not in rl_columns:
            cursor.execute("ALTER TABLE readiness_logs ADD COLUMN diet INTEGER DEFAULT 0")
            conn.commit()

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS meso_configs ("
            "meso_number INTEGER PRIMARY KEY, "
            "length_weeks INTEGER, "
            "selected_days TEXT, "
            "priorities TEXT, "
            "daily_ex_cap INTEGER, "
            "blueprint_json TEXT)"
        )

        cursor.execute("PRAGMA table_info(workout_sessions)")
        cols = [info[1] for info in cursor.fetchall()]
        if "bodyweight_snapshot" not in cols:
            cursor.execute("ALTER TABLE workout_sessions ADD COLUMN bodyweight_snapshot REAL")
            conn.commit()

        # --- SAFE MIGRATION: REST TIME BETWEEN SETS ---
        # Records seconds elapsed between the first edit of the previous set's
        # weight/reps and the first edit of this set's -- i.e. real elapsed
        # rest time, not a countdown. NULL for a set's first row in a session
        # (no prior set to compare against) and for any row logged before this
        # migration existed.
        cursor.execute("PRAGMA table_info(workout_sets)")
        ws_cols = [info[1] for info in cursor.fetchall()]
        if "rest_seconds" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN rest_seconds INTEGER")
            conn.commit()
        if "target_weight" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN target_weight REAL")
            conn.commit()
        if "target_reps" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN target_reps INTEGER")
            conn.commit()
        if "completed_at" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN completed_at TEXT")
            conn.commit()
        if "is_complete" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN is_complete INTEGER DEFAULT 0")
            conn.commit()

        # --- ONE-TIME SAFE BODYWEIGHT FIX MIGRATION ---
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('migration_bw_v1', '0')")
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_key = 'migration_bw_v1'")
        if cursor.fetchone()[0] == '0':
            bw_exercises = [ex for ex, meta in EXERCISE_METADATA.items() if meta.get("equipment") == "Bodyweight"]
            for bw_ex in bw_exercises:
                cursor.execute("""
                    UPDATE workout_sets 
                    SET weight = 0.0 
                    WHERE weight > 170 AND weight < 180 
                    AND session_id IN (SELECT id FROM workout_sessions WHERE exercise = ? AND target_weight > 170 AND target_weight < 180)
                """, (bw_ex,))
                cursor.execute("UPDATE workout_sessions SET target_weight = 0.0 WHERE exercise = ? AND target_weight > 170 AND target_weight < 180", (bw_ex,))
            cursor.execute("UPDATE user_settings SET setting_value = '1' WHERE setting_key = 'migration_bw_v1'")
            conn.commit()

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_meso_week_day ON workout_sessions(meso_number, week, day_of_week)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sets_session ON workout_sets(session_id)")

        cursor.execute("UPDATE exercise_dict SET category = 'Biceps' WHERE category = 'Calves & Arms & Abs' AND name LIKE '%Curl%' AND name NOT LIKE '%Wrist%'")
        cursor.execute("UPDATE workout_sessions SET category = 'Biceps' WHERE category = 'Calves & Arms & Abs' AND exercise LIKE '%Curl%' AND exercise NOT LIKE '%Wrist%'")

        cursor.execute("UPDATE exercise_dict SET category = 'Triceps' WHERE category = 'Calves & Arms & Abs' AND (name LIKE '%Tricep%' OR name LIKE '%Extension%' OR name LIKE '%Kickback%')")
        cursor.execute("UPDATE workout_sessions SET category = 'Triceps' WHERE category = 'Calves & Arms & Abs' AND (exercise LIKE '%Tricep%' OR exercise LIKE '%Extension%' OR exercise LIKE '%Kickback%')")

        cursor.execute("UPDATE exercise_dict SET category = 'Forearms' WHERE category = 'Calves & Arms & Abs' AND name LIKE '%Wrist%'")
        cursor.execute("UPDATE workout_sessions SET category = 'Forearms' WHERE category = 'Calves & Arms & Abs' AND exercise LIKE '%Wrist%'")

        cursor.execute("UPDATE exercise_dict SET category = 'Abs' WHERE category = 'Calves & Arms & Abs' AND name = 'Modified Candlestick'")
        cursor.execute("UPDATE workout_sessions SET category = 'Abs' WHERE category = 'Calves & Arms & Abs' AND exercise = 'Modified Candlestick'")

        # --- AUTO-MIGRATE HISTORICAL LEGS DATA INTO 4 SPLITS ---
        for ex_name, meta in EXERCISE_METADATA.items():
            if meta.get("category") in ["Quads", "Hamstrings", "Glutes", "Calves"]:
                cursor.execute("UPDATE exercise_dict SET category = ? WHERE name = ?", (meta["category"], ex_name))
                cursor.execute("UPDATE workout_sessions SET category = ? WHERE exercise = ?", (meta["category"], ex_name))
                
        cursor.execute("UPDATE exercise_dict SET category = 'General' WHERE category = 'Calves & Arms & Abs'")
        cursor.execute("UPDATE workout_sessions SET category = 'General' WHERE category = 'Calves & Arms & Abs'")
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM exercise_dict")
        if cursor.fetchone()[0] == 0:
            for ex_name, ex_data in EXERCISE_METADATA.items():
                cursor.execute("INSERT OR IGNORE INTO exercise_dict (name, category, movement_pattern) VALUES (?, ?, ?)", (ex_name, ex_data["category"], ex_data["pattern"]))
            conn.commit()

        cursor.execute("SELECT COUNT(*) FROM meso_configs")
        if cursor.fetchone()[0] == 0:
            seed_meso_week_one(1)

def get_latest_meso_number(cursor):
    cursor.execute("SELECT COALESCE(MAX(meso_number), 0) FROM meso_names")
    max_names = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COALESCE(MAX(meso_number), 0) FROM meso_configs")
    max_cfg = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COALESCE(MAX(meso_number), 0) FROM workout_sessions")
    max_sessions = cursor.fetchone()[0] or 0
    return max(max_names, max_cfg, max_sessions)

def get_next_meso_number(cursor):
    return get_latest_meso_number(cursor) + 1

def get_user_bodyweight():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_key = 'bodyweight'")
        row = cursor.fetchone()
        if row:
            try:
                return float(row[0])
            except:
                pass
    return 178.0

def get_user_age():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_key = 'age'")
        row = cursor.fetchone()
        if row:
            try:
                return int(row[0])
            except:
                pass
    return 43

def get_user_sex():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_key = 'sex'")
        row = cursor.fetchone()
        if row and row[0] in ("Male", "Female"):
            return row[0]
    return "Male"

def get_user_progression_profile():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM user_settings WHERE setting_key = 'progression_profile'")
        row = cursor.fetchone()
        if row:
            try:
                return int(row[0])
            except:
                pass
    return 0

def upsert_meso_config(cursor, meso_number, length_weeks, selected_days, priorities, daily_ex_cap, blueprint_json):
    cursor.execute(
        """
        INSERT INTO meso_configs
        (meso_number, length_weeks, selected_days, priorities, daily_ex_cap, blueprint_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(meso_number) DO UPDATE SET
            length_weeks = excluded.length_weeks,
            selected_days = excluded.selected_days,
            priorities = excluded.priorities,
            daily_ex_cap = excluded.daily_ex_cap,
            blueprint_json = excluded.blueprint_json
        """,
        (meso_number, length_weeks, selected_days, priorities, daily_ex_cap, blueprint_json)
    )

def seed_meso_week_one(meso_num):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM workout_sessions WHERE meso_number = ? AND week = '1'", (meso_num,))
        if cursor.fetchone()[0] > 0:
            return

        cursor.execute("INSERT OR IGNORE INTO meso_names (meso_number, meso_label) VALUES (?, ?)", (meso_num, f"Meso {meso_num}"))

        today_str = datetime.now().strftime("%Y-%m-%d")
        true_routine = [
            ('Dumbbell Row (2-Arm)', 'Monday', '1', 60.0, 10, 'Compound', 'Back'),
            ('Dumbbell Stiff Legged Deadlift', 'Monday', '1', 30.0, 12, 'Compound', 'Hamstrings'),
            ('Dumbbell Lateral Raise (Super ROM)', 'Monday', '1', 15.0, 12, 'Isolation', 'Shoulders'),
            ('Smith Machine Shrug', 'Monday', '1', 100.0, 12, 'Isolation', 'Shoulders'),
            ('Cable Flexion Row', 'Monday', '1', 170.0, 10, 'Compound', 'Back'),
            ('Pulldown (Normal Grip)', 'Monday', '1', 160.0, 10, 'Compound', 'Back'),
            ('Pullup (Wide Grip)', 'Monday', '1', 0.0, 8, 'Compound', 'Back'),
            ('Modified Candlestick', 'Monday', '1', 0.0, 12, 'Isolation', 'Abs'),
            ('Bodyweight Squat (2/3)', 'Monday', '1', 0.0, 12, 'Isolation', 'Quads'),
            ('Stair Calves (Single Leg)', 'Monday', '1', 0.0, 12, 'Isolation', 'Calves'),
            ('Bench Press (Medium Grip)', 'Tuesday', '1', 135.0, 8, 'Compound', 'Chest'),
            ('Flat Barbell Bench Press', 'Tuesday', '1', 135.0, 8, 'Compound', 'Chest'),
            ('Incline Barbell Bench Press', 'Tuesday', '1', 115.0, 8, 'Compound', 'Chest'),
            ('Cable Curl (EZ Bar)', 'Tuesday', '1', 42.5, 12, 'Isolation', 'Biceps'),
            ('Dumbbell Press (Flat)', 'Tuesday', '1', 65.0, 8, 'Compound', 'Chest'),
            ('Cable Triceps Pushdown (Bar)', 'Tuesday', '1', 57.5, 12, 'Isolation', 'Triceps'),
            ('Dumbbell Press (Low Incline)', 'Tuesday', '1', 50.0, 8, 'Compound', 'Chest'),
            ('Dumbbell Flye (Flat)', 'Tuesday', '1', 25.0, 12, 'Isolation', 'Chest'),
            ('Cable Overhead Triceps Extension', 'Tuesday', '1', 65.0, 12, 'Isolation', 'Triceps'),
            ('Barbell Standing Wrist Curl', 'Tuesday', '1', 45.0, 15, 'Isolation', 'Forearms'),
            ('EZ Bar Curl (Wide Grip)', 'Tuesday', '1', 85.0, 12, 'Isolation', 'Biceps'),
            ('Dumbbell Overhead Extension', 'Tuesday', '1', 65.0, 12, 'Isolation', 'Triceps'),
            ('Barbell Squat (High Bar)', 'Wednesday', '1', 105.0, 8, 'Compound', 'Quads'),
            ('Deadlift', 'Wednesday', '1', 155.0, 5, 'Compound', 'Hamstrings'),
            ('Hack Squat', 'Wednesday', '1', 45.0, 8, 'Compound', 'Quads'),
            ('Calf Machine', 'Wednesday', '1', 255.0, 12, 'Isolation', 'Calves'),
            ('Leg Press', 'Wednesday', '1', 255.0, 8, 'Compound', 'Quads'),
            ('Leg Extension', 'Wednesday', '1', 175.0, 12, 'Isolation', 'Quads'),
            ('Single-Leg Leg Curl', 'Wednesday', '1', 10.0, 12, 'Isolation', 'Hamstrings'),
            ('Modified Candlestick', 'Wednesday', '1', 0.0, 12, 'Isolation', 'Abs'),
            ('Reverse Hyper', 'Wednesday', '1', 210.0, 12, 'Isolation', 'Glutes'),
            ('Walking Lunges (Glute-Focused)', 'Wednesday', '1', 15.0, 10, 'Compound', 'Glutes'),
            ('Bodyweight Squat (2/3)', 'Wednesday', '1', 0.0, 12, 'Isolation', 'Quads'),
            ('Dumbbell Stiff Legged Deadlift', 'Wednesday', '1', 35.0, 12, 'Compound', 'Hamstrings'),
            ('Dumbbell Lateral Raise (Super ROM)', 'Thursday', '1', 15.0, 12, 'Isolation', 'Shoulders'),
            ('Pullup (Wide Grip)', 'Thursday', '1', 0.0, 8, 'Compound', 'Back'),
            ('Dumbbell Row (2-Arm, Incline)', 'Thursday', '1', 50.0, 10, 'Compound', 'Back'),
            ('Dumbbell Press (High Incline)', 'Thursday', '1', 40.0, 8, 'Compound', 'Chest'),
            ('Dumbbell Shrug', 'Thursday', '1', 55.0, 12, 'Isolation', 'Shoulders'),
            ('Cable Leaning Lateral Raise', 'Thursday', '1', 10.0, 12, 'Isolation', 'Shoulders'),
            ('Cable Rope Facepull', 'Thursday', '1', 50.0, 12, 'Isolation', 'Shoulders'),
            ('Freemotion Rear Delt Flyes (Paused)', 'Thursday', '1', 10.0, 12, 'Isolation', 'Shoulders'),
            ('Smith Machine Shoulder Press (Seated)', 'Thursday', '1', 50.0, 8, 'Compound', 'Shoulders'),
            ('Pulldown (Straight Arm)', 'Thursday', '1', 50.0, 12, 'Isolation', 'Back'),
            ('Bench Press (Medium Grip)', 'Friday', '1', 145.0, 8, 'Compound', 'Chest'),
            ('Dumbbell Overhead Extension', 'Friday', '1', 65.0, 12, 'Isolation', 'Triceps'),
            ('Cable Curl (EZ Bar)', 'Friday', '1', 42.5, 12, 'Isolation', 'Biceps'),
            ('Cable Overhead Triceps Extension', 'Friday', '1', 60.0, 12, 'Isolation', 'Triceps'),
            ('Modified Candlestick', 'Friday', '1', 0.0, 12, 'Isolation', 'Abs'),
            ('Concentration Curl', 'Friday', '1', 25.0, 12, 'Isolation', 'Biceps'),
            ('Cable Tricep Kickback', 'Friday', '1', 12.5, 12, 'Isolation', 'Triceps'),
            ('Cable Triceps Pushdown (Bar)', 'Friday', '1', 57.5, 12, 'Isolation', 'Triceps'),
            ('Pullup (Wide Grip)', 'Friday', '1', 0.0, 8, 'Compound', 'Back'),
            ('Dumbbell Flye (Flat)', 'Friday', '1', 25.0, 12, 'Isolation', 'Chest'),
            ('Barbell Standing Wrist Curl', 'Friday', '1', 45.0, 15, 'Isolation', 'Forearms')
        ]

        active_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        blueprint = {d: [] for d in active_days}

        for row in true_routine:
            cursor.execute(
                f"""
                INSERT INTO workout_sessions (date, exercise, category, day_of_week, week, target_weight, target_reps, status, movement_type, meso_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, '{STATUS_PENDING}', ?, ?)
                """,
                (today_str, row[0], row[6], row[1], row[2], row[3], row[4], row[5], meso_num)
            )
            if row[0] not in blueprint[row[1]]:
                blueprint[row[1]].append(row[0])

        upsert_meso_config(
            cursor,
            meso_num,
            4,
            json.dumps(active_days),
            json.dumps({"mode": "manual"}),
            0,
            json.dumps(blueprint)
        )
        conn.commit()


# --- DUMBBELL PHYSICAL RACK LIMITERS ---
def get_next_dumbbell(current_weight):
    db_rack = [2.5, 5.0, 7.5, 10.0, 12.5, 15.0] + [float(x) for x in range(20, 105, 5)]
    for w in db_rack:
        if w > current_weight:
            return w
    return current_weight # Maxed out!

def get_prev_dumbbell(current_weight):
    db_rack = [2.5, 5.0, 7.5, 10.0, 12.5, 15.0] + [float(x) for x in range(20, 105, 5)]
    for w in reversed(db_rack):
        if w < current_weight:
            return w
    return current_weight


def calculate_progression(first_set_w, first_set_reps, first_set_rpe, tgt_r, mov_type, readiness_score=15, joint_score=5, equipment_type="Barbell", is_bodyweight=False, age=43, profile=0):
    # Coerce None or non-numeric RPE to a neutral baseline value (8.0 = moderate effort)
    # so the engine never crashes silently when a set was logged without RPE.
    try:
        first_set_rpe = float(first_set_rpe) if first_set_rpe is not None else 8.0
    except (TypeError, ValueError):
        first_set_rpe = 8.0

    # Guard tgt_r (this week's target reps) the same way -- it flows into
    # `tgt_r - first_set_reps` arithmetic further down with no prior check.
    # A None/blank target_reps (e.g. an older row, or a data path that didn't
    # set it) would otherwise throw TypeError and silently abort the whole
    # week's progression with zero feedback to the user.
    try:
        tgt_r = int(tgt_r) if tgt_r is not None else 10
    except (TypeError, ValueError):
        tgt_r = 10

    # Same defensive coercion for the actual logged performance values --
    # these should always be numeric by the time they reach here, but the
    # cost of guarding is negligible next to a silently aborted week.
    try:
        first_set_w = float(first_set_w) if first_set_w is not None else 0.0
    except (TypeError, ValueError):
        first_set_w = 0.0
    try:
        first_set_reps = int(first_set_reps) if first_set_reps is not None else tgt_r
    except (TypeError, ValueError):
        first_set_reps = tgt_r

    is_heavy_compound = (mov_type == 'Compound' and first_set_w >= HEAVY_THRESHOLD_COMPOUND)
    is_heavy_isolation = (mov_type == 'Isolation' and first_set_w >= HEAVY_THRESHOLD_ISOLATION)

    standard_jump = COMPOUND_JUMP_STANDARD if mov_type == 'Compound' else ISOLATION_JUMP_STANDARD
    heavy_jump = COMPOUND_JUMP_HEAVY if mov_type == 'Compound' else ISOLATION_JUMP_HEAVY

    jump_size = heavy_jump if (is_heavy_compound or is_heavy_isolation) else standard_jump
    
    if is_bodyweight:
        jump_size = 0.0

    # --- PROGRESSION OVERRIDE LOGIC ---
    # Determine the effective profile: 1 (Conservative), 2 (Balanced), 3 (Aggressive)
    if profile == 0:  # Auto (Age-Based)
        if age < 35: effective_profile = 3
        elif age < 45: effective_profile = 2
        else: effective_profile = 1
    else:
        effective_profile = profile

    if effective_profile == 3: # Aggressive Profile
        REP_CEILING = 12
        FORCE_DOUBLE_PROG_WEIGHT = 9999 
    elif effective_profile == 2: # Balanced Profile
        REP_CEILING = 15
        FORCE_DOUBLE_PROG_WEIGHT = 225  
    else: # Conservative / Longevity Profile
        REP_CEILING = 18
        FORCE_DOUBLE_PROG_WEIGHT = 185  

    # Determine if we should use Double Progression
    use_double_progression = False
    if equipment_type == "Dumbbell":
        use_double_progression = True
    elif effective_profile == 1 and first_set_w >= FORCE_DOUBLE_PROG_WEIGHT and not is_bodyweight:
        use_double_progression = True

    # --- 1. DOUBLE PROGRESSION (Volume Accumulation) ---
    if use_double_progression:
        REP_FLOOR = tgt_r if tgt_r else 8
        
        if joint_score <= 2:
            lower_w = get_prev_dumbbell(first_set_w) if equipment_type == "Dumbbell" else max(first_set_w - standard_jump, 0.0)
            return lower_w, tgt_r

        if readiness_score <= 7 and first_set_rpe >= 9.0:
            return first_set_w, tgt_r
            
        miss_margin = tgt_r - first_set_reps
        
        if miss_margin >= 5:
            lower_w = get_prev_dumbbell(first_set_w) if equipment_type == "Dumbbell" else max(first_set_w - standard_jump, 0.0)
            if first_set_rpe <= 8.5:
                return lower_w, first_set_reps + 1
            else:
                return lower_w, tgt_r
        
        # The Graduation Check
        if first_set_reps >= REP_CEILING and first_set_rpe <= 9.0:
            next_w = get_next_dumbbell(first_set_w) if equipment_type == "Dumbbell" else first_set_w + standard_jump
            return next_w, REP_FLOOR
        else:
            # Grind Phase: Hold weight, build reps
            reps_to_add = 2 if first_set_rpe <= 8.0 else 1
            return first_set_w, first_set_reps + reps_to_add


    # --- 2. STANDARD PROGRESSION (Aggressive Load) ---
    if joint_score <= 2:
        return max(first_set_w - standard_jump, 0.0), tgt_r

    if readiness_score <= 7:
        jump_size = standard_jump if not is_bodyweight else 0.0
        if first_set_rpe >= 9.0:
            jump_size = 0.0

    miss_margin = tgt_r - first_set_reps

    if miss_margin >= 5:
        if first_set_rpe <= 8.5:
            return max(first_set_w - jump_size, 0.0), first_set_reps + 1
        else:
            return max(first_set_w - jump_size, 0.0), tgt_r

    elif miss_margin > 0:
        return first_set_w, tgt_r

    else:
        if first_set_rpe <= 8.5:
            if first_set_reps >= tgt_r + 3:
                return first_set_w + jump_size, tgt_r + (2 if is_bodyweight else 1)
            else:
                return first_set_w + jump_size, tgt_r + (1 if is_bodyweight else 0)
        elif 8.5 < first_set_rpe <= 9.5:
            if jump_size > 0:
                return first_set_w + standard_jump, tgt_r
            else:
                return first_set_w, tgt_r + 1
        else:
            return first_set_w, tgt_r + 1



def _progression_weight_step(weight, movement_type, equipment_type, direction=1):
    """Return one practical equipment-specific weight step."""
    weight = float(weight or 0.0)
    if equipment_type == "Dumbbell":
        return get_next_dumbbell(weight) if direction > 0 else get_prev_dumbbell(weight)
    step = COMPOUND_JUMP_STANDARD if movement_type == "Compound" else ISOLATION_JUMP_STANDARD
    return max(0.0, weight + (step * direction))


def evaluate_straight_set_session(completed_sets, target_weight, target_reps, is_bodyweight=False, bodyweight=0.0):
    """Evaluate the complete straight-set prescription instead of only Set 1.

    Returns prescription-completion metrics and a progress/hold/reduce decision.
    Weight-adjusted rep ratios prevent lighter back-off sets from counting as full
    straight-set completions, while still giving those sets partial credit.
    """
    valid_sets = []
    for row in completed_sets or []:
        try:
            weight = float(row[0]) if row[0] is not None else 0.0
            reps = int(row[1]) if row[1] is not None else 0
            rpe = float(row[2]) if len(row) > 2 and row[2] is not None else 8.0
        except (TypeError, ValueError):
            continue
        if reps > 0:
            valid_sets.append((weight, reps, rpe))

    try:
        target_reps = max(1, int(target_reps))
    except (TypeError, ValueError):
        target_reps = 10

    if not valid_sets:
        return {
            "decision": "hold", "set_count": 0, "sets_at_target": 0,
            "set_completion_ratio": 0.0, "total_actual_reps": 0,
            "total_target_reps": 0, "rep_completion_ratio": 0.0,
            "lowest_set_ratio": 0.0, "average_rpe": 8.0, "peak_rpe": 8.0,
            "working_weight": float(target_weight or 0.0), "average_reps": 0.0,
            "reason": "No valid completed sets were available."
        }

    # Straight sets normally share one load. Use the most frequently logged load;
    # ties resolve to the earliest logged load, which is usually the intended work weight.
    weight_counts = {}
    first_index = {}
    for idx, (weight, _reps, _rpe) in enumerate(valid_sets):
        key = round(weight, 3)
        weight_counts[key] = weight_counts.get(key, 0) + 1
        first_index.setdefault(key, idx)
    working_weight = max(weight_counts, key=lambda key: (weight_counts[key], -first_index[key]))

    effective_reference = working_weight + (float(bodyweight or 0.0) if is_bodyweight else 0.0)
    if effective_reference <= 0:
        effective_reference = 1.0

    weighted_ratios = []
    sets_at_target = 0
    total_actual_reps = 0
    rpes = []
    tolerance = STRAIGHT_SET_WEIGHT_TOLERANCE

    for weight, reps, rpe in valid_sets:
        effective_weight = weight + (float(bodyweight or 0.0) if is_bodyweight else 0.0)
        load_ratio = max(0.0, effective_weight / effective_reference)
        # Cap the per-set contribution so one unusually heavy/high-rep set cannot
        # erase a major collapse across the remaining straight sets.
        set_ratio = min(1.20, load_ratio * (reps / target_reps))
        weighted_ratios.append(set_ratio)
        total_actual_reps += reps
        rpes.append(rpe)
        if load_ratio >= (1.0 - tolerance) and reps >= target_reps:
            sets_at_target += 1

    set_count = len(valid_sets)
    rep_completion = sum(weighted_ratios) / set_count
    set_completion = sets_at_target / set_count
    lowest_ratio = min(weighted_ratios)
    average_rpe = sum(rpes) / len(rpes)
    peak_rpe = max(rpes)
    average_reps = total_actual_reps / set_count

    progress_ok = (
        rep_completion >= STRAIGHT_SET_PROGRESS_REP_COMPLETION
        and set_completion >= STRAIGHT_SET_PROGRESS_SET_COMPLETION
        and lowest_ratio >= STRAIGHT_SET_PROGRESS_MIN_SET_RATIO
        and peak_rpe <= STRAIGHT_SET_MAX_PROGRESS_RPE
    )
    reduce_needed = (
        rep_completion < STRAIGHT_SET_REDUCE_REP_COMPLETION
        or lowest_ratio < STRAIGHT_SET_REDUCE_MIN_SET_RATIO
    )

    if progress_ok:
        decision = "progress"
        reason = "The full straight-set prescription met the progression thresholds."
    elif reduce_needed:
        decision = "reduce"
        reason = "The complete exercise performance was substantially below the prescription."
    else:
        decision = "hold"
        reason = "The first set may have succeeded, but the full straight-set prescription was not mastered."

    return {
        "decision": decision,
        "set_count": set_count,
        "sets_at_target": sets_at_target,
        "set_completion_ratio": round(set_completion, 4),
        "total_actual_reps": total_actual_reps,
        "total_target_reps": target_reps * set_count,
        "rep_completion_ratio": round(rep_completion, 4),
        "lowest_set_ratio": round(lowest_ratio, 4),
        "average_rpe": round(average_rpe, 2),
        "peak_rpe": round(peak_rpe, 2),
        "working_weight": float(working_weight),
        "average_reps": round(average_reps, 2),
        "reason": reason,
    }


def calculate_session_progression(completed_sets, target_weight, target_reps, movement_type,
                                  readiness_score=15, joint_score=5, equipment_type="Barbell",
                                  is_bodyweight=False, bodyweight=0.0, age=43, profile=0):
    """Gate the existing progression engine with whole-session performance."""
    metrics = evaluate_straight_set_session(
        completed_sets, target_weight, target_reps,
        is_bodyweight=is_bodyweight, bodyweight=bodyweight
    )
    working_weight = metrics["working_weight"]

    # Readiness and joint protection remain authoritative regardless of performance.
    if joint_score <= 2:
        next_weight = working_weight if is_bodyweight else _progression_weight_step(
            working_weight, movement_type, equipment_type, direction=-1
        )
        return next_weight, int(target_reps or 10), metrics

    if metrics["decision"] == "hold":
        return working_weight, int(target_reps or 10), metrics

    if metrics["decision"] == "reduce":
        next_weight = working_weight if is_bodyweight else _progression_weight_step(
            working_weight, movement_type, equipment_type, direction=-1
        )
        return next_weight, int(target_reps or 10), metrics

    # Only a successful whole session reaches the existing profile/equipment engine.
    representative_reps = max(int(target_reps or 10), int(round(metrics["average_reps"])))
    next_weight, next_reps = calculate_progression(
        working_weight, representative_reps, metrics["peak_rpe"], target_reps,
        movement_type, readiness_score, joint_score,
        equipment_type=equipment_type, is_bodyweight=is_bodyweight,
        age=age, profile=profile
    )
    return next_weight, next_reps, metrics


def calculate_set_specific_progression(completed_sets, default_target_weight, default_target_reps,
                                       movement_type, readiness_score=15, joint_score=5,
                                       equipment_type="Barbell", is_bodyweight=False,
                                       bodyweight=0.0, age=43, profile=0):
    """Return an independent next target for each completed set position.

    Expected row shape:
      (weight, reps, rpe[, target_weight, target_reps])
    Legacy rows without per-set targets fall back to the session target.
    """
    next_targets = []
    diagnostics = []

    try:
        fallback_w = float(default_target_weight or 0.0)
    except (TypeError, ValueError):
        fallback_w = 0.0 if is_bodyweight else 45.0
    try:
        fallback_r = max(1, int(default_target_reps or 10))
    except (TypeError, ValueError):
        fallback_r = 10

    for set_index, row in enumerate(completed_sets or []):
        try:
            actual_w = float(row[0]) if row[0] is not None else fallback_w
            actual_r = int(row[1]) if row[1] is not None else 0
            actual_rpe = float(row[2]) if len(row) > 2 and row[2] is not None else 8.0
            prior_target_w = float(row[3]) if len(row) > 3 and row[3] is not None else fallback_w
            prior_target_r = int(row[4]) if len(row) > 4 and row[4] is not None else fallback_r
        except (TypeError, ValueError):
            continue
        if actual_r <= 0:
            continue

        next_w, next_r = calculate_progression(
            actual_w, actual_r, actual_rpe, prior_target_r, movement_type,
            readiness_score, joint_score, equipment_type=equipment_type,
            is_bodyweight=is_bodyweight, age=age, profile=profile
        )

        # Preserve bodyweight external-load semantics and practical numeric types.
        next_w = float(next_w)
        next_r = max(1, int(next_r))
        # Ratio-based, not absolute -- a miss of N reps means something very
        # different on a 5-rep set than a 20-rep set. STRAIGHT_SET_REDUCE_REP_COMPLETION
        # (currently 0.70) is the same constant the session-level evaluator uses,
        # so "reduce" means the same thing everywhere in the app, not two
        # different standards depending on which code path got there.
        completion_ratio = (actual_r / prior_target_r) if prior_target_r > 0 else 1.0
        if actual_r >= prior_target_r:
            decision = "progress"
        elif completion_ratio < STRAIGHT_SET_REDUCE_REP_COMPLETION:
            decision = "reduce"
        else:
            decision = "hold"

        next_targets.append({"w": next_w, "r": next_r})
        diagnostics.append({
            "set_number": set_index + 1,
            "decision": decision,
            "actual_weight": actual_w,
            "actual_reps": actual_r,
            "actual_rpe": actual_rpe,
            "prior_target_weight": prior_target_w,
            "prior_target_reps": prior_target_r,
            "next_weight": next_w,
            "next_reps": next_r,
        })

    return next_targets, diagnostics

def get_exercise_smart_defaults(exercise_name, meso_number):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, target_weight, target_reps, movement_type, bodyweight_snapshot
            FROM workout_sessions
            WHERE exercise = ? AND meso_number = ?
            ORDER BY id DESC LIMIT 1
        """, (exercise_name, meso_number))
        session_row = cursor.fetchone()

        meta = EXERCISE_METADATA.get(exercise_name, {})
        mov_type = meta.get("movement_type", "Compound")
        is_bw = meta.get("equipment") == "Bodyweight"
        eq_type = meta.get("equipment", "Barbell")

        if session_row:
            session_id, tgt_w, tgt_r, db_mov_type, bodyweight_snapshot = session_row
            cursor.execute("""
                SELECT weight, reps, rpe, target_weight, target_reps
                FROM workout_sets
                WHERE session_id = ?
                ORDER BY set_number ASC
            """, (session_id,))
            set_rows = cursor.fetchall()
            if set_rows:
                targets, _ = calculate_set_specific_progression(
                    set_rows, tgt_w, tgt_r, db_mov_type or mov_type,
                    equipment_type=eq_type, is_bodyweight=is_bw,
                    bodyweight=bodyweight_snapshot if bodyweight_snapshot is not None else get_user_bodyweight(),
                    age=get_user_age(), profile=get_user_progression_profile()
                )
                if targets:
                    # Session-level fields remain a compatibility seed. The card builds
                    # the real next prescription independently for every set position.
                    return targets[0]["w"], targets[0]["r"], db_mov_type or mov_type

            safe_w = tgt_w if tgt_w is not None else (0.0 if is_bw else 45.0)
            safe_r = tgt_r if tgt_r is not None else 10
            return safe_w, safe_r, db_mov_type or mov_type

        return 0.0 if is_bw else 45.0, 10, mov_type

def get_compact_rpe_badge(week_str):
    if week_str == "Deload": return "RPE 5-6"
    elif week_str == "1": return "RPE 7-8"
    elif week_str == "2": return "RPE 8-9"
    else: return "RPE 9-10"

def calculate_e1rm(weight, reps, bodyweight=0.0):
    try:
        w, r = float(weight) + float(bodyweight), int(reps)
        if r <= 0: return 0.0
        if r == 1: return w
        elif 1 < r < 37: return round(w * (36 / (37 - r)), 1)
        return 0.0
    except: return 0.0

def format_duration_seconds(secs):
    """Formats a duration in seconds as a short human string (e.g. '4m 12s',
    '1h 2m'). Shared by the per-set rest caption and the day/week/meso
    average-rest stats so all four always agree on formatting. Returns None
    if secs is None or negative, so callers can decide how to render 'no data'."""
    if secs is None or secs < 0:
        return None
    secs = int(round(secs))
    if secs < 60:
        return f"{secs}s"
    elif secs < 3600:
        mins, s = divmod(secs, 60)
        return f"{mins}m {s:02d}s" if s else f"{mins}m"
    else:
        hours, rem = divmod(secs, 3600)
        mins, _ = divmod(rem, 60)
        return f"{hours}h {mins}m"

def get_strength_classification(weight, reps, bodyweight, age, sex, exercise_name):
    """Compares a lift against bodyweight-ratio strength standards, age-adjusted
    via the McCulloch Masters coefficients. Returns a dict with level/percentile/
    lift_key/ratio, or None if the exercise isn't a standards-eligible lift or
    inputs are invalid. See STRENGTH_STANDARD_LIFT_MAP in constants.py for which
    exercises qualify."""
    lift_key = STRENGTH_STANDARD_LIFT_MAP.get(exercise_name)
    if not lift_key or not bodyweight or bodyweight <= 0:
        return None

    e1rm = calculate_e1rm(weight, reps)
    if e1rm <= 0:
        return None

    age_coef = 1.0
    if age and age >= 40:
        clamped_age = min(int(age), max(MCCULLOCH_AGE_COEFFICIENTS))
        age_coef = MCCULLOCH_AGE_COEFFICIENTS.get(clamped_age, 1.0)

    ratio = (e1rm * age_coef) / bodyweight
    table = STRENGTH_STANDARDS_MALE if sex == "Male" else STRENGTH_STANDARDS_FEMALE
    levels = table.get(lift_key)
    if not levels:
        return None

    tiers = sorted(levels.items(), key=lambda x: x[1])  # [(beginner, .5), (novice, .75), ...]

    if ratio <= tiers[0][1]:
        pct = max(0.5, round((ratio / tiers[0][1]) * PERCENTILE_ANCHORS[tiers[0][0]], 1))
        return {"level": tiers[0][0].title(), "percentile": pct, "lift_key": lift_key, "ratio": round(ratio, 2), "e1rm": e1rm}

    if ratio >= tiers[-1][1]:
        overshoot = ratio / tiers[-1][1]
        pct = min(99.5, PERCENTILE_ANCHORS[tiers[-1][0]] + (overshoot - 1) * 10)
        return {"level": tiers[-1][0].title(), "percentile": round(pct, 1), "lift_key": lift_key, "ratio": round(ratio, 2), "e1rm": e1rm}

    for i in range(len(tiers) - 1):
        lo_label, lo_ratio = tiers[i]
        hi_label, hi_ratio = tiers[i + 1]
        if lo_ratio <= ratio <= hi_ratio:
            frac = (ratio - lo_ratio) / (hi_ratio - lo_ratio) if hi_ratio > lo_ratio else 0
            pct = PERCENTILE_ANCHORS[lo_label] + frac * (PERCENTILE_ANCHORS[hi_label] - PERCENTILE_ANCHORS[lo_label])
            label = hi_label if frac > 0.5 else lo_label
            return {"level": label.title(), "percentile": round(pct, 1), "lift_key": lift_key, "ratio": round(ratio, 2), "e1rm": e1rm}

    return None

def calculate_plates_per_side(exercise_name, total_weight_str):
    try:
        total_weight = float(total_weight_str)
        meta = EXERCISE_METADATA.get(exercise_name, {})
        
        if not meta:
            ex_lower = exercise_name.lower()
            if any(x in ex_lower for x in ["dumbbell", "cable", "machine", "pulldown", "pullup", "lunges", "squat (2/3)", "candlestick", "stair", "calf", "calves", "bodyweight"]):
                return ""
            if "ez bar" in ex_lower:
                if total_weight < BAR_WEIGHT_EZ: return "Below bar weight"
                remaining = (total_weight - BAR_WEIGHT_EZ) / 2
                bar_label = "EZ Bar"
            else:
                if total_weight < BAR_WEIGHT_STANDARD: return ""
                remaining = (total_weight - BAR_WEIGHT_STANDARD) / 2
                bar_label = "Bar"
        else:
            if not meta.get("plate_loaded", False):
                return ""
                
            bar_w = meta.get("bar_weight", 45.0)
            if total_weight < bar_w:
                return "Below bar weight" if bar_w > 0 else ""
                
            remaining = (total_weight - bar_w) / 2
            bar_label = "EZ Bar" if bar_w == 15.0 else ("Bar" if bar_w == 45.0 else "Sled")

        breakdown = []
        for plate in PLATE_WEIGHTS:
            count = int(remaining // plate)
            if count > 0:
                breakdown.append(f"{count}x{plate}" if count > 1 else str(plate))
                remaining -= count * plate

        if abs(remaining) < 0.01: pass
        
        prefix = f"Plates ({bar_label}): " if bar_label != "Sled" else "Plates/Side: "
        return f"{prefix}{', '.join(breakdown)} lbs" if breakdown else f"Empty {bar_label}"
    except:
        return ""
