from pathlib import Path
def test_context_compatibility_factory():
 s=(Path(__file__).parents[1]/'main.py').read_text(); b=s[s.index('def build_workout_context_panel'):s.index('def toggle_navigation_rows')]
 assert 'build_tag_controls' in b and 'dense=True' not in b
