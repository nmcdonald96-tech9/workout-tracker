import asyncio
from pathlib import Path

from app.navigation import exercise_anchor_key
import flet as ft
if not hasattr(ft, "control"):
    ft.control = lambda *args, **kwargs: (lambda cls: cls)
if not hasattr(ft, "Service"):
    ft.Service = ft.Control
ft.app = lambda *args, **kwargs: None
import main

SOURCE = Path("main.py").read_text(encoding="utf-8")


def method(start_name, end_name):
    start = SOURCE.index(f"    def {start_name}(")
    end = SOURCE.index(f"    def {end_name}(", start)
    return SOURCE[start:end]


def build_card():
    return method("build_card", "_reopen_completed")


class DummyEvent:
    def __init__(self, value=None, control=None):
        self.control = control or type(
            "DummyControl", (), {"value": value, "uid": "u1", "page": True}
        )()


class AsyncTaskRunnerPage:
    def __init__(self):
        self.scheduled_tasks = []

    def run_task(self, fn, *args, **kwargs):
        self.scheduled_tasks.append((fn, args, kwargs))

    def drain_tasks(self):
        executed = 0
        while self.scheduled_tasks:
            fn, args, kwargs = self.scheduled_tasks.pop(0)
            asyncio.run(fn(*args, **kwargs))
            executed += 1
        return executed


class DummyMainCanvas:
    def __init__(self):
        self.controls = []
        self.update_calls = 0
        self.fail_next_update = False

    def update(self):
        if self.fail_next_update:
            self.fail_next_update = False
            raise RuntimeError("simulated canvas update failure")
        self.update_calls += 1


class CoordinatorHarnessApp:
    """Uses WorkoutTrackerApp.replace_exercise_card_in_place with a real main_canvas list."""
    replace_exercise_card_in_place = main.WorkoutTrackerApp.replace_exercise_card_in_place

    def __init__(self):
        self.current_meso = 1
        self.current_week = "1"
        self.current_day = "Monday"
        self.workout_focus_mode = False
        self.ui_density = "compact"
        self.sets = {}
        self.pending_set_contexts = {}
        self.completed_revision_sessions = {}
        self.pr_celebrations = {}
        self.strength_badges = {}
        self.workout_ui_trace = []
        self.page = AsyncTaskRunnerPage()
        self.main_canvas = DummyMainCanvas()
        self.snackbars = []

    def record_workout_ui_trace(self, event, session_id, set_idx, card=None, control=None, **details):
        self.workout_ui_trace.append((event, session_id, set_idx, details))

    def get_bool_setting(self, key, default=False):
        return True

    def require_premium(self, label=""):
        return True

    def show_snackbar(self, text, color="green300"):
        self.snackbars.append((text, color))

    def mounted_card(self, session_id=10):
        wanted_key = exercise_anchor_key(session_id)
        return next(
            control for control in self.main_canvas.controls
            if getattr(control, "key", None) == wanted_key
        )


def make_mounted_card(monkeypatch):
    monkeypatch.setattr(main, "group_label_for_session", lambda sid: None)
    monkeypatch.setattr(main, "resolve_next_group_step", lambda *a, **k: None)
    monkeypatch.setattr(main, "get_user_bodyweight", lambda: 180.0)
    monkeypatch.setattr(main, "get_user_age", lambda: 44)
    monkeypatch.setattr(main, "get_user_progression_profile", lambda: 0)
    monkeypatch.setattr(main.database, "exercise_display_name", lambda name: name)
    monkeypatch.setattr(main.ft.Control, "update", lambda self: None)
    monkeypatch.setattr(main.ExerciseCard, "autosave_pending_sets", lambda self: True)
    app = CoordinatorHarnessApp()
    context = {
        "readiness_logged": False,
        "j_score": 5,
        "r_score": 15,
        "past_records": [
            (1, 1, 135.0, 12, 8.0, 135.0, 12, 135.0, 12),
            (1, 2, 135.0, 12, 8.0, 135.0, 12, 135.0, 12),
        ],
        "saved_sets": [],
        "saved_note": "",
        "snap_bw": 180.0,
        "category": "Chest",
        "previous_week_order": 1,
    }
    card = main.ExerciseCard(
        10, "Bench Press (Medium Grip)", 135.0, 12,
        "Pending", "Compound", app, context=context,
    )
    card.key = exercise_anchor_key(10)
    app.main_canvas.controls.append(card)
    return app, card


