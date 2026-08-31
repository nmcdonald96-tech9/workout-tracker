from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
main_path = ROOT / "main.py"
constants_path = ROOT / "constants.py"

if not main_path.exists() or not constants_path.exists():
    raise SystemExit("Place this script beside main.py and constants.py, then run it from the repository root.")

main = main_path.read_text(encoding="utf-8")
constants = constants_path.read_text(encoding="utf-8")

old_call = "not exercise_exists(ex_name)"
new_call = "not self.exercise_exists_locally(ex_name)"
if new_call not in main:
    if old_call not in main:
        raise SystemExit("Expected 1.14.0 Quick Add call was not found. No files were changed.")
    main = main.replace(old_call, new_call, 1)

method_name = "    def exercise_exists_locally(self, exercise_name):\n"
anchor = "    def save_wizard_addition(self, e):\n"
if method_name not in main:
    if anchor not in main:
        raise SystemExit("save_wizard_addition() anchor was not found. No files were changed.")
    helper = '''    def exercise_exists_locally(self, exercise_name):
        """Package-safe dictionary existence check used by Quick Add."""
        name = str(exercise_name or "").strip()
        if not name:
            return False
        try:
            with get_db() as conn:
                return conn.execute(
                    "SELECT 1 FROM exercise_dict WHERE name = ? LIMIT 1",
                    (name,),
                ).fetchone() is not None
        except Exception as err:
            print(f"[exercise_exists_locally] {err}")
            return False

'''
    main = main.replace(anchor, helper + anchor, 1)

if 'APP_VERSION = "1.14.1"' not in constants:
    updated, count = re.subn(r'APP_VERSION\s*=\s*"1\.14\.0"', 'APP_VERSION = "1.14.1"', constants, count=1)
    if count != 1:
        raise SystemExit("Expected APP_VERSION 1.14.0 was not found. No files were changed.")
    constants = updated

if 'DATABASE_SCHEMA_VERSION = 11' not in constants:
    raise SystemExit("Schema 11 was not found. No files were changed.")

# Secondary contract checks before writing.
compile(main, str(main_path), "exec")
compile(constants, str(constants_path), "exec")
assert old_call not in main
assert new_call in main
assert method_name in main
assert 'APP_VERSION = "1.14.1"' in constants
assert 'DATABASE_SCHEMA_VERSION = 11' in constants

main_path.with_suffix(".py.1.14.0.bak").write_text(main_path.read_text(encoding="utf-8"), encoding="utf-8")
constants_path.with_suffix(".py.1.14.0.bak").write_text(constants_path.read_text(encoding="utf-8"), encoding="utf-8")
main_path.write_text(main, encoding="utf-8")
constants_path.write_text(constants, encoding="utf-8")
print("IronCycle 1.14.1 hotfix applied successfully. Schema remains 11.")
