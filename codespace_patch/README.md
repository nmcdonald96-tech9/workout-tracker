# IronCycle 1.99.16 Codespaces patch

This package contains the immediate derived-reps flush patch, regression tests, and approved readiness wording. It creates `main.py.pre_19916_immediate_reps_patch` before writing.

## Apply from the repository root

```bash
mkdir -p codespace_patch
# Upload the extracted files into codespace_patch/
cp codespace_patch/test_19916_immediate_reps_flush.py tests/
python3 codespace_patch/apply_patch_19916.py
bash codespace_patch/verify_19916_patch.sh
pytest -q
git diff --check
git status --short
git diff -- main.py tests/test_19916_immediate_reps_flush.py
```

Do not package, push, approve 1.99.16, or promote 2.0 until physical Android acceptance passes.

## Roll back

```bash
cp main.py.pre_19916_immediate_reps_patch main.py
rm -f tests/test_19916_immediate_reps_flush.py
```
