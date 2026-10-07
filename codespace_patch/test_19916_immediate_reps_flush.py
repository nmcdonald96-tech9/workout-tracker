from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; S=(ROOT/'main.py').read_text(encoding='utf-8')
def method(a,b):
 x=S.index(f'    def {a}('); y=S.index(f'    def {b}(',x); return S[x:y]
def test_immediate_weight_feedback_flushes_current_mounted_card():
 b=method('refresh_weight_edit_feedback','commit_weight_edit')
 assert 'mounted_card is self' in b and 'getattr(field, "page", None) is card_page' in b
 assert 'field.value = str(draft.get("r", ""))' in b and 'self.update()' in b
 assert 'field.update()' not in b and 'plate_container.update()' not in b
 assert 'self.app.replace_exercise_card_in_place(self)' in b
 assert 'request_local_card_refresh("weight_edit_feedback")' not in b
 assert 'remount_main_canvas' not in b and 'rebuild_entire_display' not in b
def test_blank_reps_keeps_separate_deferred_timing():
 blur=method('make_blur_handler','build_card'); feedback=method('refresh_weight_edit_feedback','commit_weight_edit')
 assert 'self._pending_reps_visual_refresh = True' in blur
 assert 'request_local_card_refresh("reps_restore_after_rpe")' in blur
 assert 'reps_restore_after_rpe' not in feedback
def test_weight_commit_contract_remains():
 b=method('commit_weight_edit','make_weight_commit_handler')
 assert 'apply_direct_edit(set_data, "w", raw_value)' in b
 assert 'apply_weight_derived_reps(set_data, new_w, new_target_r)' in b
 assert 'self.autosave_pending_sets()' in b and 'self.refresh_weight_edit_feedback(set_idx)' in b
def test_readiness_paused_copy_is_display_only():
 assert 'decision_label = "Paused"' in S
 assert '"Normal target preserved; resumes when readiness clears."' in S
 assert 'self.normal_set_targets[0] != self.set_targets[0]' in S
 start=S.index('        if self.set_progression_diagnostics:'); end=S.index('        if self.mov_type == "Compound"',start)
 block=S[start:end]; assert 'calculate_progression(' not in block and 'apply_weight_derived_reps(' not in block
