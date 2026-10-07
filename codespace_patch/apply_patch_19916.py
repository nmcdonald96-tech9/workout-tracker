#!/usr/bin/env python3
from pathlib import Path
import ast, shutil
MAIN=Path.cwd()/'main.py'; BACKUP=Path.cwd()/'main.py.pre_19916_immediate_reps_patch'
if not MAIN.exists(): raise SystemExit('ERROR: run from repository root; main.py not found')
s=MAIN.read_text(encoding='utf-8')
def swap(text,a,b,new,label):
    try: x=text.index(a); y=text.index(b,x)
    except ValueError as e: raise SystemExit(f'ERROR: expected {label} block not found; source differs from supplied 1.99.16 repomix') from e
    return text[:x]+new.rstrip()+'\n\n'+text[y:]
feedback=r'''    def refresh_weight_edit_feedback(self, set_idx):
        # Synchronize weight-derived feedback before the focus transition ends.
        try:
            draft = self.app.sets[self.db_id][set_idx]
            field = self.reps_fields[set_idx]
        except (KeyError, IndexError):
            self.app.record_workout_ui_trace("reps_update_rejected_draft", self.db_id, set_idx, self)
            return False
        wanted_key = exercise_anchor_key(self.db_id)
        try:
            mounted_card = next((control for control in self.app.main_canvas.controls if getattr(control, "key", None) == wanted_key), None)
        except (AttributeError, TypeError):
            mounted_card = None
        card_page = getattr(self, "page", None)
        card_is_current = mounted_card is self and card_page is not None and getattr(field, "page", None) is card_page
        if not card_is_current:
            self.app.record_workout_ui_trace("reps_update_stale_card", self.db_id, set_idx, self, control=field)
            return self.app.replace_exercise_card_in_place(self)
        try:
            self.app.record_workout_ui_trace("reps_update_started", self.db_id, set_idx, self, control=field)
            field.value = str(draft.get("r", ""))
            plate = calculate_plates_per_side(self.exercise, draft.get("w", 0))
            self.plate_feedback_label.value = f"Set {set_idx + 1}: {plate}" if plate else ""
            self.plate_container.visible = bool(plate)
            self.update()
            self.app.record_workout_ui_trace("reps_update_flushed", self.db_id, set_idx, self, control=field, flush_scope="card")
            return True
        except (RuntimeError, IndexError, AttributeError) as ex:
            self.app.record_workout_ui_trace("reps_update_immediate_replacement", self.db_id, set_idx, self, error=type(ex).__name__)
            return self.app.replace_exercise_card_in_place(self)'''
s=swap(s,'    def refresh_weight_edit_feedback(self, set_idx):','    def commit_weight_edit(self, set_idx, raw_value=None, event_name="weight_commit"):',feedback,'refresh_weight_edit_feedback')
readiness=r'''        if self.set_progression_diagnostics:
            first_diag = self.set_progression_diagnostics[0]
            current_ref = recent_session_sets[0] if recent_session_sets else (self.tgt_w, self.tgt_r)
            clarity = progression_clarity(effective_settings, current_ref[0], current_ref[1], first_diag.get("next_weight", self.tgt_w), first_diag.get("next_reps", self.tgt_r), first_diag.get("reason_code"))
            decision = str(first_diag.get("decision", "hold"))
            readiness_reduction_active = (
                bool(self.context)
                and bool(self.context.get("readiness_logged"))
                and self.status == STATUS_PENDING
                and self.app.current_week != "Deload"
                and bool(self.normal_set_targets)
                and bool(self.set_targets)
                and self.normal_set_targets[0] != self.set_targets[0]
            )
            if readiness_reduction_active:
                decision_label = "Paused"
            else:
                decision_label = {"progress": "Advanced", "hold": "Held", "reduce": "Reduced", "resume_normal": "Resumed normal"}.get(decision, decision.replace("_", " ").title())
            chips_row.controls.append(make_helper_chip(f"Progression: {decision_label}", "bluegrey900", "cyan100"))
            if readiness_reduction_active:
                chips_row.controls.append(make_helper_chip("Normal target preserved; resumes when readiness clears.", "bluegrey900", "cyan100"))'''
s=swap(s,'        if self.set_progression_diagnostics:\n','        if self.mov_type == "Compound" and self.app.current_week != "Deload" and self.status == STATUS_PENDING:\n',readiness,'readiness chip')
for marker in ('mounted_card is self','self.update()','replace_exercise_card_in_place(self)','decision_label = "Paused"','Normal target preserved; resumes when readiness clears.'):
    if marker not in s: raise SystemExit('ERROR: missing patched marker: '+marker)
ast.parse(s,filename=str(MAIN))
if not BACKUP.exists(): shutil.copy2(MAIN,BACKUP)
MAIN.write_text(s,encoding='utf-8')
print('Patched main.py; backup:',BACKUP); print('Syntax validation: PASS')