def test_handoff_marker_is_app_scoped_and_survives_build_card():
    init = SOURCE[SOURCE.index("class ExerciseCard"):SOURCE.index("    def make_rpe_updater(")]
    assert "self.committed_weight_values = {}" in init
    assert "self.app._committed_weight_values = {}" in init
    assert "self.app._reps_focus_sync_targets = set()" in init
    assert "self.app._reps_field_sync_rev = {}" in init
    assert "self._reps_focus_sync_needed" not in SOURCE
    card = build_card()
    assert "_reps_focus_sync_targets.discard" not in card
    assert "_reps_focus_sync_targets.clear" not in card
    assert "self.app._autofocus_reps_target = None" not in card


def test_autofocus_target_is_cleared_only_after_replace_exercise_card_in_place_succeeds():
    replace_block = SOURCE[
        SOURCE.index("    def replace_exercise_card_in_place("):
        SOURCE.index("    def remount_main_canvas(")
    ]
    assign_idx = replace_block.index("self.main_canvas.controls[index] = replacement")
    update_idx = replace_block.index("self.main_canvas.update()")
    clear_idx = replace_block.index("self._autofocus_reps_target = None")
    assert assign_idx < update_idx < clear_idx


def test_mounted_card_blur_first_pipeline(monkeypatch):
    app, card = make_mounted_card(monkeypatch)
    initial_key = card.reps_fields[0].key
    assert initial_key == "reps-10-0-0"

    # 1. Change LBS and commit via blur.
    card.weight_fields[0].value = "155"
    card.weight_fields[0].on_change(DummyEvent("155", card.weight_fields[0]))
    card.weight_fields[0].on_blur(DummyEvent("155", card.weight_fields[0]))

    derived_reps = app.sets[10][0]["r"]
    assert derived_reps != "12"
    assert app._reps_field_sync_rev[(10, 0)] == 1
    assert (10, 0) in app._reps_focus_sync_targets

    # 2. Simulate an intermediate card replacement before REPS focus arrives;
    #    the app-scoped handoff marker must survive card reconstruction.
    assert app.replace_exercise_card_in_place(card) is True
    reconstructed_card = app.mounted_card(10)
    assert reconstructed_card is not card
    assert (10, 0) in app._reps_focus_sync_targets

    # 3. REPS focus arrives on the mounted card and schedules async replacement.
    reconstructed_card.reps_fields[0].on_focus(
        DummyEvent(derived_reps, reconstructed_card.reps_fields[0])
    )
    assert (10, 0) not in app._reps_focus_sync_targets
    assert app._autofocus_reps_target == (10, 0)
    assert len(app.page.scheduled_tasks) == 1

    # 4. If main_canvas.update() fails during mounting, _autofocus_reps_target survives.
    app.main_canvas.fail_next_update = True
    assert app.page.drain_tasks() == 1
    assert app._autofocus_reps_target == (10, 0)

    # 5. Re-schedule and drain successfully: replacement card is mounted in main_canvas,
    #    REPS has the revision-scoped key, derived value, autofocus=True, and target is consumed.
    reconstructed_card.request_local_card_refresh("reps_focus_weight_sync")
    updates_before = app.main_canvas.update_calls
    assert app.page.drain_tasks() == 1
    assert app.main_canvas.update_calls == updates_before + 1
    mounted = app.mounted_card(10)
    assert mounted.reps_fields[0].key == "reps-10-0-1"
    assert mounted.reps_fields[0].value == derived_reps
    assert mounted.reps_fields[0].autofocus is True
    assert app._autofocus_reps_target is None


