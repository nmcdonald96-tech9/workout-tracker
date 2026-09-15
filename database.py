import sqlite3
import os
import contextlib
import json
import uuid
import hashlib
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
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('bodyweight', '0')")
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('age', '0')")
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('progression_profile', '0')") # 0 = Auto
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('workout_focus_mode', '0')")
        cursor.execute("INSERT OR IGNORE INTO user_settings (setting_key, setting_value) VALUES ('ui_density', 'comfortable')")
        cursor.execute("INSERT OR REPLACE INTO user_settings (setting_key, setting_value) VALUES ('schema_version', ?)", (str(DATABASE_SCHEMA_VERSION),))
        
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
        progression_columns = {
            "progression_mode": "TEXT DEFAULT 'default'",
            "progression_step": "REAL",
            "reduction_steps": "INTEGER",
            "rep_ceiling": "INTEGER",
            "reduction_threshold": "REAL",
            "max_progress_rpe": "REAL",
            "max_progression_weight": "REAL",
        }
        for column_name, column_type in progression_columns.items():
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE exercise_dict ADD COLUMN {column_name} {column_type}")
                conn.commit()
        cursor.execute("PRAGMA table_info(exercise_dict)")
        columns=[x[1] for x in cursor.fetchall()]
        for n,t in {"catalog_id":"TEXT","display_name":"TEXT","movement_family":"TEXT","movement_type":"TEXT DEFAULT 'Isolation'","equipment":"TEXT DEFAULT 'Other'","angle":"TEXT DEFAULT 'Not specified'","is_custom":"INTEGER DEFAULT 0"}.items():
            if n not in columns: cursor.execute(f"ALTER TABLE exercise_dict ADD COLUMN {n} {t}")
        cursor.execute("UPDATE exercise_dict SET display_name=name WHERE display_name IS NULL OR TRIM(display_name)='' ")
        cursor.execute("CREATE TABLE IF NOT EXISTS exercise_aliases(alias TEXT PRIMARY KEY,catalog_id TEXT,exercise_name TEXT,source TEXT,confirmed INTEGER DEFAULT 0)")
        cursor.execute("CREATE TABLE IF NOT EXISTS exercise_favorites(catalog_id TEXT PRIMARY KEY,created_at TEXT NOT NULL)")
        conn.commit()
        
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS workout_sessions ("
            f"id INTEGER PRIMARY KEY AUTOINCREMENT, "
            f"date TEXT, exercise TEXT, category TEXT DEFAULT 'General', "
            f"day_of_week TEXT, week TEXT, target_weight REAL, target_reps INTEGER, "
            f"status TEXT DEFAULT '{STATUS_PENDING}', movement_type TEXT DEFAULT 'Isolation', "
            f"meso_number INTEGER DEFAULT 1, bodyweight_snapshot REAL, workout_note TEXT DEFAULT '', session_tags TEXT DEFAULT '')"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS workout_sets ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id INTEGER, set_number INTEGER, weight REAL, reps INTEGER, rpe REAL, "
            "rest_seconds INTEGER, target_weight REAL, target_reps INTEGER, "
            "normal_target_weight REAL, normal_target_reps INTEGER, "
            "completed_at TEXT, is_complete INTEGER DEFAULT 0, "
            "progression_decision TEXT, progression_reason_code TEXT, progression_reason TEXT, progression_settings_snapshot TEXT, "
            "FOREIGN KEY(session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE)"
        )
        cursor.execute("CREATE TABLE IF NOT EXISTS meso_names (meso_number INTEGER PRIMARY KEY, meso_label TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS app_audit (id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,action TEXT NOT NULL,details TEXT DEFAULT '')")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON app_audit(created_at)")
        cursor.execute("CREATE TABLE IF NOT EXISTS sync_devices(device_uuid TEXT PRIMARY KEY,device_label TEXT,created_at TEXT,last_sync_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS sync_records(table_name TEXT,local_key TEXT,record_uuid TEXT UNIQUE,content_hash TEXT,created_at TEXT,updated_at TEXT,deleted_at TEXT,sync_revision INTEGER DEFAULT 1,origin_device TEXT,PRIMARY KEY(table_name,local_key))")
        cursor.execute("CREATE TABLE IF NOT EXISTS sync_state(state_key TEXT PRIMARY KEY,state_value TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS cloud_backup_queue(id INTEGER PRIMARY KEY AUTOINCREMENT,reason TEXT,queued_at TEXT,status TEXT DEFAULT 'pending',attempt_count INTEGER DEFAULT 0,last_error TEXT)")
        if not cursor.execute("SELECT 1 FROM sync_devices LIMIT 1").fetchone():cursor.execute("INSERT INTO sync_devices VALUES(?,?,?,NULL)",(str(uuid.uuid4()),"Android Device",datetime.now().isoformat(timespec="seconds")))
        
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
        if "workout_note" not in cols:
            cursor.execute("ALTER TABLE workout_sessions ADD COLUMN workout_note TEXT DEFAULT ''")
            conn.commit()
        if "session_tags" not in cols:
            cursor.execute("ALTER TABLE workout_sessions ADD COLUMN session_tags TEXT DEFAULT ''")
            conn.commit()
        cursor.execute("PRAGMA table_info(workout_sessions)")
        session_columns=[info[1] for info in cursor.fetchall()]
        for column_name,column_type in {"schedule_origin_day":"TEXT","schedule_exception":"INTEGER DEFAULT 0","skip_reason":"TEXT"}.items():
            if column_name not in session_columns:
                cursor.execute(f"ALTER TABLE workout_sessions ADD COLUMN {column_name} {column_type}")
                conn.commit()
        cursor.execute("UPDATE workout_sessions SET schedule_origin_day=day_of_week WHERE schedule_origin_day IS NULL OR TRIM(schedule_origin_day)='' ")
        conn.commit()
        cursor.execute("PRAGMA table_info(workout_sessions)")
        structure_cols=[x[1] for x in cursor.fetchall()]
        for n,t in {"workout_order":"INTEGER","exercise_group_id":"TEXT","group_position":"INTEGER"}.items():
            if n not in structure_cols:cursor.execute(f"ALTER TABLE workout_sessions ADD COLUMN {n} {t}")
        for sm,sw,sd in cursor.execute("SELECT DISTINCT meso_number,week,day_of_week FROM workout_sessions").fetchall():
            for pos,row in enumerate(cursor.execute("SELECT id FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? ORDER BY COALESCE(workout_order,2147483647),id",(sm,sw,sd)).fetchall(),1):cursor.execute("UPDATE workout_sessions SET workout_order=COALESCE(workout_order,?) WHERE id=?",(pos,row[0]))
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
        if "normal_target_weight" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN normal_target_weight REAL")
            conn.commit()
        if "normal_target_reps" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN normal_target_reps INTEGER")
            conn.commit()
        # Existing records were unregulated before this feature; backfill their
        # normal trajectory from the target originally saved for that set.
        cursor.execute("UPDATE workout_sets SET normal_target_weight = target_weight WHERE normal_target_weight IS NULL")
        cursor.execute("UPDATE workout_sets SET normal_target_reps = target_reps WHERE normal_target_reps IS NULL")
        conn.commit()
        if "completed_at" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN completed_at TEXT")
            conn.commit()
        if "is_complete" not in ws_cols:
            cursor.execute("ALTER TABLE workout_sets ADD COLUMN is_complete INTEGER DEFAULT 0")
            conn.commit()
        snapshot_columns = {
            "progression_decision": "TEXT",
            "progression_reason_code": "TEXT",
            "progression_reason": "TEXT",
            "progression_settings_snapshot": "TEXT",
        }
        for column_name, column_type in snapshot_columns.items():
            if column_name not in ws_cols:
                cursor.execute(f"ALTER TABLE workout_sets ADD COLUMN {column_name} {column_type}")
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

        for item in BUILTIN_EXERCISE_CATALOG:
            cursor.execute("INSERT OR IGNORE INTO exercise_dict(name,category,movement_pattern,catalog_id,display_name,movement_family,movement_type,equipment,angle,is_custom) VALUES(?,?,?,?,?,?,?,?,?,0)",(item['name'],item['category'],item['pattern'],item['id'],item['name'],item['family'],item['movement_type'],item['equipment'],item.get('angle','Not specified')))
        conn.commit()
        # Fresh installs remain blank; existing plans are preserved.

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


