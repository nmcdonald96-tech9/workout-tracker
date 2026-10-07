#!/usr/bin/env bash
set -euo pipefail
test -f main.py || { echo "Run from repository root" >&2; exit 1; }
python3 -m py_compile main.py
pytest -q tests/test_19916_immediate_reps_flush.py tests/test_19916_localized_reps_sync.py
echo "Targeted verification passed. Now run: pytest -q"