def test_mounted_card_focus_first_pipeline(monkeypatch):
    app, card = make_mounted_card(monkeypatch)
    assert card.reps_fields[0].key == "reps-10-0-0"

    # 1. Change LBS; REPS focus arrives before LBS blur.
    card.weight_fields[0].value = "165"
    card.weight_fields[0].on_change(DummyEvent("165", card.weight_fields[0]))
    card.reps_fields[0].on_focus(DummyEvent("12", card.reps_fields[0]))

    derived_reps = app.sets[10][0]["r"]
    assert derived_reps != "12"
    assert app._reps_field_sync_rev[(10, 0)] == 1
    assert app._autofocus_reps_target == (10, 0)
    assert len(app.page.scheduled_tasks) == 1

    # 2. Drain the real async refresh coordinator and verify mounted replacement.
    assert app.page.drain_tasks() == 1
    mounted = app.mounted_card(10)
    assert mounted is not card
    assert mounted.reps_fields[0].key == "reps-10-0-1"
    assert mounted.reps_fields[0].value == derived_reps
    assert mounted.reps_fields[0].autofocus is True
    assert app._autofocus_reps_target is None

    # 3. Delayed LBS blur on the same committed weight is skipped without changing REPS.
    card.weight_fields[0].on_blur(DummyEvent("165", card.weight_fields[0]))
    assert app.sets[10][0]["r"] == derived_reps
    assert app._reps_field_sync_rev[(10, 0)] == 1
    assert any(
        ev == "weight_blur_same_committed_weight_skipped"
        for ev, *_ in app.workout_ui_trace
    )


def test_live_weight_on_change_survives_card_reconstruction_before_reps_focus(monkeypatch):
    app, card = make_mounted_card(monkeypatch)
    original_committed = card.committed_weight_values[0]
    assert original_committed == str(app.sets[10][0]["w"])

    # 1. User types into LBS (on_change mutates draft["w"] and sets w_source="user",
    #    but weight is NOT yet committed).
    card.weight_fields[0].value = "155"
    card.weight_fields[0].on_change(DummyEvent("155", card.weight_fields[0]))
    assert app.sets[10][0]["w"] == "155"
    assert app.sets[10][0]["w_source"] == "user"
    assert card.committed_weight_values[0] == original_committed

    # 2. Card reconstruction occurs BEFORE weight commit.
    assert app.replace_exercise_card_in_place(card) is True
    reconstructed = app.mounted_card(10)
    assert reconstructed is not card
    # Reconstruction must keep the live draft in the field, but must NOT misclassify
    # the uncommitted live draft ("155") as the committed-weight baseline ("135.0").
    assert reconstructed.weight_fields[0].value == "155"
    assert reconstructed.committed_weight_values[0] == original_committed

    # 3. REPS focus arrives on the reconstructed card and commits the pending weight.
    reconstructed.reps_fields[0].on_focus(
        DummyEvent(reconstructed.reps_fields[0].value, reconstructed.reps_fields[0])
    )
    derived_reps = app.sets[10][0]["r"]
    assert derived_reps != "12"
    assert app._reps_field_sync_rev[(10, 0)] == 1
    assert app.page.drain_tasks() == 1

    mounted = app.mounted_card(10)
    assert mounted.reps_fields[0].key == "reps-10-0-1"
    assert mounted.reps_fields[0].value == derived_reps
    assert mounted.reps_fields[0].autofocus is True
    assert float(mounted.committed_weight_values[0]) == 155.0


