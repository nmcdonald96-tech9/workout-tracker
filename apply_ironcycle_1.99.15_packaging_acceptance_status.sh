#!/usr/bin/env bash
set -euo pipefail
ZIP="IronCycle-1.99.15-packaging-acceptance-status.zip"; SUM="IronCycle-1.99.15-packaging-acceptance-status.sha256.txt"
[ -f "$ZIP" ] && [ -f "$SUM" ] || { echo "ERROR: 1.99.15 package files are missing" >&2; exit 1; }
grep -q 'APP_VERSION = "1.99.14"' constants.py || { echo "ERROR: IronCycle 1.99.14 baseline required" >&2; exit 1; }
grep -q 'DATABASE_SCHEMA_VERSION = 20' constants.py || { echo "ERROR: schema 20 baseline required" >&2; exit 1; }
sha256sum -c "$SUM"; python -m zipfile -t "$ZIP"
python - <<'PY2'
from zipfile import ZipFile
with ZipFile("IronCycle-1.99.15-packaging-acceptance-status.zip") as z:z.extractall(".")
print("Applied IronCycle 1.99.15 packaging acceptance status release.")
PY2
FILES="main.py database.py constants.py $(find app components services views -type f -name '*.py' -print | tr '
' ' ')"
python -m py_compile $FILES
python -m pytest -q tests/test_19915_packaging_acceptance_status.py
python -m pytest -q
printf '
Applied and validated IronCycle 1.99.15.
'
