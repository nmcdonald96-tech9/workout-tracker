#!/usr/bin/env bash
set -euo pipefail
ZIP="IronCycle-1.99.3-ui-trace-diagnostic.zip"; SUM="IronCycle-1.99.3-ui-trace-diagnostic.sha256.txt"
[ -f "$ZIP" ] && [ -f "$SUM" ] || { echo "ERROR: 1.99.3 files are missing" >&2; exit 1; }
grep -q 'APP_VERSION = "1.99.2"' constants.py || { echo "ERROR: IronCycle 1.99.2 baseline required" >&2; exit 1; }
sha256sum -c "$SUM"; python -m zipfile -t "$ZIP"
python - <<'PY2'
from zipfile import ZipFile
with ZipFile("IronCycle-1.99.3-ui-trace-diagnostic.zip") as z:z.extractall(".")
from pathlib import Path
for path in Path("tests").glob("test_*.py"):
    text=path.read_text(encoding="utf-8")
    text=text.replace('APP_VERSION = "1.99.2"','APP_VERSION = "1.99.3"')
    path.write_text(text,encoding="utf-8")
print("Applied IronCycle 1.99.3 UI trace diagnostic.")
PY2
FILES="main.py database.py constants.py $(find app components services views -type f -name '*.py' -print | tr '
' ' ')"
python -m py_compile $FILES
python -m pytest -q tests/test_1993_workout_ui_trace.py
python -m pytest -q
printf '
Applied and validated IronCycle 1.99.3.
'
