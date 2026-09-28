#!/usr/bin/env bash
set -euo pipefail
ZIP="IronCycle-1.95.2-corrective-patch.zip"; SUM="IronCycle-1.95.2-corrective-patch.sha256.txt"
[ -f "$ZIP" ] && [ -f "$SUM" ] || { echo "ERROR: 1.95.2 patch files are missing" >&2; exit 1; }
sha256sum -c "$SUM"; python -m zipfile -t "$ZIP"
python - <<'PY'
from pathlib import Path
from zipfile import ZipFile
root=Path('.'); cp=root/'constants.py'; mp=root/'main.py'
if not cp.is_file() or not mp.is_file():raise SystemExit('ERROR: Run from repository root.')
c=cp.read_text();
if 'APP_VERSION = "1.95.1"' not in c:raise SystemExit('ERROR: IronCycle 1.95.1 source baseline required.')
with ZipFile('IronCycle-1.95.2-corrective-patch.zip') as z:z.extractall('.')
cp.write_text(c.replace('APP_VERSION = "1.95.1"','APP_VERSION = "1.95.2"',1))
for p in (root/'tests').glob('test_*.py'):
 s=p.read_text();
 if 'APP_VERSION = "1.95.1"' in s:p.write_text(s.replace('APP_VERSION = "1.95.1"','APP_VERSION = "1.95.2"'))
s=mp.read_text()
# Replace card-local self mutation with parent ListView child replacement.
start=s.find('    def request_set_structure_refresh('); end=s.find('    def on_add_set(',start)
if start<0 or end<0:raise SystemExit('ERROR: set refresh boundary not found.')
replacement='''    def request_set_structure_refresh(self, reason):
        """Replace this card inside the mounted workout list without moving its viewport."""
        return self.app.replace_exercise_card_in_place(self)

'''
s=s[:start]+replacement+s[end:]
# Add app-level replacement coordinator before remount_main_canvas.
needle='    def remount_main_canvas(self):\n'
if needle not in s:raise SystemExit('ERROR: remount boundary not found.')
method='''    def replace_exercise_card_in_place(self, card):
        """Replace one child while preserving the existing ListView and scroll position."""
        wanted_key = exercise_anchor_key(card.db_id)
        try:
            index = next(
                i for i, control in enumerate(self.main_canvas.controls)
                if getattr(control, "key", None) == wanted_key
            )
            replacement = ExerciseCard(
                card.db_id, card.exercise, card.tgt_w, card.tgt_r,
                card.status, card.mov_type, self, context=card.context,
            )
            replacement.key = wanted_key
            self.main_canvas.controls[index] = replacement
            self.main_canvas.update()
            return True
        except Exception as ex:
            print(f"[replace_exercise_card_in_place] {ex}")
            self.show_snackbar(
                "The set was saved, but the exercise card could not refresh.",
                "amber300",
            )
            return False

'''
s=s.replace(needle,method+needle,1)
# Restore immediate superset synchronization in structure editor.
a=s.find('    def open_structure_editor('); b=s.find('    def restore_future_schedule(',a)
if a<0 or b<0:raise SystemExit('ERROR: structure editor boundary not found.')
block=s[a:b]
# Replace compact callbacks if immediate-refresh helper is absent.
if 'superset_assignment_changed' not in block:
 old="""        def group(ev=None):set_exercise_group(self.current_meso,week.value,day.value,[x['id'] for x in rows() if x['id'] in selected]);enqueue_cloud_backup('automatic: workout structure changed');self.schedule_automatic_cloud_backup();refresh(True)
        def ungroup(ev=None):
            if not selected:self.show_snackbar('Select a grouped exercise.','amber300');return
            clear_exercise_group(self.current_meso,week.value,day.value,next(iter(selected)));enqueue_cloud_backup('automatic: workout structure changed');self.schedule_automatic_cloud_backup();refresh(True)
"""
 new="""        def refresh_workout_after_group_change(message):
            self.request_structural_refresh('superset_assignment_changed',rebuild_navigation=False,remount_canvas=True)
            self.show_snackbar(message,'green300')
        def group(ev=None):
            selected_ids=[x['id'] for x in rows() if x['id'] in selected]
            if len(selected_ids)<2:self.show_snackbar('Select at least two pending exercises.','amber300');return
            set_exercise_group(self.current_meso,week.value,day.value,selected_ids);enqueue_cloud_backup('automatic: workout structure changed');self.schedule_automatic_cloud_backup();refresh(True);refresh_workout_after_group_change('Superset group created.')
        def ungroup(ev=None):
            if not selected:self.show_snackbar('Select a grouped exercise.','amber300');return
            clear_exercise_group(self.current_meso,week.value,day.value,next(iter(selected)));enqueue_cloud_backup('automatic: workout structure changed');self.schedule_automatic_cloud_backup();refresh(True);refresh_workout_after_group_change('Superset group removed.')
"""
 if old not in block:raise SystemExit('ERROR: expected 1.95.1 group callbacks not found.')
 block=block.replace(old,new,1);s=s[:a]+block+s[b:]
mp.write_text(s)
print('Applied IronCycle 1.95.2 corrective source changes.')
PY
python -m py_compile main.py database.py constants.py services/*.py app/*.py components/*.py views/*.py
python -m pytest -q tests/test_1952_mounted_list_card_replacement.py
python -m pytest -q
printf '\nApplied and validated IronCycle 1.95.2. Review git status before staging.\n'
