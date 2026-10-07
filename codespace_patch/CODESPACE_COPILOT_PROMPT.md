# Codespaces Copilot Agent prompt

Apply and review the supplied IronCycle 1.99.16 patch without broadening scope.

The authoritative draft already calculates weight-derived reps correctly, but Android displays the result one focus event late. After weight 95 -> 245 and tapping that set's RPE, reps must already show 19. This must pass for Set 1 and Set 3 with no additional tap.

Constraints:
1. Preserve model-first weight commit, calculation, ownership, and autosave.
2. Validate that the ExerciseCard and reps field belong to the current mounted page.
3. On the valid path, update reps and plate feedback and synchronously call `self.update()` once.
4. Do not use `field.update()` or `plate_container.update()` on that path.
5. On stale ownership or update failure, immediately replace only the card using `replace_exercise_card_in_place(self)`. Do not defer weight feedback through `request_local_card_refresh`.
6. Never remount/rebuild the workout canvas, scroll, reset active state, or reset Done state.
7. Keep blank reps -> RPE restoration separate and deferred after RPE blur.
8. While a temporary readiness reduction is active, display `Progression: Paused` and `Normal target preserved; resumes when readiness clears.` This is display-only.
9. Keep version 1.99.16 and schema 20 unchanged.

Run:
```bash
python3 -m py_compile main.py
pytest -q tests/test_19916_immediate_reps_flush.py tests/test_19916_localized_reps_sync.py
pytest -q
git diff --check
git status --short
git diff -- main.py tests/test_19916_immediate_reps_flush.py
```

Report exact files changed, all test results, and confirm no version/schema/progression-algorithm change. Do not package, push, tag, approve the release, or promote 2.0.