def test_sequential_same_set_and_cross_set_replacements_via_coordinator(monkeypatch):
    app, _ = make_mounted_card(monkeypatch)
    seen_set1_keys = [app.mounted_card(10).reps_fields[0].key]
    seen_set2_keys = [app.mounted_card(10).reps_fields[1].key]

    # Step 1: Set 1 first weight change (135 -> 150) via focus-first
    c1 = app.mounted_card(10)
    c1.weight_fields[0].value = "150"
    c1.weight_fields[0].on_change(DummyEvent("150", c1.weight_fields[0]))
    c1.reps_fields[0].on_focus(DummyEvent(c1.reps_fields[0].value, c1.reps_fields[0]))
    assert app.page.drain_tasks() == 1
    c2 = app.mounted_card(10)
    assert c2.reps_fields[0].key not in seen_set1_keys
    seen_set1_keys.append(c2.reps_fields[0].key)

    # Step 2: Set 1 second weight change (150 -> 170) via blur-first
    c2.weight_fields[0].value = "170"
    c2.weight_fields[0].on_change(DummyEvent("170", c2.weight_fields[0]))
    c2.weight_fields[0].on_blur(DummyEvent("170", c2.weight_fields[0]))
    c2.reps_fields[0].on_focus(DummyEvent(c2.reps_fields[0].value, c2.reps_fields[0]))
    assert app.page.drain_tasks() == 1
    c3 = app.mounted_card(10)
    assert c3.reps_fields[0].key not in seen_set1_keys
    seen_set1_keys.append(c3.reps_fields[0].key)

    # Step 3: Set 2 weight change (135 -> 160) via focus-first
    c3.weight_fields[1].value = "160"
    c3.weight_fields[1].on_change(DummyEvent("160", c3.weight_fields[1]))
    c3.reps_fields[1].on_focus(DummyEvent(c3.reps_fields[1].value, c3.reps_fields[1]))
    assert app.page.drain_tasks() == 1
    c4 = app.mounted_card(10)
    assert c4.reps_fields[1].key not in seen_set2_keys
    seen_set2_keys.append(c4.reps_fields[1].key)
    assert c4.reps_fields[1].autofocus is True
    assert c4.reps_fields[0].autofocus is False

    # Step 4: Return to Set 1 for a third weight change (170 -> 190) via focus-first
    c4.weight_fields[0].value = "190"
    c4.weight_fields[0].on_change(DummyEvent("190", c4.weight_fields[0]))
    c4.reps_fields[0].on_focus(DummyEvent(c4.reps_fields[0].value, c4.reps_fields[0]))
    assert app.page.drain_tasks() == 1
    c5 = app.mounted_card(10)
    assert c5.reps_fields[0].key not in seen_set1_keys
    seen_set1_keys.append(c5.reps_fields[0].key)
    assert seen_set1_keys == [
        "reps-10-0-0", "reps-10-0-1", "reps-10-0-2", "reps-10-0-3"
    ]
    assert seen_set2_keys == ["reps-10-1-0", "reps-10-1-1"]


def test_scoped_ime_guard_and_manual_ownership_contracts(monkeypatch):
    app, card = make_mounted_card(monkeypatch)

    # 1. Typing the same numeric value into a target-owned REPS field still establishes user ownership.
    assert app.sets[10][1]["r_source"] == "target"
    card.reps_fields[1].on_change(DummyEvent("12", card.reps_fields[1]))
    assert app.sets[10][1]["r_source"] == "user"

    # 2. On a weight_derived REPS field, a no-op IME echo of the same value stays weight_derived.
    card.weight_fields[0].value = "155"
    card.weight_fields[0].on_blur(DummyEvent("155", card.weight_fields[0]))
    derived_reps = app.sets[10][0]["r"]
    assert app.sets[10][0]["r_source"] == "weight_derived"
    card.reps_fields[0].on_change(DummyEvent(derived_reps, card.reps_fields[0]))
    assert app.sets[10][0]["r_source"] == "weight_derived"

    # 3. A genuinely different REPS value on that field establishes user ownership and clears sync target.
    card.reps_fields[0].value = "15"
    card.reps_fields[0].on_change(DummyEvent("15", card.reps_fields[0]))
    assert app.sets[10][0]["r"] == "15"
    assert app.sets[10][0]["r_source"] == "user"
    assert (10, 0) not in app._reps_focus_sync_targets


def test_sync_rev_does_not_increment_on_invalid_rejected_or_unchanged_reps(monkeypatch):
    app, card = make_mounted_card(monkeypatch)
    assert app._reps_field_sync_rev.get((10, 0), 0) == 0

    # 1. Invalid non-numeric weight
    assert card.commit_weight_edit(0, "abc", "weight_blur") is False
    assert app._reps_field_sync_rev.get((10, 0), 0) == 0

    # 2. Tiny weight change that produces the same derived REPS integer.
    prior_reps = app.sets[10][0]["r"]
    committed = float(card.committed_weight_values[0])
    tiny_weight = str(committed + 0.01)
    assert card.commit_weight_edit(0, tiny_weight, "weight_blur") is True
    assert app.sets[10][0]["r"] == prior_reps
    assert app._reps_field_sync_rev.get((10, 0), 0) == 0
    assert (10, 0) not in app._reps_focus_sync_targets

    # 3. Same committed weight
    assert card.commit_weight_edit(0, tiny_weight, "weight_blur") is True
    assert app._reps_field_sync_rev.get((10, 0), 0) == 0

    # 4. Completed set is rejected
    app.sets[10][0]["done"] = True
    assert card.commit_weight_edit(0, "185", "weight_blur") is False
    assert app._reps_field_sync_rev.get((10, 0), 0) == 0