def get_readiness_adjustment(readiness_score=15, joint_score=5, movement_type="Compound"):
    """Temporary difficulty reduction for the current day only.

    Sleep and Drive are inferred from readiness_score - joint_score and averaged.
    General scale: 5=0%/0 reps, 4=5%/-1, 3=10%/-2, 2=15%/-3, 1=20%/-4.
    Compound joint scale: 5=0%/0, 4=5%/-1, 3=10%/-2, 2=15%/-3, 1=20%/-4.
    The more protective load and rep reductions win; reductions are not stacked.
    """
    try:
        joint = min(5.0, max(1.0, float(joint_score)))
        total = min(15.0, max(3.0, float(readiness_score)))
    except (TypeError, ValueError):
        joint, total = 5.0, 15.0
    sleep_drive_avg = min(5.0, max(1.0, (total - joint) / 2.0))

    if sleep_drive_avg >= 4.5: fatigue_pct, fatigue_rep_drop = 0.0, 0
    elif sleep_drive_avg >= 3.5: fatigue_pct, fatigue_rep_drop = 0.05, 1
    elif sleep_drive_avg >= 2.5: fatigue_pct, fatigue_rep_drop = 0.10, 2
    elif sleep_drive_avg >= 1.5: fatigue_pct, fatigue_rep_drop = 0.15, 3
    else: fatigue_pct, fatigue_rep_drop = 0.20, 4

    joint_pct, joint_rep_drop = 0.0, 0
    if movement_type == "Compound":
        if joint >= 4.5: joint_pct, joint_rep_drop = 0.0, 0
        elif joint >= 3.5: joint_pct, joint_rep_drop = 0.05, 1
        elif joint >= 2.5: joint_pct, joint_rep_drop = 0.10, 2
        elif joint >= 1.5: joint_pct, joint_rep_drop = 0.15, 3
        else: joint_pct, joint_rep_drop = 0.20, 4

    return {
        "reduction_pct": max(fatigue_pct, joint_pct),
        "rep_drop": max(fatigue_rep_drop, joint_rep_drop),
        "sleep_drive_avg": sleep_drive_avg,
        "joint_score": joint,
    }

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


# Experimental analytical helper. Production targets use set-specific progression.
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


# Self-contained Android progression API. Avoids stale packaged service bytecode.
_PROGRESSION_CACHE={}
def invalidate_progression_settings_cache(exercise_name=None):
    _PROGRESSION_CACHE.clear()
def get_effective_progression_settings(exercise_name,movement_type,equipment_type,age=43,profile=0):
    effective=profile or (3 if age<35 else 2 if age<45 else 1)
    v={"progression_step":float(COMPOUND_JUMP_STANDARD if movement_type=="Compound" else ISOLATION_JUMP_STANDARD),"reduction_steps":1,"rep_ceiling":12 if effective==3 else 15 if effective==2 else 18,"reduction_threshold":.70,"max_progress_rpe":9.5,"max_progression_weight":None}
    try:
        with get_db() as conn:r=conn.execute("SELECT progression_mode,progression_step,reduction_steps,rep_ceiling,reduction_threshold,max_progress_rpe,max_progression_weight FROM exercise_dict WHERE name=?",(exercise_name,)).fetchone()
        if r and r[0]=="custom":
            for k,x in zip(("progression_step","reduction_steps","rep_ceiling","reduction_threshold","max_progress_rpe","max_progression_weight"),r[1:]):
                if x is not None:v[k]=x
    except Exception:pass
    return v
def classify_set_progression(aw,ar,rpe,tw,tr,nw,nr,settings):
    ar=int(ar or 0);tr=max(1,int(tr or 10));eff=float(rpe if rpe is not None else 8)
    if float(tw or 0)<float(nw if nw is not None else tw) or tr<int(nr if nr is not None else tr):return {"decision":"resume_normal","reason_code":"READINESS_RECOVERY","reason":"Temporary readiness reduction completed; resume the normal trajectory."}
    if ar/tr<float(settings.get("reduction_threshold",.7)):return {"decision":"reduce","reason_code":"SIGNIFICANT_MISS","reason":"Performance was below the reduction threshold."}
    if eff>float(settings.get("max_progress_rpe",9.5)):return {"decision":"hold","reason_code":"RPE_CEILING","reason":"Effort exceeded the progression RPE ceiling."}
    if ar>=tr:return {"decision":"progress","reason_code":"TARGET_MET","reason":"Target reps were completed within the progression RPE ceiling."}
    return {"decision":"hold","reason_code":"BUILD_REPS","reason":"Keep the load and continue building reps."}
def calculate_set_specific_progression(rows,dw,dr,movement_type,readiness_score=15,joint_score=5,equipment_type="Barbell",is_bodyweight=False,bodyweight=0,age=43,profile=0,exercise_name=None):
    settings=get_effective_progression_settings(exercise_name,movement_type,equipment_type,age,profile);out=[];diag=[]
    for i,row in enumerate(rows or [(dw,dr,8,dw,dr,dw,dr)]):
        w=float(row[0] if row[0] is not None else dw);reps=int(row[1] if row[1] is not None else dr);eff=float(row[2] if len(row)>2 and row[2] is not None else 8);tw=float(row[3] if len(row)>3 and row[3] is not None else dw);tr=int(row[4] if len(row)>4 and row[4] is not None else dr);nw=float(row[5] if len(row)>5 and row[5] is not None else tw);nr=int(row[6] if len(row)>6 and row[6] is not None else tr);res=classify_set_progression(w,reps,eff,tw,tr,nw,nr,settings);nextw=w;nextr=tr
        if res["decision"]=="reduce" and not is_bodyweight:nextw=get_prev_dumbbell(w) if equipment_type=="Dumbbell" else max(0,w-float(settings["progression_step"])*int(settings["reduction_steps"]))
        elif res["decision"]=="progress":
            if equipment_type=="Dumbbell" or is_bodyweight:
                if reps>=int(settings["rep_ceiling"]):nextw=w if is_bodyweight else get_next_dumbbell(w);nextr=max(1,int(dr or 10))
                else:nextr=reps+(2 if eff<=8 else 1)
            else:nextw=w+float(settings["progression_step"])
        elif res["decision"]=="resume_normal":nextw=nw;nextr=nr
        cap=settings.get("max_progression_weight")
        if cap is not None and nextw>=float(cap):nextw=min(nextw,float(cap));nextr=max(nextr,reps+1 if res["decision"]=="progress" and reps<int(settings["rep_ceiling"]) else reps);res={"decision":"progress" if nextr>reps else "hold","reason_code":"LOAD_CEILING_REACHED","reason":f"Load held at {float(cap):g} lb; rep progression remains available."}
        out.append({"w":nextw,"r":max(1,int(nextr))});diag.append({"set_number":i+1,"next_weight":nextw,"next_reps":max(1,int(nextr)),**res})
    return out,diag
