from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'main.py').read_text(encoding='utf-8')
def method(name,next_name):
    start=SOURCE.index(f'    def {name}(');end=SOURCE.index(f'    def {next_name}(',start);return SOURCE[start:end]
def test_library_progression_section_is_read_only():
    block=method('menu_manage_dict','on_dict_ex_change')
    assert 'Read-only summary. Use Open Progression Editor to make changes.' in block
    for marker in ('self.dict_progression_mode = ft.Dropdown','self.dict_progression_step = ft.TextField','self.dict_max_progression_weight = ft.TextField'):assert marker not in block
def test_library_keeps_one_authoritative_progression_editor_action():
    block=method('menu_manage_dict','on_dict_ex_change')
    assert block.count('Open Progression Editor')==2
    assert 'on_click=self.open_dictionary_progression_editor' in block and 'Reset Defaults' in block
def test_selection_updates_only_read_only_progression_controls():
    block=method('on_dict_ex_change','reset_dictionary_progression')
    assert 'mode_text = "Custom overrides" if mode == "custom" else "Inherited defaults"' in block
    assert 'self.dict_progression_preview.value' in block and 'self.dict_progression_simulation.value' in block
    assert 'self.dict_progression_mode.value' not in block and 'self.dict_progression_step.value' not in block
    assert 'for control in (self.dict_progression_preview,self.dict_progression_simulation):' in block
def test_obsolete_unsaved_library_save_path_is_removed():
    assert 'def save_dictionary_progression(' not in SOURCE
    editor=method('open_exercise_progression_editor','menu_manage_dict')
    assert 'ft.ElevatedButton("Save",on_click=save)' in editor
    assert 'invalidate_progression_settings_cache(exercise_name)' in editor
