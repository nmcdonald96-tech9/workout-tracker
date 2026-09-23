from pathlib import Path
def test_packages_and_compatibility():
 root=Path(__file__).parents[1]
 for p in ("app/__init__.py","services/__init__.py","components/__init__.py","views/__init__.py"): assert (root/p).exists()
 s=(root/"main.py").read_text(); b=s[s.index("def build_workout_context_panel"):s.index("def toggle_navigation_rows")]; assert "build_tag_controls" in b and "dense=True" not in b
def test_delegation():
 root=Path(__file__).parents[1]; assert "from services.progression_service import" in (root/"database.py").read_text(); assert "self.backup_service.create_backup_string" in (root/"main.py").read_text()