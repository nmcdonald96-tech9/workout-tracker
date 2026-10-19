from pathlib import Path

SOURCE = Path("main.py").read_text()


def block(start, end):
    left = SOURCE.index(start)
    right = SOURCE.index(end, left)
    return SOURCE[left:right]


def test_uncheck_persists_before_database_timer_resync():
    method = block("    def make_set_done_handler(", "    def make_live_updater(")
    mutation = 'set_data["completed_at"] = None'
    autosave = "autosaved = self.autosave_pending_sets()"
    sync = "self.app.sync_active_rest_from_sets()"
    refresh = "self.app.refresh_rest_timer_pill()"
    assert method.index(mutation) < method.index(autosave) < method.index(sync) < method.index(refresh)
    assert "if not requested_value" in method
    assert "and autosaved:" in method


def test_autosave_failure_does_not_claim_timer_authority_changed():
    method = block("    def make_set_done_handler(", "    def make_live_updater(")
    assert "if not requested_value and self.db_id not in self.app.completed_revision_sessions and autosaved:" in method
    assert method.count("autosaved = self.autosave_pending_sets()") == 1


def test_remove_set_resyncs_after_successful_atomic_save_before_local_replacement():
    method = block("    def on_remove_set(", "    def trigger_delete_warning(")
    autosave = "autosaved = self.autosave_pending_sets()"
    sync = "self.app.sync_active_rest_from_sets()"
    refresh = "self.app.refresh_rest_timer_pill()"
    replace = 'self.request_set_structure_refresh("remove_set")'
    assert method.index(autosave) < method.index(sync) < method.index(refresh) < method.index(replace)
    assert "if autosaved:" in method


def test_completed_revision_never_starts_or_resyncs_live_timer():
    method = block("    def make_set_done_handler(", "    def make_live_updater(")
    assert "if self.db_id not in self.app.completed_revision_sessions:" in method
    assert 'self.app.set_active_rest_start(set_data["completed_at"])' in method
    assert "not requested_value and self.db_id not in self.app.completed_revision_sessions and autosaved" in method


def test_normal_completion_and_rpe_apply_done_keep_canonical_path():
    done = block("    def make_set_done_handler(", "    def make_live_updater(")
    picker = block("    def make_rpe_picker_handler(", "    def prepare_rep_nudge_weight(")
    assert 'self.app.set_active_rest_start(set_data["completed_at"])' in done
    assert "self.make_set_done_handler(set_idx)(completion_event)" in picker


def test_version_schema_and_rest_analytics_contracts_stay_unchanged():
    constants = Path("constants.py").read_text()
    database = Path("database.py").read_text()
    assert 'APP_VERSION = "2.1.0"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants
    assert "REST_ANALYTICS_MIN_EFFECTIVE_SECONDS = 60" in database