def progression_clarity(settings,cw,cr,nw,nr,reason_code=None):
    cw=float(cw or 0);nw=float(nw or 0);cr=int(cr or 0);nr=int(nr or 0);cap=settings.get("max_progression_weight");return {"load":f"{'Load held' if nw==cw else 'Load increases' if nw>cw else 'Load reduces'}: {nw:g} lb","reps":f"{'Reps held' if nr==cr else 'Reps increase' if nr>cr else 'Reps reset'}: {nr}","at_cap":cap is not None and nw>=float(cap),"reason_code":reason_code}
def simulate_progression(settings,w,r,equipment_type="Barbell"):
    w=float(w or 0);r=int(r or 0);ceiling=int(settings["rep_ceiling"])
    if r<ceiling:return {"next_weight":w,"next_reps":r+1,"summary":f"Build reps: {w:g} x {r+1}"}
    n=get_next_dumbbell(w) if equipment_type=="Dumbbell" else w+float(settings["progression_step"]);cap=settings.get("max_progression_weight")
    if cap is not None and n>float(cap):return {"next_weight":float(cap),"next_reps":ceiling,"summary":f"Load cap: hold {float(cap):g} lb and maintain up to {ceiling} reps"}
    return {"next_weight":n,"next_reps":8,"summary":f"Graduate load: {n:g} lb, reps reset for the next climb"}

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
                SELECT weight, reps, rpe, target_weight, target_reps,
                       normal_target_weight, normal_target_reps
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
                    age=get_user_age(), profile=get_user_progression_profile(), exercise_name=exercise_name
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

        def total_plate_breakdown(load, weights):
            remaining_load = max(0.0, float(load))
            counts = []
            for plate in weights:
                count = int((remaining_load + 1e-9) // plate)
                if count:
                    counts.append((plate, count))
                    remaining_load -= count * plate
            if remaining_load > 0.01:
                return None
            return counts

        plate_mode = meta.get("plate_mode") if meta else None
        if plate_mode in ("held_total", "leg_press_total"):
            weights = meta.get("plate_weights", PLATE_WEIGHTS)
            counts = total_plate_breakdown(total_weight, weights)
            if counts is None:
                return "Exact plate mix unavailable"
            if not counts:
                return "No added plates"
            pieces = [f"{count}x{plate:g}" for plate, count in counts]
            prefix = "Hold" if plate_mode == "held_total" else "Total plates"
            return f"{prefix}: " + " + ".join(pieces)
        
        if not meta:
            ex_lower = exercise_name.lower()
            if "smith" in ex_lower:
                remaining = total_weight / 2
                bar_label = "Smith"
            elif any(x in ex_lower for x in ["dumbbell", "cable", "machine", "pulldown", "pullup", "lunges", "squat (2/3)", "candlestick", "stair", "calf", "calves", "bodyweight"]):
                return ""
            elif "ez bar" in ex_lower:
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

from exercise_catalog import *
def get_catalog_coverage():
 with get_db() as c:
  total=c.execute("SELECT COUNT(*) FROM exercise_dict").fetchone()[0];linked=c.execute("SELECT COUNT(*) FROM exercise_dict WHERE catalog_id IS NOT NULL").fetchone()[0];custom=c.execute("SELECT COUNT(*) FROM exercise_dict WHERE COALESCE(is_custom,0)=1").fetchone()[0]
 return {"total":total,"linked":linked,"custom":custom,"unlinked":total-linked}
def create_classified_exercise(name,category,family,equipment,angle="Not specified",movement_type="Isolation",catalog_id=None):
 name=str(name or "").strip()
 if not all((name,category,family,equipment)):raise ValueError("Name, category, movement family, and equipment are required.")
 if get_angle_options(family) and angle not in get_angle_options(family):raise ValueError("Choose an angle, including Not specified.")
 item=CATALOG_BY_ID.get(catalog_id) if catalog_id else None;pattern=item["pattern"] if item else movement_family_label(family)
 with get_db() as c:
  if c.execute("SELECT 1 FROM exercise_dict WHERE name=?",(name,)).fetchone():raise ValueError("Exercise already exists.")
  c.execute("INSERT INTO exercise_dict(name,category,movement_pattern,setup_notes,catalog_id,display_name,movement_family,movement_type,equipment,angle,is_custom) VALUES(?,?,?,'',?,?,?,?,?,?,?)",(name,category,pattern,catalog_id,name,family,movement_type,equipment,angle,0 if catalog_id else 1));c.commit()
 return name
def link_exercise_to_catalog(name,catalog_id):
 item=CATALOG_BY_ID.get(catalog_id)
 if not item:raise ValueError("Unknown catalog exercise.")
 with get_db() as c:c.execute("UPDATE exercise_dict SET catalog_id=?,movement_family=?,movement_type=?,equipment=?,angle=? WHERE name=?",(catalog_id,item["family"],item["movement_type"],item["equipment"],item.get("angle","Not specified"),name));c.execute("INSERT OR REPLACE INTO exercise_aliases(alias,catalog_id,exercise_name,source,confirmed) VALUES(?,?,?,?,1)",(name,catalog_id,name,"user"));c.commit()
def unlink_exercise_from_catalog(name):
 with get_db() as c:c.execute("UPDATE exercise_dict SET catalog_id=NULL WHERE name=?",(name,));c.execute("DELETE FROM exercise_aliases WHERE exercise_name=? AND source='user'",(name,));c.commit()
def probable_dictionary_duplicates():
 with get_db() as c:rows=c.execute("SELECT name,catalog_id,movement_family,equipment FROM exercise_dict ORDER BY name").fetchall()
 out=[]
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   if a[1] and a[1]==b[1] or (normalize_exercise_name(a[0])==normalize_exercise_name(b[0]) and a[0]!=b[0]):out.append({"first":a[0],"second":b[0],"reason":"same catalog identity" if a[1] and a[1]==b[1] else "same normalized name"})
 return out


def exercise_exists(exercise_name):
    name=str(exercise_name or "").strip()
    if not name:return False
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM exercise_dict WHERE name=? LIMIT 1",(name,)).fetchone() is not None


PLAN_DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
def get_plan_sessions(meso):
 with get_db() as c:rows=c.execute("SELECT id,week,day_of_week,exercise,category,status,COALESCE(schedule_origin_day,day_of_week),COALESCE(schedule_exception,0),skip_reason,COALESCE(workout_order,id),exercise_group_id,group_position FROM workout_sessions WHERE meso_number=? ORDER BY CASE WHEN week='Deload' THEN 999 ELSE CAST(week AS INTEGER) END,COALESCE(workout_order,id),id",(meso,)).fetchall()
 return [{"id":r[0],"week":r[1],"day":r[2],"exercise":r[3],"category":r[4],"status":r[5],"origin_day":r[6],"exception":bool(r[7]),"skip_reason":r[8],"workout_order":r[9],"group_id":r[10],"group_position":r[11]} for r in rows]
def plan_overview(meso):
 out={}
 for x in get_plan_sessions(meso):
  k=(x['week'],x['day']);v=out.setdefault(k,{"week":x['week'],"day":x['day'],"pending":0,"completed":0,"skipped":0,"exceptions":0});v[str(x['status']).lower()]=v.get(str(x['status']).lower(),0)+1;v['exceptions']+=int(x['exception'])
 return sorted(out.values(),key=lambda x:(-(int(x['week']) if str(x['week']).isdigit() else 999),PLAN_DAYS.index(x['day']) if x['day'] in PLAN_DAYS else 99))
def next_plan_slot(meso,week,day):
 with get_db() as c:
  cfg=c.execute("SELECT length_weeks,selected_days FROM meso_configs WHERE meso_number=?",(meso,)).fetchone()
  highest=c.execute("SELECT COALESCE(MAX(CAST(week AS INTEGER)),0) FROM workout_sessions WHERE meso_number=? AND week GLOB '[0-9]*'",(meso,)).fetchone()[0] or 0
  future_slots=c.execute("SELECT DISTINCT week,day_of_week FROM workout_sessions WHERE meso_number=? AND status=? AND week GLOB '[0-9]*'",(meso,STATUS_PENDING)).fetchall()
 configured=int(cfg[0] if cfg and cfg[0] else 0);length=max(configured,int(highest),int(week))
 try:selected=json.loads(cfg[1]) if cfg and cfg[1] else []
 except:selected=[]
 selected=[d for d in PLAN_DAYS if d in selected]
 if not selected:selected=sorted({d for _,d in future_slots if d in PLAN_DAYS},key=PLAN_DAYS.index) or PLAN_DAYS[:5]
 idx=PLAN_DAYS.index(day) if day in PLAN_DAYS else -1;existing={(str(w),d) for w,d in future_slots}
 for wk in range(int(week),length+1):
  for d in selected:
   if wk==int(week) and PLAN_DAYS.index(d)<=idx:continue
   if (str(wk),d) in existing:return str(wk),d
 return None
def preview_rollover(meso,week,day,dw,dd,ids):
 selected={int(i) for i in ids};rows=[x for x in get_plan_sessions(meso) if x['week']==str(week) and x['day']==day and x['status']==STATUS_PENDING];dest={x['exercise'] for x in get_plan_sessions(meso) if x['week']==str(dw) and x['day']==dd and x['status'] in (STATUS_PENDING,STATUS_COMPLETED)};rolled=[x for x in rows if x['id'] in selected and x['exercise'] not in dest];dups=[x for x in rows if x['id'] in selected and x['exercise'] in dest];return {"source":rows,"rolled":rolled,"duplicates":dups,"skipped":[x for x in rows if x['id'] not in selected]+dups,"result_count":len(dest)+len(rolled)}
def rollover_one_workout(meso,week,day,dw,dd,ids):
 d=preview_rollover(meso,week,day,dw,dd,ids);move={x['id'] for x in d['rolled']};dups={x['id'] for x in d['duplicates']}
 with get_db() as c:
  c.execute('BEGIN IMMEDIATE')
  for x in d['source']:
   if x['id'] in move:c.execute("UPDATE workout_sessions SET week=?,day_of_week=?,schedule_exception=1,skip_reason=NULL WHERE id=? AND status=?",(str(dw),dd,x['id'],STATUS_PENDING))
   else:c.execute("UPDATE workout_sessions SET status=?,skip_reason=? WHERE id=? AND status=?",(STATUS_SKIPPED,'rollover_destination_duplicate' if x['id'] in dups else 'missed_workout_rollover',x['id'],STATUS_PENDING))
  c.commit()
 return d
def unexpected_future_placements(meso):return [x for x in get_plan_sessions(meso) if x['status']==STATUS_PENDING and x['day']!=x['origin_day'] and not x['exception']]
def plan_diagnostics(meso):
 p=[x for x in get_plan_sessions(meso) if x['status']==STATUS_PENDING];seen=set();dups=0
 for x in p:k=(x['week'],x['day'],x['exercise']);dups+=int(k in seen);seen.add(k)
 return {"pending":len(p),"exceptions":sum(x['exception'] for x in p),"unexpected":len(unexpected_future_placements(meso)),"duplicates":dups}


def get_recurring_week_template(meso_number,source_week):
    with get_db() as c:
        cfg=c.execute("SELECT blueprint_json FROM meso_configs WHERE meso_number=?",(meso_number,)).fetchone()
        rows=c.execute("SELECT exercise,category,day_of_week,target_weight,target_reps,movement_type,COALESCE(schedule_origin_day,day_of_week) FROM workout_sessions WHERE meso_number=? AND week=? ORDER BY id",(meso_number,str(source_week))).fetchall()
        library={r[0]:r[1:] for r in c.execute("SELECT name,category,COALESCE(movement_type,'Isolation') FROM exercise_dict").fetchall()}
    latest={r[0]:r for r in rows};template=[];seen=set();blueprint={}
    try:blueprint=json.loads(cfg[0]) if cfg and cfg[0] else {}
    except Exception:blueprint={}
    if isinstance(blueprint,dict) and blueprint:
        for day in PLAN_DAYS:
            for exercise in blueprint.get(day,[]) or []:
                if exercise in seen:continue
                prior=latest.get(exercise);lib=library.get(exercise,("General","Isolation"))
                template.append({"exercise":exercise,"category":prior[1] if prior else lib[0],"day":day,"target_weight":prior[3] if prior else None,"target_reps":prior[4] if prior else None,"movement_type":prior[5] if prior else lib[1]});seen.add(exercise)
    # Preserve recurring additions absent from an older blueprint, but always use origin day.
    for r in rows:
        if r[0] in seen:continue
        template.append({"exercise":r[0],"category":r[1],"day":r[6] or r[2],"target_weight":r[3],"target_reps":r[4],"movement_type":r[5]});seen.add(r[0])
    return template

def validate_generated_week(meso_number,week):
    with get_db() as c:
        rows=c.execute("SELECT exercise,day_of_week,COALESCE(schedule_origin_day,day_of_week),COALESCE(schedule_exception,0),status FROM workout_sessions WHERE meso_number=? AND week=?",(meso_number,str(week))).fetchall()
    duplicates=len(rows)-len({(r[0],r[1]) for r in rows})
    invalid=sum(1 for r in rows if r[1]!=r[2] or r[3] or r[4]!=STATUS_PENDING)
    return {"sessions":len(rows),"duplicates":duplicates,"invalid_recurring_rows":invalid,"ok":duplicates==0 and invalid==0}


def progression_review(meso):
 with get_db() as c:rows=c.execute("SELECT ws.exercise,COALESCE(s.progression_decision,'hold'),COUNT(*),MAX(COALESCE(s.weight,0)),MAX(COALESCE(s.reps,0)),MAX(COALESCE(s.rpe,0)),ed.max_progression_weight FROM workout_sets s JOIN workout_sessions ws ON ws.id=s.session_id LEFT JOIN exercise_dict ed ON ed.name=ws.exercise WHERE ws.meso_number=? AND ws.status=? AND s.is_complete=1 GROUP BY ws.exercise,COALESCE(s.progression_decision,'hold') ORDER BY ws.exercise",(meso,STATUS_COMPLETED)).fetchall()
 out={}
 for ex,d,n,w,r,rpe,cap in rows:
  q=out.setdefault(ex,{'exercise':ex,'decisions':{},'weight':w,'reps':r,'rpe':rpe,'cap':cap});q['decisions'][d]=n
 for q in out.values():
  q['status']='load cap' if q['cap'] is not None and q['weight']>=q['cap'] else 'repeated reduction' if q['decisions'].get('reduce',0)>=2 else 'repeated hold' if q['decisions'].get('hold',0)>=3 else 'building reps' if q['decisions'].get('hold',0) else 'progressing'
 return list(out.values())
def mesocycle_health(meso):
 with get_db() as c:
  r=c.execute("SELECT status,COALESCE(schedule_exception,0),skip_reason FROM workout_sessions WHERE meso_number=?",(meso,)).fetchall();ready=c.execute("SELECT sleep,joints,drive FROM readiness_logs WHERE meso_number=?",(meso,)).fetchall()
 total=len(r);done=sum(x[0]==STATUS_COMPLETED for x in r);skip=sum(x[0]==STATUS_SKIPPED for x in r)
 return {'total':total,'completed':done,'pending':sum(x[0]==STATUS_PENDING for x in r),'skipped':skip,'completion':round(done*100/total,1) if total else 0,'exceptions':sum(bool(x[1]) for x in r),'roll_skips':sum(x[2] in ('missed_workout_rollover','rollover_destination_duplicate') for x in r),'readiness':round(sum(sum(x)/3*2 for x in ready)/len(ready),1) if ready else None}
def short_session_destinations(meso,week,day):
 idx=PLAN_DAYS.index(day);slots={(x['week'],x['day']) for x in get_plan_sessions(meso) if x['status']==STATUS_PENDING};out=[]
 for d in PLAN_DAYS[idx+1:]:
  if (str(week),d) in slots:out.append((str(week),d,False))
 for d in ('Saturday','Sunday'):
  if PLAN_DAYS.index(d)>idx and not any(x[1]==d for x in out):out.append((str(week),d,True))
 nxt=next_plan_slot(meso,week,day)
 if nxt and nxt not in [(x[0],x[1]) for x in out]:out.append((nxt[0],nxt[1],False))
 return out
def short_session_preview(meso,week,day,keep_ids,action,dest=None):
 keep={int(x) for x in keep_ids};rows=[x for x in get_plan_sessions(meso) if x['week']==str(week) and x['day']==day and x['status']==STATUS_PENDING];rem=[x for x in rows if x['id'] not in keep];dups=[];dc=0
 if action=='roll' and dest:
  dr=[x for x in get_plan_sessions(meso) if x['week']==str(dest[0]) and x['day']==dest[1] and x['status'] in (STATUS_PENDING,STATUS_COMPLETED)];dc=len(dr);names={x['exercise'] for x in dr};dups=[x for x in rem if x['exercise'] in names]
 return {'keep':len(rows)-len(rem),'remaining':rem,'roll':len(rem)-len(dups) if action=='roll' else 0,'skip':len(rem) if action=='skip' else len(dups),'duplicates':dups,'result':dc+(len(rem)-len(dups) if action=='roll' else 0)}
def apply_short_session(meso,week,day,keep_ids,action,dest=None):
 data=short_session_preview(meso,week,day,keep_ids,action,dest);dup={x['id'] for x in data['duplicates']}
 with get_db() as c:
  c.execute('BEGIN IMMEDIATE');c.execute("UPDATE workout_sessions SET session_tags=CASE WHEN instr(COALESCE(session_tags,''),'Short Session')=0 THEN TRIM(COALESCE(session_tags,'')||',Short Session',',') ELSE session_tags END WHERE meso_number=? AND week=? AND day_of_week=?",(meso,str(week),day))
  for x in data['remaining']:
   if action=='roll' and dest and x['id'] not in dup:c.execute("UPDATE workout_sessions SET week=?,day_of_week=?,schedule_exception=1,skip_reason=NULL WHERE id=? AND status=?",(str(dest[0]),dest[1],x['id'],STATUS_PENDING))
   else:c.execute("UPDATE workout_sessions SET status=?,skip_reason=? WHERE id=? AND status=?",(STATUS_SKIPPED,'short_session_destination_duplicate' if x['id'] in dup else 'short_session_skip',x['id'],STATUS_PENDING))
  c.commit()
 return data


def workout_timeline(meso,week,day):
    with get_db() as c:
        rows=c.execute("""SELECT ws.id,ws.exercise,s.set_number,s.completed_at,s.weight,s.reps,s.rpe FROM workout_sets s JOIN workout_sessions ws ON ws.id=s.session_id WHERE ws.meso_number=? AND ws.week=? AND ws.day_of_week=? AND s.is_complete=1 AND s.completed_at IS NOT NULL ORDER BY s.completed_at,s.id""",(meso,str(week),day)).fetchall()
    parsed=[]
    for row in rows:
        try:parsed.append((*row,datetime.fromisoformat(row[3])))
        except Exception:pass
    times=[x[7] for x in parsed];intervals=[max(0,int((times[i]-times[i-1]).total_seconds())) for i in range(1,len(times))]
    median=sorted(intervals)[len(intervals)//2] if intervals else None
    last_by_ex={};events=[]
    for i,x in enumerate(parsed):
        sid,ex,num,stamp,w,reps,rpe,dt=x;global_gap=max(0,int((dt-parsed[i-1][7]).total_seconds())) if i else None;same_gap=None;between=0
        if ex in last_by_ex:
            j=last_by_ex[ex];same_gap=max(0,int((dt-parsed[j][7]).total_seconds()));between=max(0,i-j-1)
        events.append({'session_id':sid,'exercise':ex,'set_number':num,'completed_at':stamp,'weight':w,'reps':reps,'rpe':rpe,'previous_exercise':parsed[i-1][1] if i else None,'previous_set':parsed[i-1][2] if i else None,'global_gap':global_gap,'same_exercise_gap':same_gap,'intervening_sets':between,'extended_global':bool(global_gap is not None and median is not None and global_gap>=median+60 and global_gap>=median*1.35)})
        last_by_ex[ex]=i
    return {'events':events,'elapsed':max(0,int((times[-1]-times[0]).total_seconds())) if len(times)>=2 else 0,'average':round(sum(intervals)/len(intervals)) if intervals else None,'median':median,'longest':max(intervals) if intervals else None}
def global_set_gap(meso,week,day,completed_at,exclude_session=None,exclude_set=None):
    try:target=datetime.fromisoformat(str(completed_at))
    except:return None
    with get_db() as c:
        row=c.execute("""SELECT s.completed_at FROM workout_sets s JOIN workout_sessions ws ON ws.id=s.session_id WHERE ws.meso_number=? AND ws.week=? AND ws.day_of_week=? AND s.is_complete=1 AND s.completed_at IS NOT NULL AND s.completed_at<? AND NOT (ws.id=? AND s.set_number=?) ORDER BY s.completed_at DESC,s.id DESC LIMIT 1""",(meso,str(week),day,str(completed_at),int(exclude_session or -1),int(exclude_set or -1))).fetchone()
    if not row:return None
    try:return max(0,int((target-datetime.fromisoformat(row[0])).total_seconds()))
    except:return None


def reorder_pending_exercise(meso,week,day,session_id,direction):
 with get_db() as c:
  rows=c.execute("SELECT id,status FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? ORDER BY COALESCE(workout_order,id),id",(meso,str(week),day)).fetchall();i=next((i for i,x in enumerate(rows) if x[0]==int(session_id)),None);j=i+direction if i is not None else -1
  if i is None or rows[i][1]!=STATUS_PENDING:raise ValueError("Only pending exercises can be reordered.")
  if j<0 or j>=len(rows):return False
  if rows[j][1]!=STATUS_PENDING:raise ValueError("Completed or skipped exercises are order-locked.")
  c.execute("UPDATE workout_sessions SET workout_order=-1 WHERE id=?",(rows[i][0],));c.execute("UPDATE workout_sessions SET workout_order=? WHERE id=?",(i+1,rows[j][0]));c.execute("UPDATE workout_sessions SET workout_order=? WHERE id=?",(j+1,rows[i][0]));c.commit();return True
def set_exercise_group(meso,week,day,ids):
 ids=[int(x) for x in ids]
 if len(ids) not in (2,3):raise ValueError("Select 2 exercises for a superset or 3 for a circuit.")
 gid="G"+datetime.now().strftime("%H%M%S%f")
 with get_db() as c:
  for pos,sid in enumerate(ids,1):
   if not c.execute("SELECT 1 FROM workout_sessions WHERE id=? AND meso_number=? AND week=? AND day_of_week=? AND status=?",(sid,meso,str(week),day,STATUS_PENDING)).fetchone():raise ValueError("Only pending exercises can be grouped.")
   c.execute("UPDATE workout_sessions SET exercise_group_id=?,group_position=? WHERE id=?",(gid,pos,sid))
  c.commit()
 return gid
def clear_exercise_group(meso,week,day,sid):
 with get_db() as c:
  r=c.execute("SELECT exercise_group_id FROM workout_sessions WHERE id=? AND status=?",(sid,STATUS_PENDING)).fetchone()
  if not r or not r[0]:return 0
  n=c.execute("UPDATE workout_sessions SET exercise_group_id=NULL,group_position=NULL WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id=? AND status=?",(meso,str(week),day,r[0],STATUS_PENDING)).rowcount;c.commit();return n


CATEGORY_DISPLAY_ORDER=["Chest","Back","Shoulders","Quads","Hamstrings","Glutes","Calves","Biceps","Triceps","Forearms","Abs","General","Custom"]
def category_sort_key(category):
 try:return (CATEGORY_DISPLAY_ORDER.index(category),str(category))
 except ValueError:return (len(CATEGORY_DISPLAY_ORDER),str(category))
def reorder_pending_exercise_in_category(meso,week,day,session_id,direction):
 with get_db() as c:
  c.execute("BEGIN IMMEDIATE");src=c.execute("SELECT category,status FROM workout_sessions WHERE id=? AND meso_number=? AND week=? AND day_of_week=?",(int(session_id),meso,str(week),day)).fetchone()
  if not src or src[1]!=STATUS_PENDING:c.rollback();raise ValueError("Only pending exercises can be reordered.")
  rows=c.execute("SELECT id,COALESCE(workout_order,id) FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND category=? AND status=? ORDER BY COALESCE(workout_order,id),id",(meso,str(week),day,src[0],STATUS_PENDING)).fetchall();i=next((i for i,r in enumerate(rows) if r[0]==int(session_id)),None);j=i+int(direction) if i is not None else -1
  if i is None or j<0 or j>=len(rows):c.rollback();return False
  a,b=rows[i],rows[j];c.execute("UPDATE workout_sessions SET workout_order=? WHERE id=?",(b[1],a[0]));c.execute("UPDATE workout_sessions SET workout_order=? WHERE id=?",(a[1],b[0]));c.commit();return True
def set_group_member_position(meso,week,day,session_id,direction):
 with get_db() as c:
  c.execute("BEGIN IMMEDIATE");r=c.execute("SELECT exercise_group_id,group_position,status FROM workout_sessions WHERE id=?",(int(session_id),)).fetchone()
  if not r or not r[0] or r[2]!=STATUS_PENDING:c.rollback();raise ValueError("Select a pending grouped exercise.")
  target=int(r[1] or 1)+int(direction);o=c.execute("SELECT id FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id=? AND group_position=? AND status=?",(meso,str(week),day,r[0],target,STATUS_PENDING)).fetchone()
  if not o:c.rollback();return False
  c.execute("UPDATE workout_sessions SET group_position=-1 WHERE id=?",(int(session_id),));c.execute("UPDATE workout_sessions SET group_position=? WHERE id=?",(int(r[1]),o[0]));c.execute("UPDATE workout_sessions SET group_position=? WHERE id=?",(target,int(session_id)));c.commit();return True
def enqueue_cloud_backup(reason):
 with get_db() as c:
  c.execute("UPDATE cloud_backup_queue SET status='coalesced' WHERE status='pending'");c.execute("INSERT INTO cloud_backup_queue(reason,queued_at,status,attempt_count) VALUES(?,?, 'pending',0)",(str(reason),datetime.now().isoformat(timespec='seconds')));c.commit()
def next_cloud_backup():
 with get_db() as c:return c.execute("SELECT id,reason,attempt_count FROM cloud_backup_queue WHERE status='pending' ORDER BY id DESC LIMIT 1").fetchone()
def finish_cloud_backup(queue_id,error=None):
 with get_db() as c:
  if error:c.execute("UPDATE cloud_backup_queue SET status='pending',attempt_count=attempt_count+1,last_error=? WHERE id=?",(str(error)[:500],int(queue_id)))
  else:c.execute("UPDATE cloud_backup_queue SET status='done',last_error=NULL WHERE id=?",(int(queue_id),))
  c.commit()
# --- 1.31 SUPERSET EXECUTION AND PLAN INTEGRITY ---
def group_label_for_session(session_id):
    with get_db() as c:
        row=c.execute("SELECT meso_number,week,day_of_week,exercise_group_id,group_position FROM workout_sessions WHERE id=?",(int(session_id),)).fetchone()
        if not row or not row[3]:return None
        groups=[r[0] for r in c.execute("SELECT exercise_group_id FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id IS NOT NULL GROUP BY exercise_group_id ORDER BY MIN(COALESCE(workout_order,id))",row[:3]).fetchall()]
    return f"{chr(65+groups.index(row[3]))}{int(row[4] or 1)}" if row[3] in groups else None

def group_next_action(meso,week,day,session_id,set_number):
    with get_db() as c:
        row=c.execute("SELECT exercise_group_id,group_position FROM workout_sessions WHERE id=?",(int(session_id),)).fetchone()
        if not row or not row[0]:return None
        members=c.execute("SELECT id,exercise,group_position FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id=? ORDER BY group_position,COALESCE(workout_order,id)",(meso,str(week),day,row[0])).fetchall()
    i=next((i for i,x in enumerate(members) if x[0]==int(session_id)),0)
    nxt=members[(i+1)%len(members)];round_no=int(set_number)+(1 if i==len(members)-1 else 0)
    return {"session_id":nxt[0],"exercise":nxt[1],"set_number":round_no,"round_complete":i==len(members)-1}

def structured_blueprint(meso):
    with get_db() as c:row=c.execute("SELECT blueprint_json FROM meso_configs WHERE meso_number=?",(meso,)).fetchone()
    try:bp=json.loads(row[0]) if row and row[0] else {}
    except Exception:bp={}
    out={}
    for day,items in (bp.items() if isinstance(bp,dict) else []):
        out[day]=[]
        for pos,item in enumerate(items or [],1):
            if isinstance(item,str):out[day].append({"exercise":item,"order":pos,"group":None,"group_position":None})
            elif isinstance(item,dict) and item.get("exercise"):out[day].append({"exercise":item["exercise"],"order":int(item.get("order",pos)),"group":item.get("group"),"group_position":item.get("group_position")})
    return out

def save_structured_blueprint_from_week(meso,week):
    with get_db() as c:
        rows=c.execute("SELECT day_of_week,exercise,COALESCE(workout_order,id),exercise_group_id,group_position FROM workout_sessions WHERE meso_number=? AND week=? AND status=? ORDER BY day_of_week,COALESCE(workout_order,id),id",(meso,str(week),STATUS_PENDING)).fetchall();bp={}
        for day,ex,order,gid,gpos in rows:bp.setdefault(day,[]).append({"exercise":ex,"order":order,"group":gid,"group_position":gpos})
        c.execute("UPDATE meso_configs SET blueprint_json=? WHERE meso_number=?",(json.dumps(bp),meso));c.commit()
    return bp

def structure_diagnostics(meso):
    with get_db() as c:
        rows=c.execute("SELECT id,week,day_of_week,status,COALESCE(workout_order,0),exercise_group_id,group_position,exercise FROM workout_sessions WHERE meso_number=?",(meso,)).fetchall()
        orphan_sets=c.execute("SELECT COUNT(*) FROM workout_sets s LEFT JOIN workout_sessions ws ON ws.id=s.session_id WHERE ws.id IS NULL").fetchone()[0]
    missing_order=sum(r[4]<=0 for r in rows);duplicate_order=0;invalid_groups=0
    slots={}
    for r in rows:slots.setdefault((r[1],r[2]),[]).append(r)
    for slot,items in slots.items():
        vals=[x[4] for x in items if x[4]>0];duplicate_order+=len(vals)-len(set(vals))
        groups={}
        for x in items:
            if x[5]:groups.setdefault(x[5],[]).append(x)
        for members in groups.values():
            positions=[x[6] for x in members];invalid_groups+=int(len(members) not in (2,3) or None in positions or len(set(positions))!=len(positions))
    base=plan_diagnostics(meso)
    return {**base,"missing_order":missing_order,"duplicate_order":duplicate_order,"invalid_groups":invalid_groups,"orphan_sets":orphan_sets,"ok":not any((base['unexpected'],base['duplicates'],missing_order,duplicate_order,invalid_groups,orphan_sets))}

def restore_future_structure(meso):
    bp=structured_blueprint(meso);changed=0
    with get_db() as c:
        c.execute("BEGIN IMMEDIATE")
        for day,items in bp.items():
            for item in items:
                rows=c.execute("SELECT id FROM workout_sessions WHERE meso_number=? AND status=? AND exercise=? AND CAST(week AS INTEGER)>=1",(meso,STATUS_PENDING,item['exercise'])).fetchall()
                for (sid,) in rows:
                    changed+=c.execute("UPDATE workout_sessions SET day_of_week=?,schedule_origin_day=?,schedule_exception=0,workout_order=?,exercise_group_id=?,group_position=? WHERE id=? AND status=?",(day,day,item['order'],item['group'],item['group_position'],sid,STATUS_PENDING)).rowcount
        c.commit()
    return changed


# --- 1.32 PROGRESSION INTELLIGENCE AND TRAINING ANALYTICS ---
def whole_exercise_progression_summary(session_id):
    with get_db() as c:
        ws=c.execute("SELECT exercise,target_weight,target_reps,movement_type,bodyweight_snapshot FROM workout_sessions WHERE id=?",(int(session_id),)).fetchone()
        rows=c.execute("SELECT weight,reps,rpe FROM workout_sets WHERE session_id=? AND is_complete=1 ORDER BY set_number",(int(session_id),)).fetchall()
    if not ws or not rows:return None
    exercise,tw,tr,mov,bw=ws;meta=EXERCISE_METADATA.get(exercise,{});settings=get_effective_progression_settings(exercise,mov or meta.get('movement_type','Isolation'),meta.get('equipment','Other'),get_user_age(),get_user_progression_profile())
    metrics=evaluate_straight_set_session(rows,tw,tr,meta.get('equipment')=='Bodyweight',bw or get_user_bodyweight())
    nw,nr,_=calculate_session_progression(rows,tw,tr,mov or 'Isolation',equipment_type=meta.get('equipment','Other'),is_bodyweight=meta.get('equipment')=='Bodyweight',bodyweight=bw or 0,age=get_user_age(),profile=get_user_progression_profile())
    reason=metrics.get('reason','Whole-exercise performance evaluated.')
    return {'exercise':exercise,'decision':metrics['decision'],'next_weight':nw,'next_reps':nr,'reason':reason,'set_count':metrics['set_count'],'completion':metrics['rep_completion_ratio'],'lowest_set':metrics['lowest_set_ratio'],'average_rpe':metrics['average_rpe'],'peak_rpe':metrics['peak_rpe'],'settings':settings}

def week_comparison(meso,first_week,second_week,category=None):
    q="""SELECT ws.week,ws.exercise,ws.category,ws.bodyweight_snapshot,s.weight,s.reps,s.rpe,s.rest_seconds,ws.exercise_group_id,s.completed_at FROM workout_sessions ws JOIN workout_sets s ON s.session_id=ws.id WHERE ws.meso_number=? AND ws.week IN (?,?) AND ws.status=? AND s.is_complete=1"""
    args=[meso,str(first_week),str(second_week),STATUS_COMPLETED]
    if category:q+=' AND ws.category=?';args.append(category)
    with get_db() as c:rows=c.execute(q,args).fetchall()
    out={str(first_week):{'volume':0,'sets':0,'rpe':[],'rest':[],'duration':0},str(second_week):{'volume':0,'sets':0,'rpe':[],'rest':[],'duration':0}}
    stamps={str(first_week):[],str(second_week):[]}
    for wk,ex,cat,bw,w,r,rpe,rest,gid,stamp in rows:
        k=str(wk);is_bw=EXERCISE_METADATA.get(ex,{}).get('equipment')=='Bodyweight';out[k]['volume']+=((float(w or 0)+float(bw or get_user_bodyweight())) if is_bw else float(w or 0))*int(r or 0);out[k]['sets']+=1
        if rpe is not None:out[k]['rpe'].append(float(rpe))
        if rest is not None:out[k]['rest'].append(float(rest))
        try:stamps[k].append(datetime.fromisoformat(stamp))
        except Exception:pass
    for k,v in out.items():
        v['average_rpe']=round(sum(v['rpe'])/len(v['rpe']),2) if v['rpe'] else None;v['average_rest']=round(sum(v['rest'])/len(v['rest'])) if v['rest'] else None;v['duration']=int((max(stamps[k])-min(stamps[k])).total_seconds()) if len(stamps[k])>1 else 0;del v['rpe'];del v['rest']
    return out

def superset_timing_analytics(meso,week,day):
    timeline=workout_timeline(meso,week,day);events=timeline['events'];transitions=[];round_recovery=[]
    with get_db() as c:groups={r[0]:(r[1],r[2]) for r in c.execute("SELECT id,exercise_group_id,group_position FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=?",(meso,str(week),day)).fetchall()}
    for e in events:
        current=groups.get(e['session_id']);prev=next((x for x in events if x['exercise']==e['previous_exercise'] and x['set_number']==e['previous_set']),None) if e['previous_exercise'] else None;prior=groups.get(prev['session_id']) if prev else None
        if current and prior and current[0] and current[0]==prior[0] and e['global_gap'] is not None:
            (round_recovery if current[1]==1 and prior[1]>1 else transitions).append(e['global_gap'])
    avg=lambda x:round(sum(x)/len(x)) if x else None
    return {'transitions':len(transitions),'average_transition':avg(transitions),'round_recoveries':len(round_recovery),'average_round_recovery':avg(round_recovery),'duration':timeline['elapsed']}


# --- 1.35 WORKOUT FLOW AND DATA MANAGEMENT ---
def resolve_next_group_step(meso,week,day,session_id,completed_set):
 with get_db() as c:
  src=c.execute("SELECT exercise_group_id,COALESCE(group_position,999) FROM workout_sessions WHERE id=?",(int(session_id),)).fetchone()
  if not src or not src[0]:return None
  members=c.execute("SELECT id,exercise,category,status,COALESCE(group_position,999) FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND exercise_group_id=? ORDER BY COALESCE(group_position,999)",(meso,str(week),day,src[0])).fetchall();cand=[]
  for sid,ex,cat,status,pos in members:
   if status!=STATUS_PENDING:continue
   sets=c.execute("SELECT set_number,is_complete FROM workout_sets WHERE session_id=? ORDER BY set_number",(sid,)).fetchall();pending=next((int(n) for n,d in sets if not d),None) if sets else 1
   if pending is not None:cand.append({'session_id':sid,'exercise':ex,'category':cat,'pending_set':pending,'position':int(pos)})
 if not cand:return None
 key=(int(completed_set or 0),int(src[1]));ordered=sorted(cand,key=lambda x:(x['pending_set'],x['position']));nxt=next((x for x in ordered if (x['pending_set'],x['position'])>key),ordered[0]);out={k:v for k,v in nxt.items() if k!='position'};out['round_complete']=(nxt['pending_set'],nxt['position'])<=key or nxt['pending_set']>int(completed_set or 0);return out
def record_audit(action,details=''):
    with get_db() as c:
        c.execute("INSERT INTO app_audit(created_at,action,details) VALUES(?,?,?)",(datetime.now().isoformat(timespec='seconds'),action,details));c.execute("DELETE FROM app_audit WHERE id NOT IN (SELECT id FROM app_audit ORDER BY id DESC LIMIT 500)");c.commit()
def recent_audit(limit=20):
    with get_db() as c:return c.execute("SELECT created_at,action,details FROM app_audit ORDER BY id DESC LIMIT ?",(int(limit),)).fetchall()
def privacy_diagnostics():
    with get_db() as c:
        integrity=c.execute("PRAGMA integrity_check").fetchone()[0];counts={t:c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ('workout_sessions','workout_sets','readiness_logs','meso_configs','app_audit')}
    return {'version':APP_VERSION,'schema':DATABASE_SCHEMA_VERSION,'integrity':integrity,'counts':counts}


def verify_restored_database(path, allow_legacy=False):
    import sqlite3
    current={'workout_sessions':{'workout_order','exercise_group_id','group_position'},'workout_sets':{'session_id','set_number'},'meso_configs':{'meso_number'},'readiness_logs':{'date'}}
    legacy={'workout_sessions':{'id','exercise'},'workout_sets':{'session_id'},'readiness_logs':{'date'}}
    required=legacy if allow_legacy else current
    c=sqlite3.connect(path)
    try:
        integrity=c.execute('PRAGMA integrity_check').fetchone()[0];missing=[]
        for table,cols in required.items():
            present={r[1] for r in c.execute(f'PRAGMA table_info({table})')}
            if not present:missing.append(table)
            else:missing.extend(f'{table}.{x}' for x in cols-present)
        orphan=0
        if not missing:orphan=c.execute('SELECT COUNT(*) FROM workout_sets s LEFT JOIN workout_sessions w ON w.id=s.session_id WHERE w.id IS NULL').fetchone()[0]
        return {'ok':integrity=='ok' and not missing and orphan==0,'integrity':integrity,'missing':missing,'orphan_sets':orphan,'mode':'legacy' if allow_legacy else 'current'}
    finally:c.close()

# Provider-neutral sync preview registry used by the 1.40 line.
def sync_status():
    with get_db() as c:
        d=c.execute("SELECT device_uuid,device_label,last_sync_at FROM sync_devices LIMIT 1").fetchone();n=c.execute("SELECT COUNT(*) FROM sync_records").fetchone()[0]
    return {'device_uuid':d[0],'device_label':d[1],'last_sync_at':d[2],'records':n,'provider':'Local package preview'}
def create_sync_package():
    with get_db() as c:
        d=c.execute("SELECT device_uuid FROM sync_devices LIMIT 1").fetchone()[0]
    return {'format':'ironcycle-sync-v1','app_version':APP_VERSION,'schema':DATABASE_SCHEMA_VERSION,'device_uuid':d,'created_at':datetime.now().isoformat(timespec='seconds'),'records':[]}
def preview_sync_package(p):
    if p.get('format')!='ironcycle-sync-v1':raise ValueError('Unsupported sync package format.')
    return {'new':0,'updates':0,'unchanged':len(p.get('records',[])),'conflicts':0}


def favorite_exercise_ids():
 with get_db() as c:return {x[0] for x in c.execute("SELECT catalog_id FROM exercise_favorites")}
def set_exercise_favorite(catalog_id,favorite=True):
 with get_db() as c:
  if favorite:c.execute("INSERT OR REPLACE INTO exercise_favorites VALUES(?,?)",(catalog_id,datetime.now().isoformat(timespec='seconds')))
  else:c.execute("DELETE FROM exercise_favorites WHERE catalog_id=?",(catalog_id,))
  c.commit()
def catalog_for_equipment(equipment=None):
 allowed=set(equipment or []);fav=favorite_exercise_ids();return sorted([x for x in BUILTIN_EXERCISE_CATALOG if not allowed or x['equipment'] in allowed or x['equipment']=='Bodyweight'],key=lambda x:(x['id'] not in fav,x['category'],x['name']))
