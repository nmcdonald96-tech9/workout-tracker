import os
import database


def _insert_identity(name, display_name, catalog_id, status):
 with database.get_db() as conn:
  conn.execute("DELETE FROM exercise_dict WHERE name=?", (name,))
  conn.execute("INSERT INTO exercise_dict(name,category,display_name,catalog_id,identity_status) VALUES (?,?,?,?,?)", (name,"Core",display_name,catalog_id,status))
  conn.commit()


def test_intentional_custom_identity_label(tmp_path, monkeypatch):
 monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "display.db"))
 database.init_and_seed_db()
 _insert_identity("Testing", "crazy crunch", None, "intentional_custom")
 assert database.exercise_display_name("Testing") == "crazy crunch"
 assert database.exercise_identity_label("Testing") == "crazy crunch • original: Testing"
 assert database.exercise_restore_name_label("Testing") == "Restore Original Name"
 database.restore_canonical_display_name("Testing")
 assert database.exercise_display_name("Testing") == "Testing"
 info=database.exercise_identity_info("Testing")
 assert info["identity_status"] == "intentional_custom"
 assert info["catalog_id"] is None


def test_catalog_linked_identity_label(tmp_path, monkeypatch):
 monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "catalog.db"))
 database.init_and_seed_db()
 _insert_identity("Bench Press", "Custom Bench", "bench_press", "customized_canonical")
 assert database.exercise_identity_label("Bench Press") == "Custom Bench • canonical: Bench Press"
 assert database.exercise_restore_name_label("Bench Press") == "Restore Canonical Name"


def test_surface_contract_keeps_stable_option_keys():
 source=open("main.py",encoding="utf-8").read()
 assert "ft.dropdown.Option(key=ex, text=database.exercise_display_name(ex))" in source
 assert "ft.Text(database.exercise_display_name(self.exercise)" in source
 assert "database.exercise_identity_label(ex)" in source
