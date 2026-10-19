from datetime import datetime
from pathlib import Path

from services.rest_timer_service import (
    elapsed_rest_seconds,
    format_rest_elapsed,
    latest_completed_timestamp,
    rest_timer_phase,
    rest_timer_snapshot,
)


def test_elapsed_format_and_clock_rollback_are_deterministic():
    start = "2026-10-19T10:00:00"
    assert elapsed_rest_seconds(start, "2026-10-19T10:01:05") == 65
    assert elapsed_rest_seconds(start, "2026-10-19T09:59:00") == 0
    assert format_rest_elapsed(0) == "0:00"
    assert format_rest_elapsed(65) == "1:05"
    assert format_rest_elapsed(3605) == "60:05"


def test_phase_boundaries_do_not_claim_recovery():
    assert rest_timer_phase(0) == "early"
    assert rest_timer_phase(59) == "early"
    assert rest_timer_phase(60) == "middle"
    assert rest_timer_phase(119) == "middle"
    assert rest_timer_phase(120) == "extended"
    snapshot = rest_timer_snapshot("2026-10-19T10:00:00", "2026-10-19T10:02:00")
    assert snapshot.text == "REST 2:00"
    assert snapshot.phase == "extended"


def test_latest_completed_timestamp_ignores_pending_and_invalid_rows():
    sets = {
        1: [
            {"done": True, "completed_at": "2026-10-19T10:00:00"},
            {"done": False, "completed_at": "2026-10-19T10:05:00"},
        ],
        2: [
            {"done": True, "completed_at": "invalid"},
            {"done": True, "completed_at": "2026-10-19T10:03:00"},
        ],
    }
    assert latest_completed_timestamp(sets) == "2026-10-19T10:03:00"
    assert latest_completed_timestamp({}) is None


def test_sticky_header_uses_one_app_owned_ticker_and_canonical_completion():
    source = Path("main.py").read_text()
    assert "self.sticky_workout_header_host = ft.Container(" in source
    assert "self._active_rest_started_at = None" in source
    assert "self._rest_timer_task_started = False" in source
    assert "if self._rest_timer_task_started:" in source
    assert "runner(self._rest_timer_loop)" in source
    assert "await asyncio.sleep(1)" in source
    assert 'self.app.set_active_rest_start(set_data["completed_at"])' in source
    assert "self.app.sync_active_rest_from_sets()" in source


def test_ticker_updates_pill_only_and_apply_done_keeps_canonical_path():
    source = Path("main.py").read_text()
    loop = source[source.index("    async def _rest_timer_loop("):source.index("    async def reconcile_billing_ownership(")]
    assert "refresh_rest_timer_pill()" in loop
    assert "rebuild_entire_display" not in loop
    refresh = source[source.index("    def refresh_rest_timer_pill("):source.index("    def ensure_rest_timer_task(")]
    assert "text.update()" in refresh
    assert "pill.update()" in refresh
    assert "page.update()" not in refresh
    picker = source[source.index("    def make_rpe_picker_handler("):source.index("    def prepare_rep_nudge_weight(")]
    assert "self.make_set_done_handler(set_idx)(completion_event)" in picker


def test_lifecycle_resume_recalculates_and_non_workout_routes_hide_pill():
    source = Path("main.py").read_text()
    lifecycle = source[source.index("    def on_app_lifecycle_state_change("):source.index("    def generate_new_onedrive_code(")]
    assert "self._rest_timer_ui_suspended" in lifecycle
    assert "self.sync_active_rest_from_sets()" in lifecycle
    assert "self.refresh_rest_timer_pill()" in lifecycle
    refresh = source[source.index("    def refresh_rest_timer_pill("):source.index("    def ensure_rest_timer_task(")]
    assert 'visible = self.view_mode == "workout" and snapshot is not None' in refresh


def test_rest_storage_and_analytics_floor_are_untouched():
    source = Path("services/rest_timer_service.py").read_text()
    assert "UPDATE workout_sets SET rest_seconds" not in source
    assert "UPDATE workout_sets" not in source
    database = Path("database.py").read_text()
    assert "REST_ANALYTICS_MIN_EFFECTIVE_SECONDS = 60" in database
    constants = Path("constants.py").read_text()
    assert 'APP_VERSION = "2.1.0"' in constants
    assert "DATABASE_SCHEMA_VERSION = 20" in constants
