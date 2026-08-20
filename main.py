import flet as ft
import os
import sqlite3
import traceback
import json
import time
from datetime import datetime
import csv
from io import StringIO
import base64
import zlib
import http.server
import socketserver
import threading
import socket
import urllib.parse
import secrets

from constants import *
from database import *

# --- WIFI TRANSFER HARDENING ---
# Threaded server prevents browser side-requests (favicon/retries) from blocking the
# actual upload/download, and allow_reuse_address helps avoid stale socket issues.
class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

MAX_BACKUP_TEXT_BYTES = 10_000_000
MAX_DECOMPRESSED_DB_BYTES = 100_000_000

# =======================================
# --- UI COMPONENTS ---
# =======================================

def make_helper_chip(text, bgcolor, text_color):
    return ft.Container(
        content=ft.Text(text, size=10, weight="bold", color=text_color),
        bgcolor=bgcolor,
        border_radius=4,
        padding=4
    )

class WarmupChip(ft.GestureDetector):
    def __init__(self, text):
        super().__init__()
        self.text_elem = ft.Text(text, size=10, weight="bold", color="cyan100")
        self.container = ft.Container(
            content=self.text_elem,
            bgcolor="cyan900",
            border_radius=4,
            padding=4,
            opacity=1.0
        )
        self.content = self.container
        self.on_tap = self.toggle

    def toggle(self, e):
        if self.container.opacity == 1.0:
            self.container.opacity = 0.3
            self.text_elem.style = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)
        else:
            self.container.opacity = 1.0
            self.text_elem.style = None
        self.update()


class ExerciseCard(ft.Card):
    def __init__(self, db_id, exercise, tgt_w, tgt_r, status, mov_type, app_instance, context=None):
        super().__init__()
        self.db_id = db_id
        self.exercise = exercise
        self.tgt_w = tgt_w
        self.tgt_r = tgt_r
        self.status = status
        self.mov_type = mov_type
        self.app = app_instance
        self.context = context
        self.weight_fields = []
        self.reps_fields = []
        self.rpe_fields = []
        self.build_card()

    def format_target_weight(self, is_bw, weight_value):
        try:
            w_val = float(weight_value)
            if is_bw:
                return "BW" if w_val == 0 else f"BW + {w_val:g} lbs"
            return f"{w_val:g} lbs"
        except:
            return "BW" if is_bw else f"{weight_value} lbs"

    def make_rpe_updater(self, set_idx):
        def rpe_handler(ev):
            if self.db_id in self.app.sets and set_idx < len(self.app.sets[self.db_id]):
                self.app.sets[self.db_id][set_idx]["rpe"] = ev.control.value
                self.autosave_pending_sets()
        return rpe_handler

    def open_swap_dialog(self, e):
        with get_db() as conn:
            cursor = conn.cursor()
            # Find the category of the current exercise
            cursor.execute("SELECT category FROM exercise_dict WHERE name=?", (self.exercise,))
            cat_row = cursor.fetchone()
            if not cat_row: return
            
            # Fetch alternatives in the same category
            cursor.execute("SELECT name FROM exercise_dict WHERE category=? AND name!=? ORDER BY name", (cat_row[0], self.exercise))
            alts = [r[0] for r in cursor.fetchall()]

        if not alts:
            self.app.show_snackbar("No other exercises found in this category.", "amber700")
            return

        def on_swap_select(ex_name):
            with get_db() as conn:
                cursor = conn.cursor()
                # Recalculate smart target weight/reps based on your history with the NEW exercise
                new_w, new_r, new_mov = get_exercise_smart_defaults(ex_name, self.app.current_meso)
                
                # Update the session and wipe the old sets
                cursor.execute("UPDATE workout_sessions SET exercise=?, target_weight=?, target_reps=?, movement_type=? WHERE id=?",
                          (ex_name, new_w, new_r, new_mov, self.db_id))
                cursor.execute("DELETE FROM workout_sets WHERE session_id=?", (self.db_id,))
                conn.commit()

            if self.db_id in self.app.sets:
                del self.app.sets[self.db_id]
                
            self.app.safe_close(swap_dialog)
            self.app.rebuild_entire_display()

        swap_dialog = ft.AlertDialog(
            title=ft.Text(f"Swap: {self.exercise}", size=16, color="cyan300"),
            content=ft.Container(
                content=ft.Column(
                    [ft.ListTile(title=ft.Text(alt, size=14), on_click=lambda e, a=alt: on_swap_select(a)) for alt in alts],
                    scroll="auto", tight=True
                ),
                width=300, height=400
            ),
            actions=[ft.TextButton("Close", on_click=lambda e: self.app.safe_close(swap_dialog))]
        )
        self.app.safe_open(swap_dialog)

    def make_blur_handler(self, set_idx, key_type):
        # Runs once when a field loses focus -- never on every keystroke.
        # Only ever mutates self.app.sets (a plain dict, always safe) and,
        # when a visual refresh is actually needed, triggers a full
        # rebuild_entire_display(). It NEVER sets a property directly on an
        # already-mounted control -- that pattern is what threw "Frozen
        # controls cannot be updated" on the packaged Android runtime.
        def blur_handler(e):
            self.autosave_pending_sets()

            if key_type != "w":
                return  # reps/RPE blur: nothing downstream needs recomputing

            if not hasattr(self, "set_targets") or set_idx >= len(self.set_targets):
                return
            if self.db_id not in self.app.sets or set_idx >= len(self.app.sets[self.db_id]):
                return

            try:
                orig_w = float(self.set_targets[set_idx]["w"])
                orig_r = int(self.set_targets[set_idx]["r"])
            except Exception:
                return

            is_bw = EXERCISE_METADATA.get(self.exercise, {}).get("equipment") == "Bodyweight"
            bw = get_user_bodyweight() if is_bw else 0.0

            raw_val = str(self.app.sets[self.db_id][set_idx].get("w", "")).strip()
            current_r = str(self.app.sets[self.db_id][set_idx].get("r", "")).strip()
            reps_already_entered = bool(current_r)

            if raw_val in ("", ".", "-", "-."):
                # Weight cleared. Never touch a reps value the user already
                # typed -- that's a real result, not a target suggestion.
                if not reps_already_entered:
                    self.app.sets[self.db_id][set_idx]["r"] = str(orig_r)
                    self.set_targets[set_idx]["r"] = orig_r
                self.app.pending_scroll_key = self.app.exercise_anchor_key(self.db_id)
                self.app.rebuild_entire_display()
                return

            try:
                new_w = float(raw_val)
            except ValueError:
                return  # let on_save's validation catch genuinely invalid text

            if new_w == orig_w:
                return  # unchanged, nothing to recompute

            orig_e1rm = calculate_e1rm(orig_w, orig_r, bw)
            if orig_e1rm > 0 and not reps_already_entered:
                # Only auto-suggest a reps target while reps is still blank.
                # Once the user has recorded an actual result, a later weight
                # correction must never silently overwrite it.
                new_total_w = new_w + bw
                if new_total_w < orig_e1rm:
                    new_target_r = int(round(37 - (36 * new_total_w / orig_e1rm)))
                else:
                    new_target_r = 1
                new_target_r = max(1, new_target_r)
                self.app.sets[self.db_id][set_idx]["r"] = str(new_target_r)
                self.set_targets[set_idx]["r"] = new_target_r

            # Rebuild regardless of whether the reps branch above fired --
            # this is also what refreshes plate feedback, which is
            # recomputed fresh from state on every build_card() call.
            self.autosave_pending_sets()
            self.app.pending_scroll_key = self.app.exercise_anchor_key(self.db_id)
            self.app.rebuild_entire_display()
        return blur_handler

    def build_card(self):
        # --- DATA FETCHING PHASE ---
        if self.context is not None:
            readiness_logged = bool(self.context.get("readiness_logged", False))
            j_score = self.context.get("j_score", 5)
            r_score = self.context.get("r_score", 15)
            past_records = self.context.get("past_records", [])
            saved_sets = self.context.get("saved_sets", [])
            saved_note = self.context.get("saved_note", "")
        else:
            # Fallback for isolated testing
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT sleep, joints, drive FROM readiness_logs WHERE meso_number = ? AND week = ? AND day_of_week = ?", (self.app.current_meso, self.app.current_week, self.app.current_day))
                readiness_row = cursor.fetchone()
                readiness_logged = readiness_row is not None
                j_score = readiness_row[1] if readiness_logged and readiness_row[1] is not None else 5
                r_score = sum(v if v is not None else 5 for v in readiness_row[:3]) if readiness_logged else 15

                cursor.execute("""
                    SELECT ws.id, s.set_number, s.weight, s.reps, s.rpe, s.target_weight, s.target_reps, s.normal_target_weight, s.normal_target_reps
                    FROM workout_sets s 
                    JOIN workout_sessions ws ON s.session_id = ws.id 
                    WHERE ws.exercise = ? AND ws.meso_number = ? AND ws.status = 'Completed'
                    ORDER BY ws.date DESC, ws.id DESC, s.set_number ASC
                """, (self.exercise, self.app.current_meso))
                past_records = cursor.fetchall()
                
                cursor.execute("SELECT weight, reps, rpe, rest_seconds, target_weight, target_reps, normal_target_weight, normal_target_reps, completed_at, is_complete FROM workout_sets WHERE session_id = ? ORDER BY set_number ASC", (self.db_id,))
                saved_sets = cursor.fetchall()
                
                cursor.execute("SELECT setup_notes FROM exercise_dict WHERE name = ?", (self.exercise,))
                notes_row = cursor.fetchone()
                saved_note = notes_row[0] if notes_row and notes_row[0] else ""
        
        # Isolate the most recent completed session and preserve straight-set order.
        recent_session_sets = []
        if past_records:
            latest_session_id = past_records[0][0]
            for row in past_records:
                if row[0] != latest_session_id:
                    break
                try:
                    recent_session_sets.append((row[2], row[3], row[4], row[5], row[6], row[7], row[8]))
                except (IndexError, TypeError):
                    pass

        # UI hints now come from the latest session only, not a flattened history.
        past_w_list = [str(r[0]) for r in recent_session_sets]
        past_r_list = [str(r[1]) for r in recent_session_sets]
        past_rpe_list = [str(r[2]) for r in recent_session_sets]

        # --- EQUIPMENT & PROG MATH ---
        is_bw = EXERCISE_METADATA.get(self.exercise, {}).get("equipment") == "Bodyweight"
        eq_type = EXERCISE_METADATA.get(self.exercise, {}).get("equipment", "Barbell")
        
        def snap_weight(w, eq):
            if eq == "Bodyweight": return w
            if eq == "Dumbbell":
                rack = [2.5, 5.0, 7.5, 10.0, 12.5, 15.0] + [float(x) for x in range(20, 105, 5)]
                return min(rack, key=lambda x: abs(x - w))
            if eq == "Barbell":
                return round(w / 5.0) * 5.0
            return round(w / 2.5) * 2.5
        
        regulation_msg = ""
        readiness_applies = (
            readiness_logged
            and self.status == STATUS_PENDING
            and self.app.current_week != "Deload"
        )
        if readiness_applies:
            readiness_adj = get_readiness_adjustment(r_score, j_score, self.mov_type)
            reduction_pct = readiness_adj["reduction_pct"]
            rep_drop = readiness_adj["rep_drop"] if reduction_pct > 0 else 0
        else:
            reduction_pct = 0.0
            rep_drop = 0
        self.set_progression_diagnostics = []

        # Build the unregulated trajectory first.
        self.normal_set_targets = []
        if recent_session_sets:
            try:
                if self.app.current_week == "Deload":
                    for row in recent_session_sets:
                        prior_w = float(row[0])
                        prior_r = max(1, int(row[1]) // 2)
                        deload_w = prior_w if is_bw else snap_weight(prior_w * DELOAD_PERCENTAGE, eq_type)
                        self.normal_set_targets.append({"w": deload_w, "r": prior_r})
                else:
                    raw_targets, self.set_progression_diagnostics = calculate_set_specific_progression(
                        recent_session_sets, self.tgt_w, self.tgt_r, self.mov_type,
                        readiness_score=15, joint_score=5, equipment_type=eq_type,
                        is_bodyweight=is_bw, bodyweight=get_user_bodyweight(),
                        age=get_user_age(), profile=get_user_progression_profile()
                    )
                    self.normal_set_targets = [
                        {"w": snap_weight(t["w"], eq_type), "r": max(1, int(t["r"]))}
                        for t in raw_targets
                    ]
            except Exception as ex:
                print(f"Set-specific progression fallback for {self.exercise}: {ex}")
                self.normal_set_targets = []

        normal_seed_w = self.normal_set_targets[0]["w"] if self.normal_set_targets else self.tgt_w
        normal_seed_r = self.normal_set_targets[0]["r"] if self.normal_set_targets else self.tgt_r
        while len(self.normal_set_targets) < 20:
            self.normal_set_targets.append({"w": normal_seed_w, "r": normal_seed_r})

        # Apply today's temporary reduction only to the displayed/logged targets.
        self.set_targets = []
        for normal_target in self.normal_set_targets:
            regulated_w = normal_target["w"]
            regulated_r = normal_target["r"]
            if reduction_pct > 0:
                regulated_w = normal_target["w"] if is_bw else snap_weight(normal_target["w"] * (1.0 - reduction_pct), eq_type)
                regulated_r = max(1, int(normal_target["r"]) - int(rep_drop))
            self.set_targets.append({"w": regulated_w, "r": regulated_r})

        adj_w, adj_r = self.set_targets[0]["w"], self.set_targets[0]["r"]
        base_target_w, base_target_r = adj_w, adj_r
        if reduction_pct > 0:
            pct_label = round(reduction_pct * 100, 1)
            regulation_msg = f"Today only: -{pct_label:g}% Lbs"
            if rep_drop:
                regulation_msg += f", -{rep_drop} Reps"
        default_sets = 1 if r_score <= 7 else 2

        # --- AUTOSAVE NOTE ---
        def save_note_on_blur(e):
            new_note = self.notes_field.value.strip()
            try:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM exercise_dict WHERE name = ?", (self.exercise,))
                    if cursor.fetchone():
                        cursor.execute("UPDATE exercise_dict SET setup_notes = ? WHERE name = ?", (new_note, self.exercise))
                    else:
                        cursor.execute("INSERT INTO exercise_dict (name, category, movement_pattern, setup_notes) VALUES (?, 'General', 'General', ?)", (self.exercise, new_note))
                    conn.commit()
            except Exception as ex:
                print(f"Error autosaving note: {ex}")

        self.notes_field = ft.TextField(
            value=saved_note,
            hint_text="✎ Setup notes...",
            text_size=10,
            height=30,
            content_padding=10,
            bgcolor="white10",
            border_radius=6,
            border_color="transparent",
            expand=True, # <-- Add this line
            on_blur=save_note_on_blur
        )
        
        # --- INITIALIZE DICT ---
        if self.db_id not in self.app.sets:
            self.app.sets[self.db_id] = []
            if saved_sets:
                for idx, (sw, sr, srpe, s_rest, stw, strp, normal_tw, normal_tr, completed_at, is_complete) in enumerate(saved_sets):
                    w_str = str(sw) if sw is not None and str(sw) != "None" else ""
                    r_str = str(sr) if sr is not None and str(sr) != "None" else ""
                    rpe_str = str(srpe) if srpe is not None and str(srpe) != "None" else ""
                    if stw is not None and strp is not None and idx < len(self.set_targets):
                        self.set_targets[idx] = {"w": float(stw), "r": int(strp)}
                    if normal_tw is not None and normal_tr is not None and idx < len(self.normal_set_targets):
                        self.normal_set_targets[idx] = {"w": float(normal_tw), "r": int(normal_tr)}
                    self.app.sets[self.db_id].append({
                        "w": w_str, "r": r_str, "rpe": rpe_str, "rest": s_rest,
                        "completed_at": completed_at, "done": bool(is_complete)
                    })
            else:
                num_sets = len(recent_session_sets) if recent_session_sets else default_sets
                num_sets = max(1, num_sets)
                for idx in range(num_sets):
                    target = self.set_targets[idx]
                    self.app.sets[self.db_id].append({
                        "w": str(target["w"]), "r": "", "rpe": "", "rest": None,
                        "completed_at": None, "done": False
                    })

        # --- UI CONSTRUCTION ---
        sets_column = ft.Column(spacing=4)
        self.set_ui_rows = [] # <-- KINETIC INIT

        # Kinetic dimming state -- computed here (before plate feedback and
        # the row loop below) so both can share it instead of scanning
        # self.app.sets twice. Never mutated on an already-mounted control
        # afterward; baked into initial construction only. That
        # mutate-after-mount pattern is what threw "Frozen controls cannot
        # be updated" on the packaged Android runtime.
        #
        # Uses the explicit "done" flag, not field-emptiness -- pre-filling
        # all sets' weight/reps/RPE before checking any Done box must not
        # make the row dimming think every set is already completed.
        kinetic_active_idx = -1
        for i, s in enumerate(self.app.sets.get(self.db_id, [])):
            if not bool(s.get("done")):
                kinetic_active_idx = i
                break

        # Plate feedback follows this same active set (first not-Done, or
        # the last set once everything is Done) rather than always Set 1.
        if kinetic_active_idx != -1:
            plate_active_idx = kinetic_active_idx
        elif self.app.sets.get(self.db_id):
            plate_active_idx = len(self.app.sets[self.db_id]) - 1
        else:
            plate_active_idx = 0

        active_weight = 0
        if self.app.sets.get(self.db_id) and plate_active_idx < len(self.app.sets[self.db_id]):
            active_weight = self.app.sets[self.db_id][plate_active_idx].get("w", 0)

        plate_text = calculate_plates_per_side(self.exercise, active_weight)
        plate_display_text = f"Set {plate_active_idx + 1}: {plate_text}" if plate_text else ""
        self.plate_feedback_label = ft.Text(value=plate_display_text, size=10, font_family="monospace", color="cyan100")
        self.plate_container = ft.Container(
            content=self.plate_feedback_label, 
            bgcolor="bluegrey900", 
            border_radius=4, 
            padding=4, 
            visible=bool(plate_text)
        )

        self.rpe_warning = ft.Container(
            content=ft.Text("⚠️ Max effort reached. Drop weight or scratch next set to manage fatigue.", color="amber300", size=10, weight="bold"),
            bgcolor="amber900", padding=4, border_radius=4, visible=False
        )

        for idx, set_data in enumerate(self.app.sets[self.db_id]):
            set_num = idx + 1
            w_hint = str(self.set_targets[idx]["w"]) if idx < len(self.set_targets) else str(adj_w)
            r_hint = str(self.set_targets[idx]["r"]) if hasattr(self, 'set_targets') and idx < len(self.set_targets) else str(adj_r)
            rpe_hint = past_rpe_list[idx].strip() if idx < len(past_rpe_list) else "8"

            # Clean, bold set number outside the box
            set_indicator = ft.Text(f"{set_num}", size=14, weight="bold", color="white54", width=18, text_align="center")

            # Borderless, filled TextFields
            w_f = ft.TextField(
                value=set_data["w"],
                label="LBS",
                hint_text=str(w_hint),
                hint_style=ft.TextStyle(color="white54", size=12),
                label_style=ft.TextStyle(color="cyan200", size=10, weight="bold"),
                expand=3,
                text_size=15,
                content_padding=8,
                bgcolor="white5", # Soft dark fill
                border_color="transparent", # Removes the archaic outline
                border_radius=6,
                text_align="center",
                keyboard_type=ft.KeyboardType.NUMBER
            )
            w_f.on_change = self.make_live_updater(idx, "w")
            w_f.on_blur = self.make_blur_handler(idx, "w")

            r_f = ft.TextField(
                value=set_data["r"],
                label="REPS",
                hint_text=str(r_hint),
                hint_style=ft.TextStyle(color="white54", size=12),
                label_style=ft.TextStyle(color="cyan200", size=10, weight="bold"),
                expand=2,
                text_size=15,
                content_padding=8,
                bgcolor="white5",
                border_color="transparent",
                border_radius=6,
                text_align="center",
                keyboard_type=ft.KeyboardType.NUMBER
            )
            r_f.on_change = self.make_live_updater(idx, "r")
            r_f.on_blur = self.make_blur_handler(idx, "r")

            rpe_f = ft.TextField(
                value=set_data["rpe"],
                label="RPE",
                hint_text=str(rpe_hint),
                hint_style=ft.TextStyle(color="white54", size=12),
                label_style=ft.TextStyle(color="cyan200", size=10, weight="bold"),
                expand=2,
                text_size=15,
                content_padding=8,
                bgcolor="white5",
                border_color="transparent",
                border_radius=6,
                text_align="center",
                keyboard_type=ft.KeyboardType.NUMBER
            )
            rpe_f.on_change = self.make_rpe_updater(idx)
            rpe_f.on_blur = self.make_blur_handler(idx, "rpe")

            self.weight_fields.append(w_f)
            self.reps_fields.append(r_f)
            self.rpe_fields.append(rpe_f)

            done_checkbox = ft.Checkbox(
                label="Done",
                value=bool(set_data.get("done")),
                disabled=(self.status == STATUS_COMPLETED),
                on_change=self.make_set_done_handler(idx),
                width=70,
                label_style=ft.TextStyle(size=11, color="white70"),
            )
            
            # Explicit completion controls rest timing. Editing planned values never starts a timer.
            set_row = ft.Row([set_indicator, w_f, r_f, rpe_f, done_checkbox], alignment="start", vertical_alignment="center", spacing=6)

            # Kinetic dimming, baked in at construction (see kinetic_active_idx above).
            if idx < kinetic_active_idx or kinetic_active_idx == -1:
                row_opacity, row_bgcolor = 0.4, None   # completed, dimmed
            elif idx == kinetic_active_idx:
                row_opacity, row_bgcolor = 1.0, "white10"  # active, highlighted
            else:
                row_opacity, row_bgcolor = 0.8, None   # upcoming

            # Rest-time caption: only for already-completed sets that have a
            # computed gap (set 1 of an exercise never has one -- no prior
            # set to compare against, which is intentional, not a bug).
            rest_secs = set_data.get("rest")
            rest_str = format_duration_seconds(rest_secs)
            if self.status == STATUS_COMPLETED and rest_str is not None:
                rest_caption = ft.Text(
                    f"⏱️ {rest_str} since previous set",
                    size=10, color="white38", italic=True
                )
                row_container = ft.Container(
                    content=ft.Column([set_row, rest_caption], spacing=2, tight=True),
                    padding=6, border_radius=8,
                    opacity=row_opacity, bgcolor=row_bgcolor
                )
            else:
                row_container = ft.Container(
                    content=set_row, padding=6, border_radius=8,
                    opacity=row_opacity, bgcolor=row_bgcolor
                )

            self.set_ui_rows.append(row_container)
            sets_column.controls.append(row_container)

        type_code = "CP" if self.mov_type == "Compound" else "IS"
        e1rm_display_str = ""

        status_color = "grey600"
        status_text_color = "grey300"
        status_bg_color = "white10"
        accent_color = "blue400" 
        
        if self.context is not None:
            snap_bw = self.context.get("snap_bw", None)
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT bodyweight_snapshot FROM workout_sessions WHERE id = ?", (self.db_id,))
                row = cursor.fetchone()
                snap_bw = row[0] if row else None
            
        current_bw = get_user_bodyweight()
        bw = (snap_bw if snap_bw is not None else current_bw) if is_bw else 0.0

        if self.status == STATUS_COMPLETED:
            status_color = "green400"
            status_text_color = "green100"
            status_bg_color = "green900"
            accent_color = "green500"
            try:
                calculated_max = calculate_e1rm(self.app.sets[self.db_id][0]['w'], self.app.sets[self.db_id][0]['r'], bw)
                if calculated_max > 0:
                    e1rm_display_str = f" | e1RM: {calculated_max}"
            except Exception: pass
        elif self.status == STATUS_PENDING:
            status_color = "blue200"
            status_text_color = "blue100"
            status_bg_color = "blue900"
            calculated_target_max = calculate_e1rm(base_target_w, base_target_r, bw)
            if calculated_target_max > 0:
                e1rm_display_str = f" | Max: {calculated_target_max}"
        elif self.status == STATUS_SKIPPED:
            status_color = "white30"
            accent_color = "grey800"

        status_chip = ft.Container(
            content=ft.Text(self.status.upper(), size=9, weight="bold", color=status_text_color),
            bgcolor=status_bg_color,
            border_radius=12,
            padding=4
        )

        title_zone = ft.Column([
            # Top Floor: Title, Swap Button, Status Chip
            ft.Row([
                ft.Row([
                    ft.Text(f"{self.exercise}", size=14, weight="bold", color="white"),
                    ft.TextButton(content=ft.Text("🔄", size=14, color="cyan300"), style=ft.ButtonStyle(padding=2), on_click=self.open_swap_dialog)
                ], spacing=2, expand=True),
                ft.Row([
                    ft.Container(
                        content=ft.Text(f"Prev #{(self.context or {}).get('previous_week_order')}", size=9, weight="bold", color="amber200"),
                        bgcolor="amber900", border_radius=10, padding=4,
                        visible=bool(self.context and self.context.get("previous_week_order"))
                    ),
                    status_chip
                ], spacing=5)
            ], alignment="spaceBetween"),
            
            # Bottom Floor: e1RM text and Notes Field
            ft.Row([
                ft.Text(f"{type_code}{e1rm_display_str}", size=11, color="white54"),
                self.notes_field
            ], alignment="spaceBetween", spacing=10)
        ], spacing=4)
        
        display_weight = self.format_target_weight(is_bw, base_target_w)
        self.target_banner_text = ft.Text(f"🎯 Target: {display_weight} x {base_target_r}  |  RPE Goal: 8-9", color="blue200", size=12, weight="bold")
        
        target_banner = ft.Container(
            content=self.target_banner_text,
            padding=4,
            visible=(self.status == STATUS_PENDING)
        )

        chips_row = ft.Row(spacing=6, wrap=True)
        
        if regulation_msg:
            chips_row.controls.append(make_helper_chip(regulation_msg, "red900", "red100"))
        
        if self.mov_type == "Compound" and self.app.current_week != "Deload" and self.status == STATUS_PENDING:
            w1 = snap_weight(adj_w * WARMUP_PERCENT_1, eq_type)
            w2 = snap_weight(adj_w * WARMUP_PERCENT_2, eq_type)
            if not is_bw:
                chips_row.controls.append(WarmupChip(f"Warm-Up: {w1}x5"))
                chips_row.controls.append(WarmupChip(f"Warm-Up: {w2}x3"))
            
        if self.db_id in self.app.pr_celebrations:
            chips_row.controls.append(make_helper_chip("🎉 NEW PR!", "amber900", "amber100"))

        if self.db_id in self.app.strength_badges:
            cls = self.app.strength_badges[self.db_id]
            top_pct = max(0.5, 100 - cls["percentile"])
            chips_row.controls.append(make_helper_chip(f"🏆 Top {top_pct:.0f}% ({cls['level']})", "purple900", "purple100"))
            
        chips_row.controls.append(self.plate_container)
        helper_zone = ft.Container(content=chips_row, margin=4) if chips_row.controls else ft.Container()

        # Softer utility buttons
        minus_btn = ft.TextButton(content=ft.Text("—", color="white54", size=20, weight="bold"), style=ft.ButtonStyle(padding=8), on_click=self.on_remove_set)
        plus_btn = ft.TextButton(content=ft.Text("+", color="white54", size=20, weight="bold"), style=ft.ButtonStyle(padding=8), on_click=self.on_add_set)
        
        delete_btn = ft.TextButton(content=ft.Text("Delete", size=13, color="white30"), style=ft.ButtonStyle(padding=8), on_click=self.trigger_delete_warning)
        
        if self.status in [STATUS_SKIPPED, STATUS_COMPLETED]:
            skip_btn = ft.TextButton(content=ft.Text("Unskip", size=13, color="cyan300"), style=ft.ButtonStyle(padding=8), on_click=self.on_unskip)
        else:
            skip_btn = ft.TextButton(content=ft.Text("Skip", size=13, color="white54"), style=ft.ButtonStyle(padding=8), on_click=self.on_skip)
            
        # Premium primary action button
        log_btn = ft.ElevatedButton(
            content=ft.Text("LOG SETS", size=14, weight="w900", color="grey900"), 
            on_click=self.on_save, 
            height=44, 
            style=ft.ButtonStyle(bgcolor="cyan300", shape=ft.RoundedRectangleBorder(radius=8))
        )

        action_zone = ft.Row([
            ft.Row([delete_btn, skip_btn], spacing=0),  
            ft.Row([minus_btn, plus_btn], spacing=2),   
            log_btn                                     
        ], alignment="spaceBetween")

        card_body = ft.Column([
            title_zone,
            target_banner,
            helper_zone,
            sets_column,
            self.rpe_warning,
            action_zone
        ], spacing=6, expand=True)
        
        accent_bar = ft.Container(width=4, bgcolor=accent_color, border_radius=4)
        
        self.content = ft.Container(
            content=ft.Row([accent_bar, card_body], spacing=10),
            padding=10,
            border_radius=8,
            bgcolor="white10"
        )
        self.margin = 4

    def make_set_done_handler(self, set_idx):
        def set_done_changed(ev):
            if self.db_id not in self.app.sets or set_idx >= len(self.app.sets[self.db_id]):
                return
            set_data = self.app.sets[self.db_id][set_idx]
            exercise_was_started = any(bool(s.get("done")) for s in self.app.sets.get(self.db_id, []))
            if ev.control.value:
                w_raw = str(set_data.get("w", "")).strip()
                r_raw = str(set_data.get("r", "")).strip()
                rpe_raw = str(set_data.get("rpe", "")).strip()
                if not w_raw or not r_raw or not rpe_raw:
                    # Do not mutate the mounted checkbox. Rebuild from unchanged
                    # state so older Android Flet runtimes cannot freeze-crash.
                    self.app.show_snackbar(f"Enter weight, reps, and RPE before completing Set {set_idx + 1}.", "red300")
                    self.app.rebuild_entire_display()
                    return
                # Same numeric check on_save already enforces -- catch it here too
                # so "Done" can never go green on garbage data. Same rebuild-to-revert
                # pattern as the empty-field case above; no direct control mutation.
                try:
                    float(w_raw)
                except ValueError:
                    self.app.show_snackbar(f"Set {set_idx + 1} weight must be numeric.", "red300")
                    self.app.rebuild_entire_display()
                    return
                try:
                    int(r_raw)
                except ValueError:
                    self.app.show_snackbar(f"Set {set_idx + 1} reps must be a whole number.", "red300")
                    self.app.rebuild_entire_display()
                    return
                try:
                    float(rpe_raw)
                except ValueError:
                    self.app.show_snackbar(f"Set {set_idx + 1} RPE must be numeric.", "red300")
                    self.app.rebuild_entire_display()
                    return
                set_data["done"] = True
                set_data["completed_at"] = datetime.now().isoformat(timespec="seconds")
            else:
                set_data["done"] = False
                set_data["completed_at"] = None
            self.autosave_pending_sets()
            if ev.control.value and not exercise_was_started:
                category_name = self.context.get("category") if self.context else None
                self.app.activate_exercise(category_name, self.db_id)  # rebuilds internally
            else:
                # Dimming is baked into initial row construction (see build_card),
                # so a fresh rebuild is all that's needed to reflect the new state --
                # no direct mutation of the already-mounted rows.
                self.app.rebuild_entire_display()
        return set_done_changed

    def make_live_updater(self, set_idx, key_type):
        # on_change fires on every keystroke -- must stay completely inert
        # from a UI-mutation standpoint. All the heavier recompute work
        # (plate feedback, reps-target recalculation) lives in the
        # corresponding blur handler instead, which fires once per field.
        def live_update_event(ev):
            raw_val = ev.control.value
            if self.db_id in self.app.sets and set_idx < len(self.app.sets[self.db_id]):
                self.app.sets[self.db_id][set_idx][key_type] = raw_val
                self.autosave_pending_sets()
        return live_update_event

    def autosave_pending_sets(self):
        # Quietly saves the current draft to the database without finalizing the workout
        if self.db_id not in self.app.sets: return
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workout_sets WHERE session_id = ?", (self.db_id,))
                for i, s_data in enumerate(self.app.sets[self.db_id], start=1):
                    w_val = float(s_data["w"]) if str(s_data.get("w", "")).strip() else None
                    r_val = int(s_data["r"]) if str(s_data.get("r", "")).strip() else None
                    rpe_val = float(s_data["rpe"]) if str(s_data.get("rpe", "")).strip() else None
                    
                    target = self.set_targets[i - 1] if i - 1 < len(self.set_targets) else {"w": self.tgt_w, "r": self.tgt_r}
                    normal_target = self.normal_set_targets[i - 1] if i - 1 < len(self.normal_set_targets) else target
                    completed_at = s_data.get("completed_at")
                    done = 1 if s_data.get("done") else 0
                    rest_secs = None
                    if done and completed_at and i > 1:
                        prev_completed = self.app.sets[self.db_id][i - 2].get("completed_at")
                        if prev_completed:
                            try:
                                rest_secs = max(0, int(round((datetime.fromisoformat(completed_at) - datetime.fromisoformat(prev_completed)).total_seconds())))
                            except Exception:
                                rest_secs = None
                    cursor.execute("""
                        INSERT INTO workout_sets
                            (session_id, set_number, weight, reps, rpe, rest_seconds, target_weight, target_reps, normal_target_weight, normal_target_reps, completed_at, is_complete)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (self.db_id, i, w_val, r_val, rpe_val, rest_secs,
                          float(target["w"]), int(target["r"]), float(normal_target["w"]), int(normal_target["r"]), completed_at, done))
                conn.commit()
        except Exception as e:
            print(f"Error autosaving pending sets: {e}")

    def on_add_set(self, ev):
        if self.db_id not in self.app.sets: return
        last_w = self.app.sets[self.db_id][-1].get("w", "") if self.app.sets[self.db_id] else str(self.tgt_w)
        self.app.sets[self.db_id].append({"w": last_w, "r": "", "rpe": "", "rest": None, "completed_at": None, "done": False})
        self.autosave_pending_sets() # Force save draft
        self.app.rebuild_entire_display()

    def on_remove_set(self, ev):
        if self.db_id not in self.app.sets or len(self.app.sets[self.db_id]) <= 1:
            return
        self.app.sets[self.db_id] = self.app.sets[self.db_id][:-1]
        self.autosave_pending_sets() # Force save draft
        self.app.rebuild_entire_display()

    def trigger_delete_warning(self, ev):
        self.app.delete_dialog_id = self.db_id
        self.app.delete_dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete", size=15, weight="bold"),
            content=ft.Text(f"Remove exercise from today's routine?", size=12),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=self.app.close_delete_dialog),
                ft.ElevatedButton(content=ft.Text("Delete"), style=ft.ButtonStyle(bgcolor="red700"), on_click=self.app.confirm_delete)
            ], actions_alignment="end"
        )
        self.app.safe_open(self.app.delete_dialog)

    def on_skip(self, ev):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE workout_sessions SET status = '{STATUS_SKIPPED}' WHERE id = ?", (self.db_id,))
            conn.commit()
        if self.db_id in self.app.sets:
            del self.app.sets[self.db_id]

        try:
            self.app.check_and_route_day()
        except Exception as e:
            print(f"[on_skip] check_and_route_day failed: {e}")

        try:
            self.app.rebuild_navigation_headers()
        except Exception as e:
            print(f"[on_skip] rebuild_navigation_headers failed: {e}")

        self.app.rebuild_entire_display()

    def on_unskip(self, ev):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE workout_sessions SET status = '{STATUS_PENDING}' WHERE id = ?", (self.db_id,))
            conn.commit()
            
        if self.db_id in self.app.sets:
            del self.app.sets[self.db_id]
        
        self.app.rebuild_navigation_headers()
        self.app.rebuild_entire_display()

    def on_save(self, ev):
        rows_to_save = []

        for idx, set_data in enumerate(self.app.sets.get(self.db_id, []), start=1):
            w_raw = str(set_data.get("w", "")).strip()
            r_raw = str(set_data.get("r", "")).strip()
            rpe_raw = str(set_data.get("rpe", "")).strip()

            if not w_raw and not r_raw and not rpe_raw:
                continue

            if w_raw and not r_raw:
                self.app.show_snackbar(f"Set {idx} has weight but no reps.", "red300")
                return

            if r_raw and not w_raw:
                self.app.show_snackbar(f"Set {idx} has reps but no weight.", "red300")
                return

            try:
                w_val = float(w_raw)
            except ValueError:
                self.app.show_snackbar(f"Set {idx} weight must be numeric.", "red300")
                return

            try:
                r_val = int(r_raw)
            except ValueError:
                self.app.show_snackbar(f"Set {idx} reps must be a whole number.", "red300")
                return

            if rpe_raw:
                try:
                    rpe_val = float(rpe_raw)
                except ValueError:
                    self.app.show_snackbar(f"Set {idx} RPE must be numeric.", "red300")
                    return
            else:
                rpe_val = 10.0

            if not set_data.get("done") or not set_data.get("completed_at"):
                self.app.show_snackbar(f"Mark Set {idx} Done before logging the exercise.", "red300")
                return
            target = self.set_targets[idx - 1] if idx - 1 < len(self.set_targets) else {"w": self.tgt_w, "r": self.tgt_r}
            rows_to_save.append((w_val, r_val, rpe_val, idx - 1, target, set_data.get("completed_at")))

        if not rows_to_save:
            return

        is_new_pr = False
        current_bw = get_user_bodyweight()

        with get_db() as conn:
            cursor = conn.cursor()
            is_bw = EXERCISE_METADATA.get(self.exercise, {}).get("equipment") == "Bodyweight"
            
            cursor.execute(f"SELECT s.weight, s.reps, ws.bodyweight_snapshot FROM workout_sets s JOIN workout_sessions ws ON s.session_id = ws.id WHERE ws.exercise = ? AND ws.status = '{STATUS_COMPLETED}' AND ws.id != ?", (self.exercise, self.db_id))
            all_historical_records = cursor.fetchall()
            
            historical_max_e1rm = 0.0
            for hw, hr, h_snap_bw in all_historical_records:
                h_bw_to_use = h_snap_bw if h_snap_bw is not None else current_bw
                h_e1rm = calculate_e1rm(hw, hr, h_bw_to_use if is_bw else 0.0)
                if h_e1rm > historical_max_e1rm:
                    historical_max_e1rm = h_e1rm
                    
            current_max_e1rm = 0.0
            best_raw_w, best_raw_r = 0.0, 0
            for w_val, r_val, _, _, _, _ in rows_to_save:
                c_e1rm = calculate_e1rm(float(w_val), int(r_val), current_bw if is_bw else 0.0)
                if c_e1rm > current_max_e1rm:
                    current_max_e1rm = c_e1rm
                    best_raw_w, best_raw_r = float(w_val), int(r_val)

            if current_max_e1rm > historical_max_e1rm and historical_max_e1rm > 0:
                is_new_pr = True
            elif not all_historical_records and current_max_e1rm > 0:
                is_new_pr = True

            cursor.execute("UPDATE exercise_dict SET setup_notes = ? WHERE name = ?", (self.notes_field.value.strip(), self.exercise))

            cursor.execute("DELETE FROM workout_sets WHERE session_id = ?", (self.db_id,))

            prev_completed_at = None
            for i, (w_val, r_val, rpe_val, orig_idx, target, completed_at) in enumerate(rows_to_save, start=1):
                normal_target = self.normal_set_targets[orig_idx] if orig_idx < len(self.normal_set_targets) else target
                rest_secs = None
                if prev_completed_at and completed_at:
                    try:
                        rest_secs = max(0, int(round((datetime.fromisoformat(completed_at) - datetime.fromisoformat(prev_completed_at)).total_seconds())))
                    except Exception:
                        rest_secs = None
                prev_completed_at = completed_at or prev_completed_at
                cursor.execute("""
                    INSERT INTO workout_sets
                        (session_id, set_number, weight, reps, rpe, rest_seconds, target_weight, target_reps, normal_target_weight, normal_target_reps, completed_at, is_complete)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (self.db_id, i, float(w_val), int(r_val), float(rpe_val), rest_secs,
                      float(target["w"]), int(target["r"]), float(normal_target["w"]), int(normal_target["r"]), completed_at))
            
            true_completion_date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(f"UPDATE workout_sessions SET status = '{STATUS_COMPLETED}', date = ?, bodyweight_snapshot = ? WHERE id = ?", (true_completion_date, current_bw, self.db_id))
            conn.commit()

        if self.db_id in self.app.sets:
            del self.app.sets[self.db_id]

        if is_new_pr:
            self.app.pr_celebrations[self.db_id] = True
            # Badge classification is best-effort — a failure here must never block the UI refresh.
            try:
                classification = get_strength_classification(
                    weight=best_raw_w,
                    reps=best_raw_r,
                    bodyweight=current_bw,
                    age=get_user_age(),
                    sex=get_user_sex(),
                    exercise_name=self.exercise
                )
                if classification:
                    self.app.strength_badges[self.db_id] = classification
            except Exception as badge_err:
                print(f"[on_save] strength badge skipped: {badge_err}")

        # Each post-save step is isolated so that a failure in routing or header
        # rebuild cannot prevent the display refresh.  The display refresh MUST
        # always run — it is the only thing that makes the card show as Completed.
        try:
            self.app.check_and_route_day()
        except Exception as route_err:
            print(f"[on_save] check_and_route_day failed: {route_err}")

        try:
            self.app.rebuild_navigation_headers()
        except Exception as nav_err:
            print(f"[on_save] rebuild_navigation_headers failed: {nav_err}")

        # Unconditional — runs regardless of what happened above.
        self.app.rebuild_entire_display()


class WorkoutTrackerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "IronCycle"
        self.page.theme_mode = "dark"
        self.page.padding = 6
        try:
            self.page.safe_area = True
        except:
            pass

        self.sets = {}
        self.show_add_form = False
        self.show_survey = False
        self.pr_celebrations = {}
        self.strength_badges = {}
        self.meso_just_completed = False
        # Retained for compatibility with older in-memory state. Rest timing now
        # uses each set's explicit Done checkbox and workout_sets.completed_at.
        self.set_touch_times = {}
        self.view_mode = "workout" 
        self.collapsed_categories = {}
        # Quick-nav and active-exercise focus state.
        self.active_exercise_by_category = {}
        self.pending_scroll_key = None
        self.delete_dialog_id = None
        self.current_meso = 1
        
        self.gen_days = {"Monday": True, "Tuesday": True, "Wednesday": True, "Thursday": True, "Friday": True, "Saturday": False, "Sunday": False}
        self.gen_length = 4

        init_and_seed_db()
        
        with get_db() as conn:
            cursor = conn.cursor()
            latest_meso = get_latest_meso_number(cursor)
            if latest_meso:
                self.current_meso = latest_meso
        
                                
        self.set_active_position()
        self.build_ui_shell()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    
    def safe_open(self, control):
        # Sweep the overlay for old zombie dialogs and purge them to prevent freezing
        if isinstance(control, ft.AlertDialog):
            zombies = [c for c in self.page.overlay if isinstance(c, ft.AlertDialog) and c != control]
            for z in zombies:
                self.page.overlay.remove(z)
                
        if hasattr(self.page, "open"):
            self.page.open(control)
        else:
            if control not in self.page.overlay:
                self.page.overlay.append(control)
            control.open = True
            self.page.update()

    def safe_close(self, control):
        if control is None:
            return
        try:
            # 1. INSTANTLY hide the UI to prevent overlapping dialog freezes
            control.open = False
            self.page.update()
            
            # 2. Let Flet safely clean up the native background objects 
            if hasattr(self.page, "close"):
                self.page.close(control)
        except Exception:
            pass

    def set_active_position(self, force_week=None):
        day_order = {day: idx for idx, day in enumerate(self.ordered_day_names(), start=1)}
        selected_days = self.get_selected_days_for_meso()

        with get_db() as conn:
            cursor = conn.cursor()
            if force_week:
                self.current_week = force_week
                cursor.execute(
                    "SELECT day_of_week FROM workout_sessions WHERE meso_number = ? AND week = ? AND status = 'Pending'",
                    (self.current_meso, self.current_week)
                )
                pending_days = [r[0] for r in cursor.fetchall() if r[0]]
                if pending_days:
                    pending_days.sort(key=lambda d: day_order.get(d, 99))
                    self.current_day = pending_days[0]
                else:
                    self.current_day = selected_days[0] if selected_days else "Monday"
                return

            cursor.execute(
                "SELECT week, day_of_week FROM workout_sessions WHERE meso_number = ? AND status = 'Pending'",
                (self.current_meso,)
            )
            pending = [(r[0], r[1]) for r in cursor.fetchall() if r[0] and r[1]]
            if pending:
                pending.sort(key=lambda x: (999 if x[0] == 'Deload' else int(x[0]), day_order.get(x[1], 99)))
                self.current_week = pending[0][0]
                self.current_day = pending[0][1]
                return

            cursor.execute("SELECT DISTINCT week FROM workout_sessions WHERE meso_number = ?", (self.current_meso,))
            session_weeks = [r[0] for r in cursor.fetchall() if r[0]]
            if session_weeks:
                self.current_week = sorted(session_weeks, key=lambda w: 999 if w == 'Deload' else int(w))[-1]
            else:
                weeks = self.get_existing_weeks()
                self.current_week = "1" if "1" in weeks else (weeks[0] if weeks else "1")

            self.current_day = selected_days[0] if selected_days else "Monday"

    def check_and_route_day(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM workout_sessions "
                "WHERE meso_number = ? AND week = ? AND day_of_week = ? AND status = 'Pending'",
                (self.current_meso, self.current_week, self.current_day)
            )
            current_day_pending = cursor.fetchone()[0]

            if current_day_pending > 0:
                return

            cursor.execute(
                "SELECT COUNT(*) FROM workout_sessions "
                "WHERE meso_number = ? AND week = ? AND day_of_week = ? AND status = 'Completed'",
                (self.current_meso, self.current_week, self.current_day)
            )
            completed_today = cursor.fetchone()[0]
            
            if completed_today > 0:
                # Meso completion is based on hard training work only; pending deload sessions are excluded.
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM workout_sessions
                    WHERE meso_number = ?
                      AND status = 'Pending'
                      AND COALESCE(week, '') != 'Deload'
                    """,
                    (self.current_meso,)
                )
                pending_non_deload = cursor.fetchone()[0]
                self.meso_just_completed = (pending_non_deload == 0 and self.current_week != "Deload")
                self.view_mode = "summary"
                return

        self.advance_active_position()

    def advance_active_position(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM workout_sessions "
                "WHERE meso_number = ? AND week = ? AND status = 'Pending'",
                (self.current_meso, self.current_week)
            )
            week_pending = cursor.fetchone()[0]

        if week_pending > 0:
            self.set_active_position(force_week=self.current_week)
        else:
            self.set_active_position()
        self.view_mode = "workout"

    def load_exercise_dict(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, name FROM exercise_dict ORDER BY category, name")
            rows = cursor.fetchall()
            
        dict_map = {}
        for cat, name in rows:
            if cat not in dict_map:
                dict_map[cat] = []
            dict_map[cat].append(name)
        return dict_map

    def build_ui_shell(self):
        self.page.controls.clear()
        
        ex_dict = self.load_exercise_dict()
        dropdown_options_list = []
        self.first_valid_exercise = ""
        
        for category, exercises in ex_dict.items():
            dropdown_options_list.append(ft.dropdown.Option(text=f"─── {category.upper()} ───", disabled=True))
            for ex in exercises:
                if not self.first_valid_exercise: self.first_valid_exercise = ex
                dropdown_options_list.append(ft.dropdown.Option(key=ex, text=ex))

        dropdown_options_list.append(ft.dropdown.Option(text="─── END OF LIST ───", disabled=True))
        for i in range(4):
            dropdown_options_list.append(ft.dropdown.Option(text=" " * (i + 1), disabled=True))

        self.wizard_custom_input = ft.TextField(label="Or type custom exercise...", expand=True, text_size=12)
        self.wizard_weight_input = ft.TextField(label="Lbs", value="45.0", expand=True, text_size=12, keyboard_type=ft.KeyboardType.NUMBER)
        self.wizard_reps_input = ft.TextField(label="Reps", value="10", expand=True, text_size=12, keyboard_type=ft.KeyboardType.NUMBER)
        self.wizard_type_dropdown = ft.Dropdown(
            label="Type", value="Compound", width=110, text_size=12,
            options=[ft.dropdown.Option("Compound"), ft.dropdown.Option("Isolation")]
        )
        
        category_options = [ft.dropdown.Option(c) for c in ex_dict.keys()]
        if "Custom" not in ex_dict.keys(): category_options.append(ft.dropdown.Option("Custom"))
        self.wizard_cat_dropdown = ft.Dropdown(label="Category", value="Chest", expand=True, text_size=12, options=category_options)

        self.wizard_exercise_dropdown = ft.Dropdown(
            label="Pick Exercise", value=self.first_valid_exercise, expand=True, text_size=12,
            options=dropdown_options_list
        )
        
        self.wizard_exercise_dropdown.on_select = lambda e: [
            self.update_wizard_stats(e.control.value),
            self.page.update()
        ]

        self.dict_dropdown = ft.Dropdown(label="Select Exercise to Delete", expand=True, text_size=12, options=dropdown_options_list)

        self.main_canvas = ft.ListView(expand=True, spacing=6)
        self.history_canvas = ft.ListView(expand=True, spacing=10)
        self.generator_canvas = ft.ListView(expand=True, spacing=6) 
        self.summary_canvas = ft.ListView(expand=True, spacing=10)
        self.meso_report_canvas = ft.ListView(expand=True, spacing=8)
        self.strength_standards_canvas = ft.ListView(expand=True, spacing=10)
        
        self.survey_panel = ft.Container()
        self.engine_button_container = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)

        self.current_meso_title = ft.Text("", size=13, weight="bold", color="cyan300")
        self.meso_nav_row = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Text("MESO", size=8, weight="bold", color="white38"),
                    self.current_meso_title,
                ], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="white10",
                border_radius=9,
                padding=5,
            )
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=0, expand=True)
        self.week_nav_row = ft.Row(spacing=6, scroll="auto", expand=True)
        self.day_nav_row = ft.Row(spacing=6, scroll="auto", expand=True)

        self.btn_menu = ft.ElevatedButton(
            content=ft.Text("Menu", weight="bold", size=12),
            on_click=self.open_actions_menu,
            height=32,
            width=82,
            style=ft.ButtonStyle(
                bgcolor="white10", color="white",
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=6
            )
        )

        # Equal-width side slots keep the mesocycle indicator truly centered.
        # The extra right inset keeps Menu clear of Android's landscape nav overlay.
        self.top_header_row = ft.Row([
            ft.Container(width=140),
            self.meso_nav_row,
            ft.Container(content=self.btn_menu, width=140, padding=4),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        self.week_header_row = ft.Row([self.week_nav_row], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.day_header_row = ft.Row([self.day_nav_row], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self.navigation_header_container = ft.Column([
            self.top_header_row,
            self.week_header_row,
            self.day_header_row
        ], spacing=3)

        self.page.add(
            ft.Container(height=1),
            self.navigation_header_container,
            ft.Divider(height=1, color="white10"),
            self.main_canvas
        )

    def open_actions_menu(self, e=None):
        history_lbl = "🕰️ Open History" if self.view_mode == "workout" else "🏋️ Back to Workout"
        btn_style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6), padding=12)

        self.actions_menu_dialog = ft.AlertDialog(
            title=ft.Text("Quick Actions", size=16, weight="bold"),
            content=ft.Container(
                width=320,
                content=ft.Column([
                    ft.Text("NAVIGATION", size=10, weight="bold", color="cyan300"),
                    ft.Dropdown(
                        label="Mesocycle",
                        value=str(self.current_meso),
                        options=[ft.dropdown.Option(key=str(m_id), text=m_label) for m_id, m_label in self.get_existing_mesos()],
                        on_select=self.menu_change_meso,
                        text_size=12,
                        dense=True,
                    ),
                    ft.Row([
                        ft.ElevatedButton(history_lbl, on_click=self.menu_toggle_history, expand=True, style=btn_style),
                        ft.ElevatedButton("➕ Add Exercise", on_click=self.menu_add_exercise, expand=True, style=btn_style),
                    ], spacing=6),
                    
                    ft.Divider(height=10, color="white10"),
                    
                    ft.Text("MESOCYCLE", size=10, weight="bold", color="cyan300"),
                    ft.Row([
                        ft.ElevatedButton("✏️ Rename", on_click=self.trigger_rename_active_meso, expand=True, style=btn_style),
                        ft.ElevatedButton("⏳ Length", on_click=self.trigger_adjust_meso_length, expand=True, style=btn_style),
                    ], spacing=6),
                    ft.ElevatedButton("🏗️ Architect New Meso", style=ft.ButtonStyle(bgcolor="orange700", shape=ft.RoundedRectangleBorder(radius=6), color="white"), on_click=self.open_generator_view, width=float('inf')),
                    ft.ElevatedButton("🔁 Repeat Previous Meso", style=ft.ButtonStyle(bgcolor="blue700", shape=ft.RoundedRectangleBorder(radius=6), color="white"), on_click=self.open_clone_meso_dialog, width=float('inf')),
                    
                    ft.Divider(height=10, color="white10"),

                    ft.Text("PROGRESS", size=10, weight="bold", color="cyan300"),
                    ft.Row([
                        ft.ElevatedButton("📈 Strength Standards", on_click=self.open_strength_standards, expand=True, style=btn_style),
                        ft.ElevatedButton("🏁 Meso Report", on_click=self.open_meso_report, expand=True, style=btn_style),
                    ], spacing=6),

                    ft.Divider(height=10, color="white10"),
                    
                    ft.Text("SETTINGS & DATA", size=10, weight="bold", color="cyan300"),
                    ft.Row([
                        ft.ElevatedButton("👤 Profile Settings", on_click=self.open_settings_dialog, expand=True, style=btn_style),
                        ft.ElevatedButton("📖 Dictionary", on_click=self.menu_manage_dict, expand=True, style=btn_style),
                    ], spacing=6),
                    ft.ElevatedButton("📊 Export History to CSV", on_click=self.export_to_csv, width=float('inf'), style=btn_style),

                    ft.Divider(height=10, color="white10"),

                    # --- COMPACTED BACKUPS & TRANSFERS SECTION ---
                    ft.Text("BACKUPS & TRANSFERS", size=10, weight="bold", color="cyan300"),
                    ft.Row([
                        ft.ElevatedButton("💾 Save Local", on_click=self.handle_local_backup_click, expand=True, style=btn_style),
                        ft.ElevatedButton("📂 Load Local", on_click=self.handle_local_restore_click, expand=True, style=btn_style),
                    ], spacing=6),
                    ft.Row([
                        ft.ElevatedButton("📡 WiFi Export", on_click=self.handle_wifi_export_click, expand=True, style=btn_style),
                        ft.ElevatedButton("🛰️ WiFi Import", on_click=self.handle_wifi_import_click, expand=True, style=btn_style),
                    ], spacing=6),
                    ft.Row([
                        ft.ElevatedButton("📋 Copy Code", on_click=self.handle_backup_click, expand=True, style=btn_style),
                        ft.ElevatedButton("📥 Paste Code", on_click=self.handle_restore_click, expand=True, style=btn_style),
                    ], spacing=6),

                ], tight=True, spacing=4, scroll="auto")
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Close"),
                    on_click=lambda e: self.close_actions_menu(e)
                )
            ],
            actions_alignment="end",
            content_padding=20
        )
        self.safe_open(self.actions_menu_dialog)

    def menu_change_meso(self, e):
        try:
            meso_num = int(e.control.value)
        except (TypeError, ValueError):
            return
        self.close_actions_menu()
        self.change_active_meso(meso_num)

    def close_actions_menu(self, e=None):
        if hasattr(self, "actions_menu_dialog") and self.actions_menu_dialog:
            self.safe_close(self.actions_menu_dialog)
            # DO NOT set it to None here. We need to remember it so we can guarantee it closes later!
            
    def open_settings_dialog(self, e=None):
        self.close_actions_menu()
        current_bw = get_user_bodyweight()
        current_age = get_user_age()
        current_profile = get_user_progression_profile()
        current_sex = get_user_sex()
        
        self.bw_input = ft.TextField(label="Bodyweight (Lbs)", value=str(current_bw), keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.age_input = ft.TextField(label="Age (Years)", value=str(current_age), keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.sex_dropdown = ft.Dropdown(
            label="Sex",
            value=current_sex,
            options=[ft.dropdown.Option("Male"), ft.dropdown.Option("Female")],
            expand=True,
        )
        
        self.slider_label = ft.Text(size=12, color="cyan300", weight="bold")
        
        def update_slider_label(val):
            if val == 0: return "Auto (Scales with Age)"
            if val == 1: return "Conservative (Volume Focus, Joint Safe)"
            if val == 2: return "Balanced (Standard Hypertrophy)"
            if val == 3: return "Aggressive (Heavy Load Focus)"
            return ""

        self.slider_label.value = update_slider_label(current_profile)

        def on_slider_change(ev):
            self.slider_label.value = update_slider_label(int(ev.control.value))
            self.slider_label.update()

        self.profile_slider = ft.Slider(
            min=0, max=3, divisions=3, value=current_profile, 
            on_change=on_slider_change
        )
        
        def save_settings(ev):
            try:
                new_bw = float(self.bw_input.value)
                new_age = int(self.age_input.value)
                new_profile = int(self.profile_slider.value)
                new_sex = self.sex_dropdown.value or "Male"
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO user_settings (setting_key, setting_value) VALUES ('bodyweight', ?)", (str(new_bw),))
                    cursor.execute("INSERT OR REPLACE INTO user_settings (setting_key, setting_value) VALUES ('age', ?)", (str(new_age),))
                    cursor.execute("INSERT OR REPLACE INTO user_settings (setting_key, setting_value) VALUES ('progression_profile', ?)", (str(new_profile),))
                    cursor.execute("INSERT OR REPLACE INTO user_settings (setting_key, setting_value) VALUES ('sex', ?)", (new_sex,))
                    conn.commit()
                self.safe_close(self.settings_dialog)
                self.show_snackbar("Profile settings saved!", "green300")
                self.rebuild_entire_display()
            except ValueError:
                self.show_snackbar("Invalid input. Please use numbers.", "red300")

        self.settings_dialog = ft.AlertDialog(
            title=ft.Text("Profile Settings", weight="bold"),
            content=ft.Column([
                ft.Row([self.bw_input, self.age_input]),
                self.sex_dropdown,
                ft.Text("Used for strength standards comparisons.", size=10, color="white54"),
                ft.Divider(height=10, color="transparent"),
                ft.Text("Pacing Override", size=13, weight="bold", color="white"),
                ft.Text("Force the engine to progress faster or slower.", size=11, color="white54"),
                self.slider_label,
                self.profile_slider
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: self.safe_close(self.settings_dialog)),
                ft.ElevatedButton("Save", on_click=save_settings, style=ft.ButtonStyle(bgcolor="blue700", color="white"))
            ], actions_alignment="end"
        )
        self.safe_open(self.settings_dialog)

    def trigger_delete_double_check(self, e=None):
        self.delete_confirm_dialog = ft.AlertDialog(
            title=ft.Text("DANGER: WIPE MESOCYCLE"), content=ft.Text("Are you sure? This cannot be undone."),
            actions=[
                ft.TextButton(content=ft.Text("Cancel"), on_click=self.close_delete_confirm_dialog),
                ft.ElevatedButton(content=ft.Text("Permanently Delete"), style=ft.ButtonStyle(bgcolor="red700"), on_click=self.delete_meso_final_confirmed)
            ], actions_alignment="end"
        )
        self.safe_open(self.delete_confirm_dialog)

    def close_delete_confirm_dialog(self, e=None):
        if hasattr(self, 'delete_confirm_dialog'):
            self.safe_close(self.delete_confirm_dialog)
        
    def close_delete_dialog(self, e=None):
        if hasattr(self, 'delete_dialog'):
            self.safe_close(self.delete_dialog)

    def confirm_delete(self, e=None):
        if self.delete_dialog_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workout_sessions WHERE id = ?", (self.delete_dialog_id,))
                conn.commit()
            
            if self.delete_dialog_id in self.sets:
                del self.sets[self.delete_dialog_id]
            if self.delete_dialog_id in self.set_touch_times:
                del self.set_touch_times[self.delete_dialog_id]
                
            self.delete_dialog_id = None
            
        self.close_delete_dialog()
        self.show_snackbar("Exercise deleted from today's routine.", "green300")

        try:
            self.check_and_route_day()
        except Exception as e:
            print(f"[delete_exercise] check_and_route_day failed: {e}")

        try:
            self.rebuild_navigation_headers()
        except Exception as e:
            print(f"[delete_exercise] rebuild_navigation_headers failed: {e}")

        self.rebuild_entire_display()
        
    def trigger_rename_active_meso(self, e=None):
        self.close_actions_menu()
        self.input_rename_field = ft.TextField(value=self.current_meso_label(), label="Edit Title", width=220, height=38, text_size=13)
        self.rename_dialog = ft.AlertDialog(
            title=ft.Text("Modify Title"), content=self.input_rename_field,
            actions=[
                ft.Row([
                    ft.TextButton(content=ft.Text("Delete", color="red400"), on_click=lambda e: [self.close_rename_dialog(), self.trigger_delete_double_check()]),
                    ft.Row([
                        ft.TextButton(content=ft.Text("Cancel"), on_click=self.close_rename_dialog),
                        ft.ElevatedButton(content=ft.Text("Update"), on_click=self.save_active_rename)
                    ], spacing=5)
                ], alignment="spaceBetween", expand=True)
            ]
        )
        self.safe_open(self.rename_dialog)

    def close_rename_dialog(self, e=None):
        if hasattr(self, 'rename_dialog'):
            self.safe_close(self.rename_dialog)
    
    def trigger_adjust_meso_length(self, e=None):
        self.close_actions_menu()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT length_weeks FROM meso_configs WHERE meso_number = ?",
                (self.current_meso,)
            )
            row = cursor.fetchone()
            current_len = int(row[0]) if row and row[0] else 4

        self.length_slider = ft.Slider(
            min=2,
            max=12,
            divisions=10,
            value=current_len,
            label="{value} Weeks"
        )

        def save_new_length(ev):
            new_len = int(self.length_slider.value)

            with get_db() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT DISTINCT week
                    FROM workout_sessions
                    WHERE meso_number = ?
                    """,
                    (self.current_meso,)
                )
                raw_weeks = [r[0] for r in cursor.fetchall()]

                future_numeric_weeks = sorted(
                    [int(w) for w in raw_weeks if str(w).isdigit() and int(w) > new_len]
                )

                completed_beyond = 0
                pending_beyond = 0

                if future_numeric_weeks:
                    placeholders = ",".join("?" * len(future_numeric_weeks))

                    cursor.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM workout_sessions
                        WHERE meso_number = ?
                          AND status = 'Completed'
                          AND CAST(week AS INTEGER) IN ({placeholders})
                        """,
                        (self.current_meso, *future_numeric_weeks)
                    )
                    completed_beyond = cursor.fetchone()[0] or 0

                    cursor.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM workout_sessions
                        WHERE meso_number = ?
                          AND status = 'Pending'
                          AND CAST(week AS INTEGER) IN ({placeholders})
                        """,
                        (self.current_meso, *future_numeric_weeks)
                    )
                    pending_beyond = cursor.fetchone()[0] or 0

                if completed_beyond > 0:
                    self.safe_close(self.length_dialog)
                    self.show_snackbar(
                        f"Cannot shorten to {new_len} week(s) because completed workouts already exist beyond that point.",
                        "red300"
                    )
                    return

                cursor.execute(
                    "UPDATE meso_configs SET length_weeks = ? WHERE meso_number = ?",
                    (new_len, self.current_meso)
                )

                if future_numeric_weeks:
                    placeholders = ",".join("?" * len(future_numeric_weeks))

                    cursor.execute(
                        f"""
                        DELETE FROM workout_sessions
                        WHERE meso_number = ?
                          AND status = 'Pending'
                          AND CAST(week AS INTEGER) IN ({placeholders})
                        """,
                        (self.current_meso, *future_numeric_weeks)
                    )

                    cursor.execute(
                        f"""
                        DELETE FROM readiness_logs
                        WHERE meso_number = ?
                          AND CAST(week AS INTEGER) IN ({placeholders})
                        """,
                        (self.current_meso, *future_numeric_weeks)
                    )

                conn.commit()

            if str(self.current_week).isdigit() and int(self.current_week) > new_len:
                self.current_week = str(new_len)
                self.set_active_position(force_week=self.current_week)
            else:
                self.set_active_position()

            self.safe_close(self.length_dialog)

            if pending_beyond > 0:
                self.show_snackbar(
                    f"Meso length updated to {new_len} weeks. Removed {pending_beyond} future pending workout(s).",
                    "green300"
                )
            else:
                self.show_snackbar(
                    f"Meso length updated to {new_len} weeks.",
                    "green300"
                )

            self.rebuild_navigation_headers()
            self.rebuild_entire_display()

        self.length_dialog = ft.AlertDialog(
            title=ft.Text("Adjust Meso Length", weight="bold"),
            content=ft.Column([
                ft.Text(
                    "Extend or shorten the total training weeks before your Deload.",
                    size=12,
                    color="white70"
                ),
                ft.Text(
                    "Shortening will remove only future pending weeks. Completed weeks will be protected.",
                    size=11,
                    color="amber300"
                ),
                self.length_slider
            ], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.safe_close(self.length_dialog)),
                ft.ElevatedButton(
                    "Update",
                    on_click=save_new_length,
                    style=ft.ButtonStyle(bgcolor="blue700", color="white")
                )
            ]
        )
        self.safe_open(self.length_dialog)

    def menu_manage_dict(self, e=None):
        try:
            self.close_actions_menu()
            ex_dict = self.load_exercise_dict()
            options = []
            
            self.current_dict_mapping = {}
            for cat, exercises in ex_dict.items():
                options.append(ft.dropdown.Option(text=f"─── {cat.upper()} ───"))
                for ex in exercises:
                    options.append(ft.dropdown.Option(key=ex, text=ex))
                    self.current_dict_mapping[ex] = cat
                    
            self.dict_dropdown = ft.Dropdown(
                label="Select Exercise", 
                text_size=12, 
                options=options
            )
            self.dict_dropdown.on_select = self.on_dict_ex_change
            
            cat_options = [ft.dropdown.Option(key=c, text=c) for c in ["Chest", "Back", "Shoulders", "Quads", "Hamstrings", "Glutes", "Calves", "Biceps", "Triceps", "Forearms", "Abs", "General", "Custom"]]
            
            self.dict_cat_dropdown = ft.Dropdown(
                label="Category", 
                text_size=12, 
                options=cat_options
            )

            self.dict_rename_field = ft.TextField(
                label="Rename to...",
                text_size=12,
                hint_text="New exercise name",
                expand=True,
                visible=False,
            )

            self.dict_dialog = ft.AlertDialog(
                title=ft.Text("Manage Dictionary", size=16, weight="bold"),
                content=ft.Container(
                    width=320, 
                    content=ft.Column([
                        ft.Text("Modify category, rename, or remove an exercise.", size=12, color="white54"), 
                        self.dict_dropdown,
                        self.dict_cat_dropdown,
                        ft.ElevatedButton(
                            "Update Category",
                            style=ft.ButtonStyle(bgcolor="blue700", color="white"),
                            on_click=self.update_dictionary_category,
                            width=320
                        ),
                        ft.Divider(height=6, color="white10"),
                        self.dict_rename_field,
                        ft.ElevatedButton(
                            "Rename Exercise",
                            style=ft.ButtonStyle(bgcolor="teal700", color="white"),
                            on_click=self.rename_dictionary_exercise,
                            width=320,
                        ),
                        ft.Divider(height=6, color="white10"),
                        ft.Row([
                            ft.TextButton("Cancel", on_click=self.close_dict_dialog),
                            ft.TextButton("Delete", icon="delete", icon_color="red400", on_click=self.delete_from_dictionary)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.ElevatedButton("Update Category", style=ft.ButtonStyle(bgcolor="blue700", color="white"), on_click=self.update_dictionary_category, width=320)
                    ], tight=True, spacing=6)
                )
            )
            self.safe_open(self.dict_dialog)

        except Exception as ex:
            error_msg = f"DICT CRASH: {str(ex)}\n\n{traceback.format_exc()}"
            self.main_canvas.controls.insert(0, ft.Container(
                content=ft.Text(error_msg, color="white", size=10, font_family="monospace"),
                bgcolor="red900", padding=10, border_radius=8
            ))
            self.main_canvas.update()
            self.page.update()

    def on_dict_ex_change(self, e):
        selected_ex = self.dict_dropdown.value
        if selected_ex in self.current_dict_mapping:
            self.dict_cat_dropdown.value = self.current_dict_mapping[selected_ex]
            try:
                self.dict_cat_dropdown.update()
            except:
                pass
        if hasattr(self, 'dict_rename_field'):
            self.dict_rename_field.value = selected_ex or ""
            self.dict_rename_field.visible = bool(selected_ex)
            try:
                self.dict_rename_field.update()
            except:
                pass

    def update_dictionary_category(self, e):
        ex_name = self.dict_dropdown.value
        new_cat = self.dict_cat_dropdown.value
        if not ex_name or not new_cat:
            self.show_snackbar("Select an exercise and category.", "red300")
            return
            
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE exercise_dict SET category = ? WHERE name = ?", (new_cat, ex_name))
            cursor.execute("UPDATE workout_sessions SET category = ? WHERE exercise = ?", (new_cat, ex_name))
            conn.commit()
            
        self.close_dict_dialog()
        self.show_snackbar(f"{ex_name} moved to {new_cat}.", "green300")
        
        self.build_ui_shell()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def rename_dictionary_exercise(self, e):
        old_name = self.dict_dropdown.value
        new_name = self.dict_rename_field.value.strip() if hasattr(self, 'dict_rename_field') else ""

        if not old_name:
            self.show_snackbar("Select an exercise first.", "red300")
            return
        if not new_name:
            self.show_snackbar("Enter a new name.", "red300")
            return
        if new_name == old_name:
            self.show_snackbar("Name is unchanged.", "white54")
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Check for collision
            cursor.execute("SELECT COUNT(*) FROM exercise_dict WHERE name = ?", (new_name,))
            if cursor.fetchone()[0] > 0:
                self.show_snackbar(f"'{new_name}' already exists in the dictionary.", "red300")
                return

            # 1. Rename in the dictionary
            cursor.execute("UPDATE exercise_dict SET name = ? WHERE name = ?", (new_name, old_name))

            # 2. Cascade to all workout sessions
            cursor.execute("UPDATE workout_sessions SET exercise = ? WHERE exercise = ?", (new_name, old_name))

            # 3. Cascade into every meso's blueprint_json
            cursor.execute("SELECT meso_number, blueprint_json FROM meso_configs WHERE blueprint_json IS NOT NULL")
            meso_rows = cursor.fetchall()
            for meso_num, bp_raw in meso_rows:
                try:
                    bp = json.loads(bp_raw)
                    updated = False
                    for day, exercises in bp.items():
                        if isinstance(exercises, list) and old_name in exercises:
                            bp[day] = [new_name if ex == old_name else ex for ex in exercises]
                            updated = True
                    if updated:
                        cursor.execute(
                            "UPDATE meso_configs SET blueprint_json = ? WHERE meso_number = ?",
                            (json.dumps(bp), meso_num)
                        )
                except (json.JSONDecodeError, AttributeError):
                    pass  # Skip malformed blueprints silently

            conn.commit()

        self.close_dict_dialog()
        self.show_snackbar(f"Renamed '{old_name}' → '{new_name}' everywhere.", "green300")

        self.build_ui_shell()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def close_dict_dialog(self, e=None):
        if hasattr(self, 'dict_dialog'):
            self.safe_close(self.dict_dialog)

    def show_snackbar(self, text, color="green300"):
        sb = ft.SnackBar(ft.Text(text, color=color, weight="bold"), bgcolor="grey900", duration=3000)
        self.safe_open(sb)

    def current_meso_label(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT meso_label FROM meso_names WHERE meso_number = ?", (self.current_meso,))
            row = cursor.fetchone()
        return row[0] if row else f"Meso {self.current_meso}"

    def ordered_day_names(self):
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def get_selected_days_for_meso(self, meso_num=None):
        target_meso = self.current_meso if meso_num is None else meso_num
        day_order = self.ordered_day_names()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT selected_days FROM meso_configs WHERE meso_number = ?", (target_meso,))
            row = cursor.fetchone()

            if row and row[0]:
                try:
                    decoded = json.loads(row[0])
                    if isinstance(decoded, list):
                        ordered_selected = []
                        seen = set()
                        for d in day_order:
                            if d in decoded and d not in seen:
                                ordered_selected.append(d)
                                seen.add(d)
                        if ordered_selected:
                            return ordered_selected
                except Exception:
                    pass

            cursor.execute("SELECT DISTINCT day_of_week FROM workout_sessions WHERE meso_number = ?", (target_meso,))
            session_days = {r[0] for r in cursor.fetchall() if r[0]}

        ordered = [d for d in day_order if d in session_days]
        return ordered if ordered else ["Monday"]

    def get_blueprint_for_meso(self, meso_num=None):
        target_meso = self.current_meso if meso_num is None else meso_num
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT blueprint_json FROM meso_configs WHERE meso_number = ?", (target_meso,))
            row = cursor.fetchone()

        if row and row[0]:
            try:
                decoded = json.loads(row[0])
                return decoded if isinstance(decoded, dict) else {}
            except Exception:
                return {}
        return {}

    def is_planned_rest_day(self, day_name, meso_num=None):
        target_meso = self.current_meso if meso_num is None else meso_num
        selected_days = self.get_selected_days_for_meso(target_meso)
        if day_name not in selected_days:
            return False

        blueprint = self.get_blueprint_for_meso(target_meso)
        if blueprint:
            return len(blueprint.get(day_name, [])) == 0
        return False

    def current_week_days(self):
        return self.get_selected_days_for_meso(self.current_meso)

    def get_existing_mesos(self):
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT meso_number, meso_label FROM meso_names")
            label_map = {num: label for num, label in cursor.fetchall()}

            meso_ids = set(label_map.keys())

            cursor.execute("SELECT meso_number FROM meso_configs")
            meso_ids.update(r[0] for r in cursor.fetchall())

            cursor.execute("SELECT DISTINCT meso_number FROM workout_sessions")
            meso_ids.update(r[0] for r in cursor.fetchall())

        if not meso_ids:
            return [(1, "Meso 1")]

        rows = []
        for meso_num in sorted(meso_ids):
            rows.append((meso_num, label_map.get(meso_num, f"Meso {meso_num}")))
        return rows

    def open_clone_meso_dialog(self, e=None):
        self.close_actions_menu()
        mesos = self.get_existing_mesos()
        if not mesos:
            self.show_snackbar("No mesocycles found to repeat.", "red300")
            return

        # Default to the active/latest meso, since this is usually what you just finished.
        default_source = self.current_meso if any(m[0] == self.current_meso for m in mesos) else mesos[-1][0]
        default_label = next((label for num, label in mesos if num == default_source), f"Meso {default_source}")

        options = [
            ft.dropdown.Option(key=str(num), text=f"{label}  (Meso {num})")
            for num, label in sorted(mesos, key=lambda x: x[0], reverse=True)
        ]

        self.clone_source_dropdown = ft.Dropdown(
            label="Routine to repeat",
            value=str(default_source),
            options=options,
            text_size=12,
            width=320,
        )
        self.clone_name_field = ft.TextField(
            label="New meso name",
            value=f"Repeat of {default_label}",
            text_size=12,
            width=320,
        )

        self.clone_meso_dialog = ft.AlertDialog(
            title=ft.Text("🔁 Repeat Previous Meso", weight="bold"),
            content=ft.Column([
                ft.Text("This copies the selected routine into a new mesocycle, skips the deload week, and seeds each exercise from your most recent non-deload completed workout sets.", size=12, color="white70"),
                self.clone_source_dropdown,
                self.clone_name_field,
                ft.Text("Copied sessions will be Pending. Previous RPEs are not copied, so you still log the new workouts normally.", size=11, color="cyan200"),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda ev: self.safe_close(self.clone_meso_dialog)),
                ft.ElevatedButton("Create Repeat", style=ft.ButtonStyle(bgcolor="blue700", color="white"), on_click=self.execute_clone_meso),
            ],
            actions_alignment="spaceBetween"
        )
        self.safe_open(self.clone_meso_dialog)

    def _latest_non_deload_sets_for_exercise(self, cursor, exercise_name):
        """Return the most recent non-deload completed session target plus its set rows for an exercise."""
        cursor.execute("""
            SELECT id, target_weight, target_reps, movement_type, category
            FROM workout_sessions
            WHERE exercise = ?
              AND status = ?
              AND COALESCE(week, '') != 'Deload'
            ORDER BY date DESC, id DESC
            LIMIT 1
        """, (exercise_name, STATUS_COMPLETED))
        latest = cursor.fetchone()
        if not latest:
            return None, []

        latest_session_id, target_weight, target_reps, movement_type, category = latest
        cursor.execute("""
            SELECT set_number, weight, reps
            FROM workout_sets
            WHERE session_id = ?
            ORDER BY set_number ASC
        """, (latest_session_id,))
        set_rows = cursor.fetchall()
        return {
            "session_id": latest_session_id,
            "target_weight": target_weight,
            "target_reps": target_reps,
            "movement_type": movement_type,
            "category": category,
        }, set_rows

    def execute_clone_meso(self, e=None):
        try:
            source_meso = int(self.clone_source_dropdown.value)
        except Exception:
            self.show_snackbar("Please choose a mesocycle to repeat.", "red300")
            return

        new_label = (self.clone_name_field.value or "").strip()
        today_str = datetime.now().strftime("%Y-%m-%d")

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                new_meso_num = get_next_meso_number(cursor)
                if not new_label:
                    new_label = f"Repeated Meso {new_meso_num}"

                # 1. Find the highest non-deload week to capture the final state of the split
                cursor.execute("""
                    SELECT MAX(CAST(week AS INTEGER)) FROM workout_sessions
                    WHERE meso_number = ? AND COALESCE(week, '') != 'Deload' AND week GLOB '[0-9]*'
                """, (source_meso,))
                max_week_row = cursor.fetchone()
                max_week = str(max_week_row[0]) if max_week_row and max_week_row[0] else '1'

                # 2. Grab only the exercises from that final week to form the new Week 1 blueprint
                cursor.execute("""
                    SELECT exercise, category, day_of_week, movement_type
                    FROM workout_sessions
                    WHERE meso_number = ? AND week = ?
                    ORDER BY
                        CASE day_of_week
                            WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
                            WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
                            WHEN 'Sunday' THEN 7 ELSE 8 END,
                        id ASC
                """, (source_meso, max_week))
                final_week_sessions = cursor.fetchall()

                if not final_week_sessions:
                    raise ValueError("Selected mesocycle has no valid sessions to copy.")

                selected_days = []
                blueprint = {}
                cloned_count = 0
                seeded_set_count = 0

                for exercise, category, day, old_type in final_week_sessions:
                    if day and day not in selected_days:
                        selected_days.append(day)
                    blueprint.setdefault(day, [])
                    if exercise not in blueprint[day]:
                        blueprint[day].append(exercise)

                    # Use your brilliant helper function to get the exact weights/sets
                    latest_meta, latest_sets = self._latest_non_deload_sets_for_exercise(cursor, exercise)

                    if latest_sets:
                        first_set = latest_sets[0]
                        new_target_w = first_set[1] if first_set[1] is not None else 0
                        new_target_r = first_set[2] if first_set[2] is not None else 0
                    elif latest_meta:
                        new_target_w = latest_meta.get("target_weight") if latest_meta.get("target_weight") is not None else 0
                        new_target_r = latest_meta.get("target_reps") if latest_meta.get("target_reps") is not None else 0
                    else:
                        # --- FIX 1: Look at the old meso for smart defaults, not the empty new one ---
                        new_target_w, new_target_r, _ = get_exercise_smart_defaults(exercise, source_meso)

                    new_category = (latest_meta or {}).get("category") or category or "General"
                    new_type = (latest_meta or {}).get("movement_type") or old_type or "Isolation"

                    # 3. Stamp ONLY Week 1
                    cursor.execute("""
                        INSERT INTO workout_sessions
                            (date, exercise, category, day_of_week, week, target_weight, target_reps, status, movement_type, meso_number)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today_str, exercise, new_category, day, '1', new_target_w, new_target_r, STATUS_PENDING, new_type, new_meso_num))
                    new_session_id = cursor.lastrowid
                    cloned_count += 1

                    if latest_sets:
                        for idx, (_set_number, set_weight, set_reps) in enumerate(latest_sets, start=1):
                            cursor.execute("""
                                INSERT INTO workout_sets (session_id, set_number, weight, reps, rpe)
                                VALUES (?, ?, ?, ?, NULL)
                            """, (new_session_id, idx, set_weight, set_reps))
                            seeded_set_count += 1
                    else:
                        cursor.execute("INSERT INTO workout_sets (session_id, set_number, weight, reps, rpe) VALUES (?, ?, ?, ?, NULL)", (new_session_id, 1, new_target_w, new_target_r))
                        # --- FIX 2: Accurately count fallback sets for the success UI ---
                        seeded_set_count += 1

                # Copy configuration length and caps
                cursor.execute("SELECT length_weeks, daily_ex_cap FROM meso_configs WHERE meso_number = ?", (source_meso,))
                cfg_row = cursor.fetchone()
                length_weeks = cfg_row[0] if cfg_row and cfg_row[0] else 4
                daily_cap = cfg_row[1] if cfg_row and cfg_row[1] else 0

                upsert_meso_config(
                    cursor,
                    new_meso_num,
                    length_weeks,
                    json.dumps(selected_days),
                    json.dumps({
                        "mode": "repeat_previous_meso",
                        "source_meso": source_meso,
                        "uses_latest_non_deload_workout_sets": True,
                        "source_final_week": max_week  # <-- NEW: Easy debugging breadcrumb
                    }),
                    daily_cap,
                    json.dumps(blueprint)
                )

                cursor.execute(
                    "INSERT INTO meso_names (meso_number, meso_label) VALUES (?, ?)",
                    (new_meso_num, new_label)
                )
                conn.commit()

            if hasattr(self, 'clone_meso_dialog'):
                self.safe_close(self.clone_meso_dialog)

            self.sets.clear()
            self.pr_celebrations.clear()
            self.strength_badges.clear()
            self.show_add_form = False
            self.show_survey = False
            self.current_meso = new_meso_num
            self.current_week = '1'
            self.view_mode = "workout"
            self.set_active_position()
            self.rebuild_navigation_headers()
            self.rebuild_entire_display()
            self.show_snackbar(f"Repeated meso created: Week 1 generated, {seeded_set_count} sets seeded.", "green300")

        except Exception as err:
            self.show_snackbar(f"Repeat meso failed: {err}", "red300")
            traceback.print_exc()

    def get_existing_weeks(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT week FROM workout_sessions WHERE meso_number = ?", (self.current_meso,))
            rows = cursor.fetchall()
            cursor.execute("SELECT length_weeks FROM meso_configs WHERE meso_number = ?", (self.current_meso,))
            cfg_row = cursor.fetchone()

        weeks = set()
        has_deload = False

        for r in rows:
            if r[0] == "Deload":
                has_deload = True
            elif r[0] and str(r[0]).isdigit():
                weeks.add(str(r[0]))

        if cfg_row and cfg_row[0]:
            for i in range(1, int(cfg_row[0]) + 1):
                weeks.add(str(i))

        ordered = sorted(weeks, key=lambda x: int(x) if str(x).isdigit() else 0)
        if has_deload:
            ordered.append("Deload")
        return ordered if ordered else ["1"]

    def toggle_history_view(self, e=None):
        self.view_mode = "history" if self.view_mode == "workout" else "workout"
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def open_generator_view(self, e=None):
        self.close_actions_menu()
        self.view_mode = "generator"
        self.rebuild_entire_display()
        
    def cancel_generator_view(self, e=None):
        self.view_mode = "workout"
        self.rebuild_entire_display()

    def menu_toggle_history(self, e):
        self.close_actions_menu()
        self.toggle_history_view(None)

    def menu_add_exercise(self, e):
        self.close_actions_menu()
        if not self.show_add_form: self.toggle_add_exercise_form(None)
        
    def delete_from_dictionary(self, e):
        target = self.dict_dropdown.value
        if not target: return
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exercise_dict WHERE name = ?", (target,))
            conn.commit()
            
        self.close_dict_dialog()
        self.show_snackbar(f"{target} removed from dictionary.", "green300")
        
        self.build_ui_shell()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    # --- TEXT-BASED BACKUP & RESTORE METHODS ---

    def get_backup_storage_dir(self):
        db_dir = os.path.dirname(os.path.abspath(DB_PATH))
        backup_dir = os.path.join(db_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def create_backup_string(self):
        snapshot_path = DB_PATH + ".snapshot"
        try:
            with sqlite3.connect(DB_PATH, timeout=5.0) as src_conn:
                with sqlite3.connect(snapshot_path) as dst_conn:
                    src_conn.backup(dst_conn)

            with open(snapshot_path, "rb") as f:
                db_data = f.read()

            return base64.b64encode(zlib.compress(db_data, level=9)).decode("utf-8")
        finally:
            try:
                if os.path.exists(snapshot_path):
                    os.remove(snapshot_path)
            except:
                pass

    def handle_local_backup_click(self, e=None):
        self.close_actions_menu()
        try:
            encoded_str = self.create_backup_string()
            backup_dir = self.get_backup_storage_dir()
            filename = f"workout_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            backup_path = os.path.join(backup_dir, filename)

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(encoded_str)

            self.local_backup_success_dialog = ft.AlertDialog(
                title=ft.Text("Local Rollback Saved", weight="bold"),
                content=ft.Column(
                    [
                        ft.Text("A local snapshot was saved to your device.", size=12),
                        ft.Text(filename, size=12, weight="bold", color="cyan300"),
                        ft.Text("Use 'Restore Local Backup' to load it if you make a mistake.", size=11, color="white70")
                    ],
                    tight=True,
                    spacing=8
                ),
                actions=[
                    ft.TextButton(content=ft.Text("Close"), on_click=self.close_local_backup_success_dialog)
                ],
                actions_alignment="end"
            )
            self.safe_open(self.local_backup_success_dialog)
        except Exception as err:
            self.show_snackbar(f"Local backup failed: {err}", "red300")

    def close_local_backup_success_dialog(self, e=None):
        if hasattr(self, 'local_backup_success_dialog'):
            self.safe_close(self.local_backup_success_dialog)

    def handle_local_restore_click(self, e=None):
        self.close_actions_menu()
        try:
            backup_dir = self.get_backup_storage_dir()
            files = []
            
            if os.path.exists(backup_dir):
                for name in os.listdir(backup_dir):
                    if name.lower().endswith(".txt"):
                        path = os.path.join(backup_dir, name)
                        if os.path.isfile(path):
                            files.append((name, path, os.path.getmtime(path), os.path.getsize(path)))

            if not files:
                self.no_backups_dialog = ft.AlertDialog(
                    title=ft.Text("No Backups Found"),
                    content=ft.Text("You haven't created any local snapshots yet.", size=12),
                    actions=[ft.TextButton("Close", on_click=lambda e: self.safe_close(self.no_backups_dialog))]
                )
                self.safe_open(self.no_backups_dialog)
                return

            files.sort(key=lambda x: x[2], reverse=True)
            restore_buttons = []
            for name, path, mtime, size in files[:20]:
                ts = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                label = f"{name}  •  {ts}  •  {size:,} bytes"
                restore_buttons.append(
                    ft.TextButton(
                        content=ft.Text(label, size=11),
                        on_click=lambda ev, p=path, n=name: self.restore_local_backup_file(p, n)
                    )
                )

            self.local_restore_dialog = ft.AlertDialog(
                title=ft.Text("Restore Local Backup", weight="bold"),
                content=ft.Container(
                    width=340,
                    height=320,
                    content=ft.Column(
                        [
                            ft.Text("Choose a rollback point. This overwrites current data.", color="red300", size=12),
                            ft.Column(restore_buttons, scroll="auto", spacing=6)
                        ],
                        tight=True,
                        spacing=10
                    )
                ),
                actions=[
                    ft.TextButton(content=ft.Text("Close"), on_click=self.close_local_restore_dialog)
                ],
                actions_alignment="end"
            )
            self.safe_open(self.local_restore_dialog)
        except Exception as err:
            self.show_snackbar(f"Could not list local backups: {err}", "red300")

    def close_local_restore_dialog(self, e=None):
        if hasattr(self, 'local_restore_dialog'):
            self.safe_close(self.local_restore_dialog)

    def restore_local_backup_file(self, backup_path, backup_name=None):
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                raw_str = f.read()
            self.close_local_restore_dialog()
            self.execute_restore(raw_str)
        except Exception as err:
            display_name = backup_name or os.path.basename(backup_path)
            self.show_snackbar(f"Restore failed for {display_name}: {err}", "red300")

    def _cleanup_existing_wifi_server(self):
        """Cancel old WiFi timers and close any existing transfer server before starting a new one."""
        if hasattr(self, '_wifi_timeout_timer') and self._wifi_timeout_timer:
            try:
                self._wifi_timeout_timer.cancel()
            except:
                pass
            self._wifi_timeout_timer = None

        if hasattr(self, '_wifi_server') and self._wifi_server:
            server_ref = self._wifi_server
            self._wifi_server = None
            try:
                server_ref.shutdown()
            except:
                pass
            try:
                server_ref.server_close()
            except:
                pass

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't actually send data, just figures out which network interface routes to the internet
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
        finally:
            s.close()

    def handle_wifi_export_click(self, e=None):
        self.close_actions_menu()
        try:
            self._cleanup_existing_wifi_server()
            backup_str = self.create_backup_string()
            
            # Cryptographically secure short-lived LAN token
            token = secrets.token_urlsafe(24)
            app_ref = self

            class Handler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed_path = urllib.parse.urlparse(self.path)
                    query = urllib.parse.parse_qs(parsed_path.query)
                    
                    if parsed_path.path == "/backup.txt" and query.get("t", [""])[0] == token:
                        data = backup_str.encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain")
                        self.send_header("Content-Disposition", f'attachment; filename="workout_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"')
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        
                        # Trigger shutdown 1 second after transfer finishes
                        threading.Timer(1.0, app_ref._trigger_wifi_shutdown).start()
                    else:
                        self.send_response(404)
                        self.end_headers()
                        
                def log_message(self, *args):
                    pass 

            server = ReusableTCPServer(("", 0), Handler)
            port = server.server_address[1]
            
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._wifi_server = server

            # 3. BATTERY PROTECTION: 5-Minute Auto-Timeout
            self._wifi_timeout_timer = threading.Timer(300.0, self._trigger_wifi_shutdown)
            self._wifi_timeout_timer.daemon = True
            self._wifi_timeout_timer.start()

            ip = self._get_local_ip()
            url = f"http://{ip}:{port}/backup.txt?t={token}"

            self._wifi_export_dialog = ft.AlertDialog(
                title=ft.Text("📡 Secure WiFi Export", weight="bold"),
                content=ft.Column([
                    ft.Text("On any laptop or phone on your WiFi network, open your browser and go to:", size=12, color="white70"),
                    ft.TextField(value=url, read_only=True, text_size=13, color="cyan300", border_color="cyan700", text_align="center"),
                    ft.Text("The server will automatically shut down after one successful download or after 5 minutes.", size=11, color="orange300"),
                ], tight=True, spacing=10),
                actions=[
                    ft.ElevatedButton("Cancel Server", on_click=lambda e: self._trigger_wifi_shutdown(), style=ft.ButtonStyle(bgcolor="red900", color="white"))
                ]
            )
            self.safe_open(self._wifi_export_dialog)

        except Exception as err:
            self.show_snackbar(f"WiFi export failed: {err}", "red300")

    def check_wifi_import_pending(self, e=None):
        if getattr(self, '_pending_restore_str', None):
            # 1. Close the server and dismiss the import dialog FIRST
            self._trigger_wifi_shutdown()
            
            # 2. Wait half a second for the Android UI to finish the closing animation, THEN pop the warning
            threading.Timer(0.5, self._safe_pop_warning).start()
        else:
            self.show_snackbar("No backup file received yet.", "amber300")

    def _safe_pop_warning(self):
        # 1. Double-tap the Quick Actions menu to guarantee Flutter purges it from the stack
        if hasattr(self, "actions_menu_dialog") and self.actions_menu_dialog:
            self.safe_close(self.actions_menu_dialog)
            
        # 2. Safely open the overwrite dialog now that the screen is truly clear
        self.trigger_external_restore_warning()
        try: self.page.update()
        except: pass

    def _trigger_wifi_shutdown(self, clear_pending_restore=False):
        if clear_pending_restore:
            self._pending_restore_str = None

        # Cancel the 5-minute timeout if it's still running
        if hasattr(self, '_wifi_timeout_timer') and self._wifi_timeout_timer:
            try: self._wifi_timeout_timer.cancel()
            except: pass
            self._wifi_timeout_timer = None
            
        # Shut down the server WITHOUT blocking the UI thread or causing a socket race condition
        if hasattr(self, '_wifi_server') and self._wifi_server:
            server_ref = self._wifi_server
            
            def _bg_shutdown():
                try: server_ref.shutdown()
                except: pass
                try: server_ref.server_close()
                except: pass
                
            threading.Thread(target=_bg_shutdown, daemon=True).start()
            self._wifi_server = None
            
        # Cleanly close the EXPORT dialog without relying on strict property checks
        if hasattr(self, '_wifi_export_dialog') and self._wifi_export_dialog:
            self.safe_close(self._wifi_export_dialog)

        # Cleanly close the IMPORT dialog without relying on strict property checks
        if hasattr(self, '_wifi_import_dialog') and self._wifi_import_dialog:
            self.safe_close(self._wifi_import_dialog)
            
        try: self.page.update()
        except: pass

    def _parse_multipart_file(self, content_type, body_bytes):
        """Extract the first file field's raw bytes from a multipart/form-data body."""
        if 'boundary=' not in content_type:
            raise ValueError("No multipart boundary found")
        boundary = content_type.split('boundary=')[-1].strip().strip('"')
        boundary_bytes = ('--' + boundary).encode('utf-8')

        for part in body_bytes.split(boundary_bytes):
            if b'Content-Disposition' not in part or b'filename=' not in part:
                continue
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            file_data = part[header_end + 4:]
            if file_data.endswith(b'\r\n'):
                file_data = file_data[:-2]
            return file_data
        raise ValueError("No file field found in upload")

    def handle_wifi_import_click(self, e=None):
        self.close_actions_menu()
        try:
            # Prevent an old upload from being restored if the user starts a fresh import.
            self._pending_restore_str = None
            self._cleanup_existing_wifi_server()

            token = secrets.token_urlsafe(24)
            app_ref = self

            class UploadHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed_path = urllib.parse.urlparse(self.path)
                    query = urllib.parse.parse_qs(parsed_path.query)
                    
                    if parsed_path.path == "/import" and query.get("t", [""])[0] == token:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        
                        # A sleek, dark-mode web UI served directly to your desktop browser
                        html_form = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Restore Workout Database</title>
                            <meta name="viewport" content="width=device-width, initial-scale=1">
                            <style>
                                body {{ font-family: sans-serif; background: #121212; color: #fff; text-align: center; padding: 50px 20px; }}
                                .container {{ max-width: 400px; margin: 0 auto; background: #1e1e1e; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
                                h2 {{ color: #4dd0e1; margin-top: 0; }}
                                p {{ color: #aaaaaa; font-size: 14px; margin-bottom: 25px; }}
                                input[type=file] {{ margin-bottom: 20px; width: 100%; }}
                                button {{ background: #0288d1; color: white; border: none; padding: 12px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; }}
                                button:hover {{ background: #0277bd; }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h2>🛰️ Send Backup to App</h2>
                                <p>Select your compressed .txt backup file to wirelessly beam it to your device.</p>
                                <form action="/upload?t={token}" method="POST" enctype="multipart/form-data">
                                    <input type="file" name="backup_file" accept=".txt" required>
                                    <button type="submit">Upload & Restore</button>
                                </form>
                            </div>
                        </body>
                        </html>
                        """
                        self.wfile.write(html_form.encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()

                def do_POST(self):
                    parsed_path = urllib.parse.urlparse(self.path)
                    query = urllib.parse.parse_qs(parsed_path.query)
                    
                    if parsed_path.path == "/upload" and query.get("t", [""])[0] == token:
                        try:
                            content_len = int(self.headers.get("Content-Length", "0"))
                            if content_len > MAX_BACKUP_TEXT_BYTES:
                                self.send_response(413) # 413 Payload Too Large
                                self.end_headers()
                                error_html = "<h2>❌ Transfer Failed</h2><p>File is too large (Maximum 10MB). Please select a valid backup text file.</p>"
                                self.wfile.write(error_html.encode("utf-8"))
                                return

                            # --- NEW: Safe parsing without the dead CGI module ---
                            body = self.rfile.read(content_len)
                            file_bytes = app_ref._parse_multipart_file(self.headers.get('Content-Type', ''), body)
                            uploaded_data = file_bytes.decode('utf-8')
                            
                            self.send_response(200)
                            self.send_header("Content-Type", "text/html; charset=utf-8")
                            self.end_headers()
                            success_html = "<h2>✅ Transfer Complete!</h2><p>Return to your phone and tap 'Check Upload & Continue'.</p><script>setTimeout(() => window.close(), 3000);</script>"
                            self.wfile.write(success_html.encode("utf-8"))
                            
                            app_ref._pending_restore_str = uploaded_data
                            return

                        except (ValueError, UnicodeDecodeError) as parse_err:
                            self.send_response(400)
                            self.end_headers()
                            self.wfile.write(f"Failed to process upload: {parse_err}".encode("utf-8"))
                            return
                    else:
                        self.send_response(403)
                        self.end_headers()

                def log_message(self, *args):
                    pass

            server = ReusableTCPServer(("", 0), UploadHandler)
            port = server.server_address[1]
            
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._wifi_server = server

            self._wifi_timeout_timer = threading.Timer(300.0, self._trigger_wifi_shutdown)
            self._wifi_timeout_timer.daemon = True
            self._wifi_timeout_timer.start()

            ip = self._get_local_ip()
            url = f"http://{ip}:{port}/import?t={token}"

            self._wifi_import_dialog = ft.AlertDialog(
                title=ft.Text("🛰️ Secure WiFi Import", weight="bold"),
                content=ft.Column([
                    ft.Text("To send a backup to your device, open your computer's browser and go to:", size=12, color="white70"),
                    ft.TextField(value=url, read_only=True, text_size=13, color="cyan300", border_color="cyan700", text_align="center"),
                    # --- UPDATED INSTRUCTIONS BELOW ---
                    ft.Text("After uploading, return here and tap Check Upload & Continue. The server also times out after 5 minutes.", size=11, color="orange300"),
                ], tight=True, spacing=10),
                actions=[
                    ft.ElevatedButton("Check Upload & Continue", on_click=self.check_wifi_import_pending, style=ft.ButtonStyle(bgcolor="green700", color="white")),
                    ft.ElevatedButton("Cancel", on_click=lambda e: self._trigger_wifi_shutdown(clear_pending_restore=True), style=ft.ButtonStyle(bgcolor="red900", color="white"))
                ],
                actions_alignment="spaceBetween"
            )
            self.safe_open(self._wifi_import_dialog)

        except Exception as err:
            self.show_snackbar(f"WiFi import failed: {err}", "red300")
            

    def handle_backup_click(self, e=None):
        self.close_actions_menu()
        try:
            backup_str = self.create_backup_string()
            
            self.export_field = ft.TextField(
                value=backup_str, multiline=True, min_lines=6, max_lines=8, text_size=11, read_only=True
            )
            
            def copy_to_clip(ev):
                self.page.set_clipboard(self.export_field.value)
                self.show_snackbar("Copied to clipboard!", "green300")
            
            self.export_dialog = ft.AlertDialog(
                title=ft.Text("Off-Device Export", weight="bold"),
                content=ft.Column([
                    ft.Text("Your database is now heavily compressed. Tap the box to select all, or use the copy button below.", size=11, color="white70"),
                    self.export_field
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Copy Code", on_click=copy_to_clip),
                    ft.ElevatedButton("Close", on_click=lambda e: self.safe_close(self.export_dialog))
                ], actions_alignment="spaceBetween"
            )
            self.safe_open(self.export_dialog)
        except Exception as err:
            self.show_snackbar(f"Backup prep failed: {err}", "red300")

    def handle_restore_click(self, e=None):
        self.close_actions_menu()
        self.import_field = ft.TextField(
            hint_text="Paste your compressed backup code here...", multiline=True, min_lines=6, max_lines=8, text_size=11
        )
        
        def process_paste(ev):
            raw_str = self.import_field.value.strip()
            if not raw_str:
                self.show_snackbar("Please paste a code first.", "amber300")
                return
            
            # Pass the data to our existing safety net
            self._pending_restore_str = raw_str
            self.safe_close(self.import_dialog)
            self.trigger_external_restore_warning()

        self.import_dialog = ft.AlertDialog(
            title=ft.Text("Off-Device Restore", weight="bold"),
            content=ft.Column([
                ft.Text("Paste your exported code below:", size=11, color="white70"),
                self.import_field
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.safe_close(self.import_dialog)),
                ft.ElevatedButton("Review Code", style=ft.ButtonStyle(bgcolor="blue700", color="white"), on_click=process_paste)
            ], actions_alignment="spaceBetween"
        )
        self.safe_open(self.import_dialog)

    def trigger_external_restore_warning(self):
        self.ext_restore_dialog = ft.AlertDialog(
            title=ft.Text("⚠️ OVERWRITE WARNING", color="red300", weight="bold"),
            content=ft.Text("Loading this file will permanently overwrite your current mesocycle and history. Are you sure?", size=12),
            actions=[
                ft.TextButton("Cancel", on_click=self.close_ext_restore_dialog),
                ft.ElevatedButton("Restore File", style=ft.ButtonStyle(bgcolor="red700", color="white"), on_click=self.execute_pending_external_restore)
            ], actions_alignment="end"
        )
        self.safe_open(self.ext_restore_dialog)

    def close_ext_restore_dialog(self, e=None):
        self._pending_restore_str = None
        if hasattr(self, 'ext_restore_dialog'):
            self.safe_close(self.ext_restore_dialog)

    def execute_pending_external_restore(self, e=None):
        # 1. Catch the string before it gets wiped
        pending = getattr(self, "_pending_restore_str", None)

        # 2. Safely close the dialog (which will wipe self._pending_restore_str)
        if hasattr(self, "ext_restore_dialog"):
            self.safe_close(self.ext_restore_dialog)

        self._pending_restore_str = None

        # 3. Execute the restore using our safely caught string
        if pending:
            self.execute_restore(pending)
        else:
            self.show_snackbar("No restore data found. Please select the backup file again.", "red300")

    def execute_restore(self, raw_str):
        backup_str = "".join(raw_str.split()) 
        if not backup_str:
            self.show_snackbar("File appears empty or invalid!", color="red300")
            return

        # --- NEW: Mobile Memory Guard ---
        if len(backup_str) > MAX_BACKUP_TEXT_BYTES: # 10MB limit prevents RAM crashes
            self.show_snackbar("File is too large to be a valid backup.", color="red300")
            return

        temp_db_path = DB_PATH + ".tmp"
        try:
            decoded_bytes = base64.b64decode(backup_str, validate=True)
            decompressed_db = zlib.decompress(decoded_bytes)
            if len(decompressed_db) > MAX_DECOMPRESSED_DB_BYTES:
                raise ValueError("Backup expands to an unexpectedly large database.")

            with open(temp_db_path, "wb") as f:
                f.write(decompressed_db)

            # --- NEW: INTEGRITY AND STRICT SCHEMA VALIDATION ---
            required_tables = {
                "workout_sessions", "workout_sets", "exercise_dict",
                "readiness_logs", "meso_configs", "meso_names", "user_settings"
            }

            with sqlite3.connect(temp_db_path) as test_conn:
                result = test_conn.execute("PRAGMA integrity_check;").fetchone()[0]
                if result.lower() != "ok":
                    raise ValueError(f"Integrity check failed: {result}")
                    
                rows = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                found_tables = {r[0] for r in rows}
                missing = required_tables - found_tables
                if missing:
                    # --- UPDATED: Sorted missing tables for cleaner errors ---
                    raise ValueError(f"Not a valid workout backup. Missing tables: {', '.join(sorted(missing))}")

            # --- NEW: AUTOMATIC PRE-RESTORE SNAPSHOT (THE UNDO BUTTON) ---
            try:
                pre_restore_str = self.create_backup_string()
                backup_dir = self.get_backup_storage_dir()
                auto_filename = f"pre_restore_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(os.path.join(backup_dir, auto_filename), "w", encoding="utf-8") as f:
                    f.write(pre_restore_str)
            except Exception as auto_err:
                print(f"Silent auto-snapshot failed: {auto_err}")

            
            self.sets.clear()
            self.pr_celebrations.clear()
            self.strength_badges.clear()
            self.show_add_form = False
            self.show_survey = False

            for suffix in ("-wal", "-shm"):
                try:
                    wal_file = DB_PATH + suffix
                    if os.path.exists(wal_file):
                        os.remove(wal_file)
                except: pass

            os.replace(temp_db_path, DB_PATH)
            init_and_seed_db()

            with get_db() as conn:
                cursor = conn.cursor()
                latest_meso = get_latest_meso_number(cursor)
                self.current_meso = latest_meso if latest_meso else 1

            # --- UPDATED: Let the user know the Undo file exists ---
            self.show_snackbar("Database Restored! (Undo snapshot saved)", color="green300")
            self.set_active_position()
            self.build_ui_shell()
            self.rebuild_navigation_headers()
            self.rebuild_entire_display()
            
            # --- ONLY DELETE TEMP FILE AFTER ABSOLUTE SUCCESS ---
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except: pass

        except Exception as err:
            self.show_snackbar(f"Restore failed: {err}", color="red300")
            traceback.print_exc()
            # If we crashed, clean up the corrupted temp file so we can try again
            try:
                if os.path.exists(temp_db_path):
                    os.remove(temp_db_path)
            except: pass

    def export_to_csv(self, e=None):
        self.close_actions_menu()
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ws.date, ws.meso_number, ws.week, ws.day_of_week, ws.exercise, ws.category,
                           ws.target_weight, ws.target_reps, ws.status,
                           (SELECT GROUP_CONCAT(weight || 'x' || reps, ' | ') 
                            FROM (SELECT weight, reps FROM workout_sets WHERE session_id = ws.id ORDER BY set_number ASC)) as sets
                    FROM workout_sessions ws
                    ORDER BY ws.date DESC
                """)
                rows = cursor.fetchall()

            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Date", "Meso", "Week", "Day", "Exercise", "Category", "Target Weight", "Target Reps", "Status", "Logged Sets"])
            writer.writerows(rows)

            self.export_field = ft.TextField(
                value=output.getvalue(), 
                multiline=True, 
                min_lines=8, 
                max_lines=15, 
                text_size=11,
                read_only=True
            )

            def copy_csv_to_clipboard(ev):
                self.page.set_clipboard(self.export_field.value)
                self.show_snackbar("CSV data copied!", "green300")

            self.export_dialog = ft.AlertDialog(
                title=ft.Text("CSV Export Ready"),
                content=ft.Column(
                    [
                        ft.Text("Copy this data to paste into an external spreadsheet:", size=12), 
                        self.export_field
                    ], 
                    tight=True, spacing=10
                ),
                actions=[
                    ft.TextButton(content=ft.Text("Copy CSV"), on_click=copy_csv_to_clipboard),
                    ft.ElevatedButton(content=ft.Text("Close"), on_click=self.close_export_dialog)
                ],
                actions_alignment="spaceBetween"
            )
            self.safe_open(self.export_dialog)
            
        except Exception as err:
            self.show_snackbar(f"Export failed: {err}", "red300")

    def close_export_dialog(self, e=None):
        if hasattr(self, 'export_dialog'):
            self.safe_close(self.export_dialog)

    # -----------------------------------------------

    def category_anchor_key(self, category_name):
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(category_name)).strip("-")
        return f"category-{safe}"

    def exercise_anchor_key(self, session_id):
        return f"exercise-{session_id}"

    def scroll_to_workout_key(self, key):
        """Scroll immediately, then retry after layout settles.

        Promotion rebuilds can finish before Android has measured the newly moved
        card. The second pass keeps the promoted, open exercise in view.
        """
        def do_scroll():
            try:
                self.main_canvas.scroll_to(key=key, duration=350, offset=-8)
                return True
            except TypeError as first_error:
                try:
                    # Some intermediate Flet builds support key but not offset.
                    self.main_canvas.scroll_to(key=key, duration=350)
                    return True
                except TypeError as second_error:
                    # Older Android/Flet packages do not support keyed scrolling
                    # at all. Do not let an optional navigation enhancement crash
                    # the workout screen; promotion and category collapse remain.
                    print(
                        "[scroll_to_workout_key] keyed scrolling unavailable: "
                        f"{second_error} (initial: {first_error})"
                    )
                    return False
                except Exception as ex:
                    print(f"[scroll_to_workout_key fallback] {ex}")
                    return False
            except Exception as ex:
                print(f"[scroll_to_workout_key] {ex}")
                return False

        do_scroll()

        def delayed_scroll():
            time.sleep(0.14)
            do_scroll()

        try:
            self.page.run_thread(delayed_scroll)
        except Exception:
            # Immediate pass above still preserves compatibility if run_thread
            # is unavailable in the packaged runtime.
            pass

    def jump_to_category(self, category_name):
        # Quick-nav behaves like an accordion: open the selected muscle group
        # and collapse every other group programmed for the current day.
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT category
                FROM workout_sessions
                WHERE meso_number = ? AND week = ? AND day_of_week = ?
                ORDER BY category
            """, (self.current_meso, self.current_week, self.current_day))
            day_categories = [row[0] for row in cursor.fetchall() if row[0]]

        for day_category in day_categories:
            self.collapsed_categories[self.category_key(day_category)] = (day_category != category_name)

        self.pending_scroll_key = self.category_anchor_key(category_name)
        self.rebuild_entire_display()

    def activate_exercise(self, category_name, session_id):
        if not category_name:
            return
        key = self.category_key(category_name)
        if self.active_exercise_by_category.get(key) == session_id:
            return
        self.active_exercise_by_category[key] = session_id
        # Keep the promoted exercise's group open and reduce screen clutter.
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT category FROM workout_sessions
                WHERE meso_number = ? AND week = ? AND day_of_week = ?
            """, (self.current_meso, self.current_week, self.current_day))
            for row in cursor.fetchall():
                if row[0]:
                    self.collapsed_categories[self.category_key(row[0])] = (row[0] != category_name)
        self.collapsed_categories[key] = False
        self.pending_scroll_key = self.exercise_anchor_key(session_id)
        self.rebuild_entire_display()

    def get_previous_week_exercise_order(self):
        """Rank exercises by first completed set within each category last week."""
        with get_db() as conn:
            cursor = conn.cursor()
            if str(self.current_week).isdigit() and int(self.current_week) > 1:
                previous_week = str(int(self.current_week) - 1)
            elif str(self.current_week) == "Deload":
                cursor.execute("""
                    SELECT week FROM workout_sessions
                    WHERE meso_number = ? AND day_of_week = ? AND week != 'Deload'
                    ORDER BY CAST(week AS INTEGER) DESC LIMIT 1
                """, (self.current_meso, self.current_day))
                row = cursor.fetchone()
                previous_week = row[0] if row else None
            else:
                previous_week = None
            if previous_week is None:
                return {}
            cursor.execute("""
                SELECT ws.category, ws.exercise, MIN(s.completed_at) AS first_done
                FROM workout_sessions ws
                JOIN workout_sets s ON s.session_id = ws.id
                WHERE ws.meso_number = ? AND ws.week = ? AND ws.day_of_week = ?
                  AND s.is_complete = 1 AND s.completed_at IS NOT NULL
                GROUP BY ws.category, ws.exercise
                ORDER BY ws.category, first_done
            """, (self.current_meso, previous_week, self.current_day))
            rows = cursor.fetchall()
        result = {}
        counters = {}
        for category, exercise, _ in rows:
            counters[category] = counters.get(category, 0) + 1
            result[(category, exercise)] = counters[category]
        return result

    def build_category_quick_nav(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, COUNT(*),
                       SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END)
                FROM workout_sessions
                WHERE meso_number = ? AND week = ? AND day_of_week = ?
                GROUP BY category
                ORDER BY MIN(id)
            """, (self.current_meso, self.current_week, self.current_day))
            rows = cursor.fetchall()

        buttons = []
        for category, total, pending in rows:
            is_done = int(pending or 0) == 0
            buttons.append(ft.Container(
                content=ft.Text(
                    f"{category} ✓" if is_done else str(category),
                    size=10,
                    weight="bold",
                    color="green300" if is_done else "cyan200",
                ),
                bgcolor="green900" if is_done else "white10",
                border_radius=9,
                padding=7,
                ink=True,
                on_click=lambda e, cat=category: self.jump_to_category(cat),
            ))

        if not buttons:
            return None
        return ft.Container(
            content=ft.Column([
                ft.Text("JUMP TO MUSCLE GROUP", size=8, weight="bold", color="white38"),
                ft.Row(buttons, spacing=5, scroll="auto"),
            ], spacing=4, tight=True),
            bgcolor="white5",
            border_radius=8,
            padding=6,
        )

    def category_key(self, category_name):
        return (self.current_meso, self.current_week, self.current_day, category_name)

    def is_category_collapsed(self, category_name):
        return self.collapsed_categories.get(self.category_key(category_name), False)

    def toggle_category(self, category_name):
        key = self.category_key(category_name)
        opening = self.collapsed_categories.get(key, False)
        if opening:
            # Accordion behavior for manual header taps: opening one group closes all others.
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT category FROM workout_sessions
                    WHERE meso_number = ? AND week = ? AND day_of_week = ?
                """, (self.current_meso, self.current_week, self.current_day))
                for row in cursor.fetchall():
                    if row[0]:
                        self.collapsed_categories[self.category_key(row[0])] = (row[0] != category_name)
        else:
            self.collapsed_categories[key] = True
        self.pending_scroll_key = self.category_anchor_key(category_name) if opening else None
        self.rebuild_entire_display()

    def make_category_header(self, category_name, rows_in_cat):
        collapsed = self.is_category_collapsed(category_name)
        total_count = len(rows_in_cat)
        pending_count = sum(1 for row in rows_in_cat if row[4] == STATUS_PENDING)
        is_completed = (pending_count == 0)

        if is_completed:
            arrow = "✓"
            status_text = "All Logged"
            text_color = "green300"
            bg_color = "green900"
            icon_color = "green400"
        else:
            arrow = "▶" if collapsed else "▼"
            status_text = f"{pending_count} of {total_count} remaining"
            text_color = "teal200"
            bg_color = "white10"
            icon_color = "white50"

        title_row = ft.Row([
            ft.Text(arrow, size=12, color=icon_color, weight="bold"),
            ft.Text(category_name.upper(), size=13, weight="bold", color="white"),
        ], spacing=8)

        status_element = ft.Text(status_text, size=11, weight="w600", color=text_color)

        header_container = ft.Container(
            key=self.category_anchor_key(category_name),
            content=ft.Row([title_row, status_element], alignment="spaceBetween"),
            bgcolor=bg_color,
            border_radius=8,
            padding=10,
            margin=4 
        )

        return ft.GestureDetector(
            on_tap=lambda e, cat=category_name: self.toggle_category(cat),
            content=header_container
        )

    def build_summary_view(self):
        self.summary_canvas.controls.clear()
        confetti = ft.Text("🎉", size=50, text_align=ft.TextAlign.CENTER)
        bw = get_user_bodyweight()

        # Calculate Workout Streak
        streak = 0
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, SUM(CASE WHEN status = 'Skipped' THEN 1 ELSE 0 END) as skips
                FROM workout_sessions
                WHERE status IN ('Completed', 'Skipped') AND date IS NOT NULL
                GROUP BY date
                ORDER BY date DESC
            """)
            for r in cursor.fetchall():
                if r[1] == 0:
                    streak += 1
                else:
                    break

            cursor.execute("""
                SELECT s.weight, s.reps, s.rpe, ws.exercise, ws.category, ws.bodyweight_snapshot, s.rest_seconds
                FROM workout_sets s
                JOIN workout_sessions ws ON s.session_id = ws.id
                WHERE ws.meso_number = ? AND ws.week = ? AND ws.day_of_week = ? AND ws.status = 'Completed'
            """, (self.current_meso, self.current_week, self.current_day))

            total_vol = 0
            total_sets = 0
            total_rpe = 0.0
            valid_rpe_sets = 0
            total_rest = 0
            valid_rest_sets = 0
            group_stats = {}

            for sw, sr, srpe, ex_name, cat, snap_bw, rest_secs in cursor.fetchall():
                is_bw = EXERCISE_METADATA.get(ex_name, {}).get("equipment") == "Bodyweight"
                bw_to_use = snap_bw if snap_bw is not None else bw
                effective_weight = (sw + bw_to_use) if is_bw else sw

                total_vol += (effective_weight * sr)
                total_sets += 1

                if cat and cat != "General":
                    if cat not in group_stats:
                        group_stats[cat] = {"sets": 0, "reps": 0}
                    group_stats[cat]["sets"] += 1
                    group_stats[cat]["reps"] += sr

                try:
                    rpe_val = float(srpe)
                    if rpe_val > 0:
                        total_rpe += rpe_val
                        valid_rpe_sets += 1
                except:
                    pass

                if rest_secs is not None:
                    total_rest += rest_secs
                    valid_rest_sets += 1

        pr_count = len(self.pr_celebrations)
        avg_rpe = (total_rpe / valid_rpe_sets) if valid_rpe_sets > 0 else 0.0
        avg_rest_today = (total_rest / valid_rest_sets) if valid_rest_sets > 0 else None

        title = ft.Text(
            "Workout Complete!",
            size=24,
            weight="bold",
            color="green300",
            text_align=ft.TextAlign.CENTER
        )

        streak_badge = ft.Container(
            content=ft.Text(
                f"🔥 {streak} Day Streak! 🔥",
                size=14,
                weight="bold",
                color="orange400"
            ),
            margin=10,
            bgcolor="orange900",
            border_radius=6,
        )

        breakdown_col = ft.Column(spacing=4, horizontal_alignment="center")
        if group_stats:
            for cat in sorted(group_stats.keys()):
                breakdown_col.controls.append(
                    ft.Text(
                        f"• {cat}: {group_stats[cat]['sets']} Sets | {group_stats[cat]['reps']} Reps",
                        size=13,
                        color="cyan100"
                    )
                )
        else:
            breakdown_col.controls.append(
                ft.Text("• General Fitness", size=13, color="cyan100")
            )

        if avg_rpe >= 9.5:
            snark_msg = "Absolute grinder. You lived in the pain cave today."
            snark_color = "red400"
        elif avg_rpe >= 8.0:
            snark_msg = "Right in the hypertrophy sweet spot. Dr. Mike would be proud."
            snark_color = "green400"
        elif avg_rpe >= 7.0:
            snark_msg = "Solid work, but don't be afraid to push closer to failure next week."
            snark_color = "blue300"
        elif avg_rpe > 0:
            snark_msg = "Was this a deload, or just junk volume? Wake up!"
            snark_color = "amber400"
        else:
            snark_msg = "No RPE logged. Did you even lift?"
            snark_color = "white54"

        stats_col = ft.Column([
            streak_badge,
            ft.Text("Targeted Breakdown:", size=14, color="cyan300", weight="bold"),
            breakdown_col,
            ft.Container(height=4),
            ft.Text(f"Total Volume: {total_vol:,.0f} lbs", size=16, color="white"),
            ft.Text(f"Total Sets: {total_sets}", size=16, color="white"),
            ft.Text(
                f"Average RPE: {avg_rpe:.1f}",
                size=16,
                color="amber300" if avg_rpe >= 8 else "white"
            ),
        ], alignment="center", horizontal_alignment="center")

        if avg_rest_today is not None:
            stats_col.controls.append(
                ft.Text(f"Avg Rest Between Sets: {format_duration_seconds(avg_rest_today)}", size=16, color="cyan200")
            )

        stats_col.controls.append(ft.Container(height=4))
        stats_col.controls.append(
            ft.Text(
                snark_msg,
                size=12,
                color=snark_color,
                italic=True,
                text_align=ft.TextAlign.CENTER
            )
        )

        if pr_count > 0:
            stats_col.controls.append(ft.Container(height=4))
            stats_col.controls.append(
                ft.Text(
                    f"New PRs Hit: {pr_count} 🔥",
                    size=16,
                    color="amber300",
                    weight="bold"
                )
            )

        # Pump slider
        pump_slider = ft.Slider(
            min=1,
            max=10,
            divisions=9,
            value=7,
            label="Pump: {value}/10"
        )
        pump_section = ft.Container(
            content=ft.Column([
                ft.Text("Rate Your Pump (1-10)", size=14, weight="bold", color="cyan300"),
                pump_slider
            ], horizontal_alignment="center", spacing=2),
            padding=10,
            bgcolor="white5",
            border_radius=8,
        )
        stats_col.controls.append(pump_section)

        # Weekly recap only on the last planned training day of the week
        planned_days = self.current_week_days()
        is_last_day = (self.current_day == planned_days[-1]) if planned_days else False

        weekly_recap_section = ft.Column(spacing=4, horizontal_alignment="center")
        if is_last_day:
            with get_db() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT SUM(wst.weight * wst.reps), COUNT(wst.id)
                    FROM workout_sets wst
                    JOIN workout_sessions ws ON wst.session_id = ws.id
                    WHERE ws.meso_number = ? AND ws.week = ? AND ws.status = 'Completed'
                """, (self.current_meso, self.current_week))
                w_vol, w_sets = cursor.fetchone()

                cursor.execute("""
                    SELECT AVG(NULLIF(wst.rpe, 0))
                    FROM workout_sets wst
                    JOIN workout_sessions ws ON wst.session_id = ws.id
                    WHERE ws.meso_number = ? AND ws.week = ? AND ws.status = 'Completed'
                """, (self.current_meso, self.current_week))
                w_rpe = cursor.fetchone()[0]

                # Schema-safe Pump recap
                cursor.execute("PRAGMA table_info(readiness_logs)")
                readiness_cols = {row[1] for row in cursor.fetchall()}
                if "pump" in readiness_cols:
                    cursor.execute("""
                        SELECT AVG(NULLIF(pump, 0))
                        FROM readiness_logs
                        WHERE meso_number = ? AND week = ?
                    """, (self.current_meso, self.current_week))
                    w_pump = cursor.fetchone()[0]
                else:
                    w_pump = 0.0

            weekly_recap_section.controls.extend([
                ft.Divider(height=10, color="white24"),
                ft.Text("🏆 WEEKLY RECAP 🏆", size=18, weight="bold", color="amber300"),
                ft.Text(
                    f"Total Weekly Volume: {w_vol:,.0f} lbs" if w_vol else "Total Weekly Volume: 0 lbs",
                    size=14,
                    color="white"
                ),
                ft.Text(f"Total Weekly Sets: {w_sets or 0}", size=14, color="white"),
                ft.Text(
                    f"Avg Weekly RPE: {w_rpe:.1f}" if w_rpe else "Avg Weekly RPE: N/A",
                    size=14,
                    color="white"
                ),
                ft.Text(
                    f"Avg Weekly Pump: {w_pump:.1f}/10" if w_pump else "Avg Weekly Pump: N/A",
                    size=14,
                    color="cyan300"
                ),
                ft.Divider(height=10, color="transparent")
            ])
            stats_col.controls.append(weekly_recap_section)

        def finish_and_advance(e):
            pump_val = int(pump_slider.value)
            with get_db() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE readiness_logs SET pump = ? WHERE meso_number = ? AND week = ? AND day_of_week = ?",
                        (pump_val, self.current_meso, self.current_week, self.current_day)
                    )
                    conn.commit()
                except Exception as ex:
                    print(f"Error saving pump: {ex}")

            self.pr_celebrations.clear()
            self.strength_badges.clear()
            self.meso_just_completed = False
            self.advance_active_position()
            self.rebuild_navigation_headers()
            self.rebuild_entire_display()

        finish_btn = ft.ElevatedButton(
            "Stamp Workout & Advance",
            style=ft.ButtonStyle(bgcolor="green700", color="white", padding=20),
            on_click=finish_and_advance
        )

        meso_complete_section = ft.Column(spacing=8, horizontal_alignment="center")
        if getattr(self, 'meso_just_completed', False):
            meso_complete_section.controls.extend([
                ft.Divider(height=10, color="purple700"),
                ft.Text("🏁 MESOCYCLE COMPLETE 🏁", size=18, weight="bold", color="purple200", text_align=ft.TextAlign.CENTER),
                ft.Text("See how every lift moved from week 1 to the finish.", size=12, color="white54", text_align=ft.TextAlign.CENTER),
                ft.ElevatedButton(
                    "📊 View Full Mesocycle Report",
                    on_click=self.open_meso_report,
                    width=float('inf'),
                    style=ft.ButtonStyle(bgcolor="purple700", color="white", padding=16)
                ),
            ])

        self.summary_canvas.controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        confetti,
                        title,
                        ft.Divider(color="white24"),
                        stats_col,
                        meso_complete_section,
                        ft.Container(height=20),
                        finish_btn
                    ],
                    horizontal_alignment="center",
                    spacing=10
                ),
                padding=40
            )
        )

    def open_meso_report(self, e=None):
        self.close_actions_menu()
        self.view_mode = "meso_report"
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def build_meso_report_view(self):
        self.meso_report_canvas.controls.clear()
        meso = self.current_meso
        meso_label = self.current_meso_label()

        def fmt_num(value):
            try:
                v = float(value)
                return f"{v:g}"
            except:
                return str(value)

        def pct_change(start, finish):
            try:
                start = float(start)
                finish = float(finish)
                return ((finish - start) / start * 100.0) if start > 0 else 0.0
            except:
                return 0.0

        def metric_chip(label, value, color="white", bgcolor="white10"):
            return ft.Container(
                content=ft.Column([
                    ft.Text(label, size=9, color="white54", weight="bold", text_align=ft.TextAlign.CENTER),
                    ft.Text(value, size=12, color=color, weight="bold", text_align=ft.TextAlign.CENTER),
                ], spacing=1, horizontal_alignment="center"),
                bgcolor=bgcolor,
                border_radius=8,
                padding=8,
                expand=True,
            )

        def trend_label(load_pct, reps_delta, e1rm_pct, finish_reps):
            # The meso report separates load progression from rep/e1RM progression.
            # This prevents high-rep Week 1 sets from making heavier target-range finish sets look like failures.
            if load_pct > 2 and 8 <= finish_reps <= 20 and e1rm_pct < 0:
                return "Load ↑ / target reps", "green300"
            if load_pct > 2 and reps_delta < 0:
                return "Heavier load / fewer reps", "cyan300"
            if e1rm_pct > 2:
                return "e1RM ↑", "green300"
            if reps_delta > 0:
                return "Reps ↑", "green300"
            if abs(e1rm_pct) <= 2:
                return "Stable", "white70"
            return "Mixed", "amber300"

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT DISTINCT week FROM workout_sessions WHERE meso_number = ? AND week GLOB '[0-9]*'",
                (meso,)
            )
            numeric_weeks = sorted([r[0] for r in cursor.fetchall()], key=lambda w: int(w))

            if not numeric_weeks:
                self.meso_report_canvas.controls.append(
                    ft.Container(content=ft.Text("No completed data yet for this mesocycle.", color="white54"), padding=20)
                )
                return

            first_week, final_week = numeric_weeks[0], numeric_weeks[-1]

            cursor.execute("""
                SELECT ws.exercise, ws.week, ws.category, s.weight, s.reps, ws.bodyweight_snapshot
                FROM workout_sessions ws
                JOIN workout_sets s ON s.session_id = ws.id
                WHERE ws.meso_number = ?
                  AND ws.status = 'Completed'
                  AND ws.week IN (?, ?)
                  AND COALESCE(ws.week, '') != 'Deload'
            """, (meso, first_week, final_week))
            rows = cursor.fetchall()

            cursor.execute("""
                SELECT ws.date, ws.bodyweight_snapshot FROM workout_sessions ws
                WHERE ws.meso_number = ? AND ws.bodyweight_snapshot IS NOT NULL
                ORDER BY ws.date ASC
            """, (meso,))
            bw_rows = [r for r in cursor.fetchall() if r[1]]

            cursor.execute("""
                SELECT ws.exercise, ws.category, s.weight, s.reps, ws.bodyweight_snapshot
                FROM workout_sessions ws
                JOIN workout_sets s ON s.session_id = ws.id
                WHERE ws.meso_number = ?
                  AND ws.status = 'Completed'
                  AND ws.week = ?
                  AND COALESCE(ws.week, '') != 'Deload'
            """, (meso, first_week))
            first_volume_rows = cursor.fetchall()

            cursor.execute("""
                SELECT ws.exercise, ws.category, s.weight, s.reps, ws.bodyweight_snapshot
                FROM workout_sessions ws
                JOIN workout_sets s ON s.session_id = ws.id
                WHERE ws.meso_number = ?
                  AND ws.status = 'Completed'
                  AND ws.week = ?
                  AND COALESCE(ws.week, '') != 'Deload'
            """, (meso, final_week))
            final_volume_rows = cursor.fetchall()

            # Meso-wide average rest between sets -- spans the whole cycle
            # (not just first/final week), excluding Deload for consistency
            # with the other meso-level stats above, since deload rest
            # patterns are intentionally different and would skew this.
            cursor.execute("""
                SELECT s.rest_seconds FROM workout_sessions ws
                JOIN workout_sets s ON s.session_id = ws.id
                WHERE ws.meso_number = ? AND ws.status = 'Completed'
                  AND COALESCE(ws.week, '') != 'Deload' AND s.rest_seconds IS NOT NULL
            """, (meso,))
            meso_rest_values = [r[0] for r in cursor.fetchall()]

        if first_week == final_week:
            self.meso_report_canvas.controls.append(
                ft.Container(content=ft.Text("Only one week of data — log a few more weeks to see a trend.", color="white54"), padding=20)
            )
            return

        def calc_volume(volume_rows):
            total = 0.0
            for ex, cat, w, r, snap in volume_rows:
                try:
                    w = float(w or 0)
                    r = int(r or 0)
                except:
                    continue
                is_bw = EXERCISE_METADATA.get(ex, {}).get("equipment") == "Bodyweight"
                bw_to_use = snap if snap is not None else get_user_bodyweight()
                total += ((w + bw_to_use) if is_bw else w) * r
            return total

        vol_first = calc_volume(first_volume_rows)
        vol_final = calc_volume(final_volume_rows)

        # Reduce to the best set per exercise per week. Keep both best e1RM and heaviest valid working set.
        best = {}
        for ex, wk, cat, w, r, snap in rows:
            try:
                w_val = float(w or 0)
                r_val = int(r or 0)
            except:
                continue
            if r_val <= 0:
                continue

            is_bw = EXERCISE_METADATA.get(ex, {}).get("equipment") == "Bodyweight"
            e1rm = calculate_e1rm(w_val, r_val, snap if (is_bw and snap) else 0.0)
            best.setdefault(ex, {})
            if wk not in best[ex]:
                best[ex][wk] = {"category": cat, "best_e1rm": e1rm, "e1rm_w": w_val, "e1rm_r": r_val, "heavy_w": w_val, "heavy_r": r_val}
            else:
                if e1rm > best[ex][wk]["best_e1rm"]:
                    best[ex][wk].update({"best_e1rm": e1rm, "e1rm_w": w_val, "e1rm_r": r_val})
                # Use heaviest set as the load-progress anchor; if tied, use higher reps.
                if w_val > best[ex][wk]["heavy_w"] or (w_val == best[ex][wk]["heavy_w"] and r_val > best[ex][wk]["heavy_r"]):
                    best[ex][wk].update({"heavy_w": w_val, "heavy_r": r_val})

        comparisons = []
        for ex, weeks in best.items():
            if first_week in weeks and final_week in weeks:
                start = weeks[first_week]
                finish = weeks[final_week]
                load_delta = finish["heavy_w"] - start["heavy_w"]
                load_pct = pct_change(start["heavy_w"], finish["heavy_w"])
                reps_delta = finish["heavy_r"] - start["heavy_r"]
                e1rm_delta = finish["best_e1rm"] - start["best_e1rm"]
                e1rm_pct = pct_change(start["best_e1rm"], finish["best_e1rm"])
                label, label_color = trend_label(load_pct, reps_delta, e1rm_pct, finish["heavy_r"])
                comparisons.append({
                    "exercise": ex,
                    "category": finish["category"] or start["category"] or "General",
                    "start": start,
                    "finish": finish,
                    "load_delta": load_delta,
                    "load_pct": load_pct,
                    "reps_delta": reps_delta,
                    "e1rm_delta": e1rm_delta,
                    "e1rm_pct": e1rm_pct,
                    "label": label,
                    "label_color": label_color,
                })

        # Sort by load progression first because the report now explicitly separates load/reps/e1RM.
        comparisons.sort(key=lambda c: (c["load_pct"], c["e1rm_pct"]), reverse=True)

        bw_delta = (bw_rows[-1][1] - bw_rows[0][1]) if len(bw_rows) >= 2 else 0.0
        vol_pct = pct_change(vol_first, vol_final)
        load_up_count = sum(1 for c in comparisons if c["load_delta"] > 0)
        e1rm_up_count = sum(1 for c in comparisons if c["e1rm_delta"] > 0)
        avg_meso_rest = (sum(meso_rest_values) / len(meso_rest_values)) if meso_rest_values else None

        self.meso_report_canvas.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("🏁", size=44, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"{meso_label} — Complete", size=20, weight="bold", color="purple200", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"Week {first_week} → Week {final_week}", size=12, color="white54", text_align=ft.TextAlign.CENTER),
                    ft.Text("Load, reps, and estimated strength are shown separately.", size=10, color="white38", text_align=ft.TextAlign.CENTER, italic=True),
                ], horizontal_alignment="center", spacing=4),
                padding=ft.Padding.only(top=16, bottom=8)
            )
        )

        summary_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{load_up_count}/{len(comparisons)}", size=20, weight="bold", color="green300"),
                    ft.Text("Loads Increased", size=10, color="white54"),
                ], horizontal_alignment="center", spacing=2),
                bgcolor="white10", border_radius=8, padding=12, expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{e1rm_up_count}/{len(comparisons)}", size=20, weight="bold", color="cyan300"),
                    ft.Text("e1RM Improved", size=10, color="white54"),
                ], horizontal_alignment="center", spacing=2),
                bgcolor="white10", border_radius=8, padding=12, expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{vol_pct:+.0f}%", size=20, weight="bold", color="cyan300" if vol_pct >= 0 else "red300"),
                    ft.Text("Volume", size=10, color="white54"),
                ], horizontal_alignment="center", spacing=2),
                bgcolor="white10", border_radius=8, padding=12, expand=True
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text(format_duration_seconds(avg_meso_rest) if avg_meso_rest is not None else "—", size=20, weight="bold", color="amber300"),
                    ft.Text("Avg Rest/Set", size=10, color="white54"),
                ], horizontal_alignment="center", spacing=2),
                bgcolor="white10", border_radius=8, padding=12, expand=True
            ),
        ], spacing=8)
        self.meso_report_canvas.controls.append(summary_row)

        if len(bw_rows) >= 2:
            self.meso_report_canvas.controls.append(
                ft.Text(f"Bodyweight change: {bw_delta:+.1f} lbs", size=11, color="amber300" if bw_delta else "white54", text_align=ft.TextAlign.CENTER)
            )

        self.meso_report_canvas.controls.append(ft.Divider(height=20, color="white10"))
        self.meso_report_canvas.controls.append(ft.Text("Per-Exercise Progress", size=14, weight="bold", color="cyan300"))

        if not comparisons:
            self.meso_report_canvas.controls.append(
                ft.Text("No exercises were logged in both the first and final week to compare.", size=12, color="white54")
            )

        for c in comparisons:
            start = c["start"]
            finish = c["finish"]
            max_load = max(start["heavy_w"], finish["heavy_w"], 1)
            start_load_bar = max(2, 90 * (start["heavy_w"] / max_load))
            finish_load_bar = max(2, 90 * (finish["heavy_w"] / max_load))
            load_color = "green300" if c["load_delta"] > 0 else ("red300" if c["load_delta"] < 0 else "white70")
            reps_color = "green300" if c["reps_delta"] > 0 else ("amber300" if c["reps_delta"] < 0 else "white70")
            e1rm_color = "green300" if c["e1rm_delta"] > 0 else ("red300" if c["e1rm_delta"] < 0 else "white70")

            high_rep_note = None
            if start["heavy_r"] > 20 or finish["heavy_r"] > 20:
                high_rep_note = "Note: e1RM is less reliable above ~20 reps; load/reps context matters."

            self.meso_report_canvas.controls.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(c["exercise"], size=13, weight="bold", expand=True),
                        ft.Container(
                            content=ft.Text(c["label"], size=10, weight="bold", color="black"),
                            bgcolor=c["label_color"],
                            border_radius=10,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        ),
                    ], alignment="spaceBetween"),

                    ft.Row([
                        metric_chip("Load", f"{c['load_delta']:+.1f} lb ({c['load_pct']:+.1f}%)", load_color),
                        metric_chip("Reps", f"{c['reps_delta']:+d}", reps_color),
                        metric_chip("e1RM", f"{c['e1rm_pct']:+.1f}%", e1rm_color),
                    ], spacing=6),

                    ft.Row([
                        ft.Text(f"Wk {first_week}: {fmt_num(start['heavy_w'])} x {start['heavy_r']}", size=11, color="white54", width=110),
                        ft.Container(content=ft.Container(width=start_load_bar, height=8, bgcolor="white24", border_radius=4), expand=True),
                    ]),
                    ft.Row([
                        ft.Text(f"Wk {final_week}: {fmt_num(finish['heavy_w'])} x {finish['heavy_r']}", size=11, color="cyan200", width=110),
                        ft.Container(content=ft.Container(width=finish_load_bar, height=8, bgcolor="cyan400", border_radius=4), expand=True),
                    ]),
                    ft.Text(
                        f"Best e1RM: {start['best_e1rm']:.1f} → {finish['best_e1rm']:.1f} lbs ({c['e1rm_delta']:+.1f})",
                        size=10,
                        color="white54"
                    ),
                    ft.Text(high_rep_note, size=9, color="amber200", italic=True) if high_rep_note else ft.Container(height=0),
                ], spacing=6),
                padding=12,
                bgcolor="white10",
                border_radius=8
            ))

    def open_strength_standards(self, e=None):
        self.close_actions_menu()
        self.view_mode = "strength_standards"
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def build_strength_standards_view(self):
        self.strength_standards_canvas.controls.clear()
        bw = get_user_bodyweight()
        age = get_user_age()
        sex = get_user_sex()

        self.strength_standards_canvas.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("📈 Strength Standards", size=20, weight="bold", color="cyan200", text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        f"Based on your best e1RM per lift, {bw:g} lbs bodyweight, age {age}, age-adjusted.",
                        size=11, color="white54", text_align=ft.TextAlign.CENTER
                    ),
                    ft.Text(
                        "Compared against trained lifters who track their numbers — not the general population.",
                        size=10, color="white38", text_align=ft.TextAlign.CENTER, italic=True
                    ),
                ], horizontal_alignment="center", spacing=4),
                padding=ft.Padding.only(top=16, bottom=16)
            )
        )

        with get_db() as conn:
            cursor = conn.cursor()
            any_data = False
            for exercise_name, lift_key in STRENGTH_STANDARD_LIFT_MAP.items():
                cursor.execute("""
                    SELECT s.weight, s.reps FROM workout_sets s
                    JOIN workout_sessions ws ON s.session_id = ws.id
                    WHERE ws.exercise = ? AND ws.status = 'Completed'
                """, (exercise_name,))
                set_rows = cursor.fetchall()
                if not set_rows:
                    continue

                best_e1rm, best_w, best_r = 0.0, 0.0, 0
                for w, r in set_rows:
                    e1rm = calculate_e1rm(w, r)
                    if e1rm > best_e1rm:
                        best_e1rm, best_w, best_r = e1rm, w, r

                classification = get_strength_classification(best_w, best_r, bw, age, sex, exercise_name)
                if not classification:
                    continue

                any_data = True
                top_pct = max(0.5, 100 - classification["percentile"])
                level_colors = {
                    "Beginner": "white54", "Novice": "blue300", "Intermediate": "cyan300",
                    "Advanced": "amber300", "Elite": "purple300"
                }
                lvl_color = level_colors.get(classification["level"], "white")

                self.strength_standards_canvas.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(exercise_name, size=14, weight="bold", expand=True),
                            ft.Container(
                                content=ft.Text(classification["level"], size=11, weight="bold", color="black"),
                                bgcolor=lvl_color, padding=ft.Padding.symmetric(horizontal=10, vertical=4), border_radius=12
                            ),
                        ], alignment="spaceBetween"),
                        ft.Text(f"Best e1RM: {best_e1rm:g} lbs  •  {classification['ratio']:g}x bodyweight", size=12, color="white70"),
                        ft.Text(f"🏆 Top {top_pct:.0f}% of trained lifters in your class", size=13, weight="bold", color="amber300"),
                    ], spacing=4),
                    padding=14, bgcolor="white10", border_radius=10, margin=ft.Margin.only(bottom=8)
                ))

        if not any_data:
            self.strength_standards_canvas.controls.append(
                ft.Container(
                    content=ft.Text(
                        "No eligible lifts logged yet. Standards currently cover: " +
                        ", ".join(sorted(set(STRENGTH_STANDARD_LIFT_MAP.keys()))),
                        size=12, color="white54", text_align=ft.TextAlign.CENTER
                    ),
                    padding=20
                )
            )

    def build_history_view(self):
        self.history_canvas.controls.clear()

        current_bw = get_user_bodyweight()

        selected_days = self.get_selected_days_for_meso(self.current_meso)
        day_order = {day: idx for idx, day in enumerate(self.ordered_day_names(), start=1)}
        current_day_order = day_order.get(self.current_day, 99)

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT length_weeks FROM meso_configs WHERE meso_number = ?",
                (self.current_meso,)
            )
            cfg_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT DISTINCT week, day_of_week
                FROM workout_sessions
                WHERE meso_number = ?
                  AND status = 'Completed'
                """,
                (self.current_meso,)
            )
            completed_rows = cursor.fetchall()

        if str(self.current_week).isdigit():
            current_week_num = int(self.current_week)
            prior_weeks_scheduled = max(0, current_week_num - 1) * len(selected_days)
            this_week_scheduled = len(
                [d for d in selected_days if day_order.get(d, 99) <= current_day_order]
            )
            scheduled_training_days = prior_weeks_scheduled + this_week_scheduled
        else:
            if cfg_row and cfg_row[0]:
                total_weeks = int(cfg_row[0])
            else:
                weeks = [w for w in self.get_existing_weeks() if str(w).isdigit()]
                total_weeks = len(weeks) if weeks else 1
            scheduled_training_days = len(selected_days) * total_weeks

        completed_slots = set()
        for week_val, day_name in completed_rows:
            if not day_name or day_name not in day_order or day_name not in selected_days:
                continue

            if str(self.current_week).isdigit():
                week_num = int(week_val)
                current_week_num = int(self.current_week)

                if week_num < current_week_num:
                    completed_slots.add((str(week_val), day_name))
                elif week_num == current_week_num and day_order.get(day_name, 99) <= current_day_order:
                    completed_slots.add((str(week_val), day_name))
            else:
                completed_slots.add((str(week_val), day_name))

        logged_training_days = len(completed_slots)
        compliance_pct = (
            (logged_training_days / scheduled_training_days) * 100
            if scheduled_training_days > 0 else 0
        )

        header_row = ft.Row([
            ft.Text("Meso Analytics", size=18, weight="bold", color="amber300"),
            ft.TextButton(
                content=ft.Text(f"BW: {current_bw} lbs ✎", size=12, color="cyan300"),
                on_click=self.open_settings_dialog,
                style=ft.ButtonStyle(padding=0)
            )
        ], alignment="spaceBetween")

        insight_banner = ft.Container(
            content=ft.Row([
                ft.Text("📊", size=16),
                ft.Text(
                    f"{logged_training_days} / {scheduled_training_days} Training Days Logged ({compliance_pct:.0f}%)",
                    size=12,
                    weight="bold",
                    color="white"
                )
            ], alignment="center", spacing=8),
            bgcolor="blue900",
            padding=8,
            border_radius=6,
        )

        self.history_canvas.controls.append(header_row)
        self.history_canvas.controls.append(insight_banner)

        def switch_tab(tab_idx):
            for i, btn in enumerate(self.tab_buttons):
                btn.style.bgcolor = "white24" if i == tab_idx else "white10"
                btn.style.color = "amber300" if i == tab_idx else "white"
                btn.update()

            try:
                if tab_idx == 0:
                    self.render_analytics_volume()
                elif tab_idx == 1:
                    self.render_analytics_e1rm()
                elif tab_idx == 2:
                    self.render_analytics_readiness()
            except Exception:
                err_log = traceback.format_exc()
                self.analytics_content.content = ft.Container(
                    content=ft.Text(
                        f"ANALYTICS CRASH:\n\n{err_log}",
                        color="white",
                        size=10,
                        font_family="monospace"
                    ),
                    bgcolor="red900",
                    padding=10,
                    border_radius=8
                )
                try:
                    self.analytics_content.update()
                except:
                    pass

            self.page.update()

        self.tab_buttons = [
            ft.ElevatedButton(
                "Volume",
                style=ft.ButtonStyle(bgcolor="white24", color="amber300"),
                on_click=lambda e: switch_tab(0)
            ),
            ft.ElevatedButton(
                "e1RM Trend",
                style=ft.ButtonStyle(bgcolor="white10", color="white"),
                on_click=lambda e: switch_tab(1)
            ),
            ft.ElevatedButton(
                "Readiness",
                style=ft.ButtonStyle(bgcolor="white10", color="white"),
                on_click=lambda e: switch_tab(2)
            )
        ]

        tab_row = ft.Row(self.tab_buttons, scroll="auto")
        self.analytics_content = ft.Container(padding=10)

        self.history_canvas.controls.append(tab_row)
        self.history_canvas.controls.append(self.analytics_content)

        try:
            self.render_analytics_volume()
        except Exception:
            err_log = traceback.format_exc()
            self.analytics_content.content = ft.Container(
                content=ft.Text(
                    f"ANALYTICS CRASH:\n\n{err_log}",
                    color="white",
                    size=10,
                    font_family="monospace"
                ),
                bgcolor="red900",
                padding=10,
                border_radius=8
            )
            try:
                self.analytics_content.update()
            except:
                pass

    def on_analytics_tab_change(self, e):
        pass
        
    def render_analytics_volume(self):
        bw = get_user_bodyweight()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ws.category, ws.week, wst.weight, wst.reps, ws.exercise, ws.bodyweight_snapshot, wst.rest_seconds
                FROM workout_sessions ws
                JOIN workout_sets wst ON ws.id = wst.session_id
                WHERE ws.status = 'Completed' AND ws.meso_number = ?
            """, (self.current_meso,))
            rows = cursor.fetchall()
            
        if not rows:
            self.analytics_content.content = ft.Text("No volume logged for this meso yet. Go train!", color="white54", italic=True)
            return
            
        category_data = {}
        week_rest_data = {}  # week -> [sum_seconds, count] -- one aggregate per week, not per exercise/category
        for c, w, weight, reps, ex_name, snap_bw, rest_secs in rows:
            is_bw = EXERCISE_METADATA.get(ex_name, {}).get("equipment") == "Bodyweight"
            bw_to_use = snap_bw if snap_bw is not None else bw
            effective_weight = (weight + bw_to_use) if is_bw else weight
            
            if c not in category_data: category_data[c] = {}
            if w not in category_data[c]: category_data[c][w] = {'vol': 0, 'sets': 0, 'reps': 0}
            category_data[c][w]['vol'] += (effective_weight * reps)
            category_data[c][w]['sets'] += 1
            category_data[c][w]['reps'] += reps

            if rest_secs is not None:
                if w not in week_rest_data:
                    week_rest_data[w] = [0, 0]
                week_rest_data[w][0] += rest_secs
                week_rest_data[w][1] += 1
            
        def week_sort_key(wk):
            return 999 if str(wk).lower() == 'deload' else int(wk)

        cat_colors = {
            "Chest": "blue400", "Back": "green400", "Shoulders": "purple400", "Legs": "amber400",
            "Quads": "amber400", "Hamstrings": "orange400", "Glutes": "deeporange400", "Calves": "yellow400", 
            "Biceps": "cyan400", "Triceps": "red400", "Abs": "teal400", "Forearms": "pink400"
        }
        
        col = ft.Column(spacing=10, scroll="auto", height=480)
        col.controls.append(ft.Text("RP Muscle Group Progression", size=14, weight="bold"))
        col.controls.append(ft.Text("Tracking working sets, total reps, and tonnage.", size=11, color="white54"))

        if week_rest_data:
            rest_chip_row = ft.Row(spacing=8, wrap=True)
            for w in sorted(week_rest_data.keys(), key=week_sort_key):
                total_secs, count = week_rest_data[w]
                avg_str = format_duration_seconds(total_secs / count) if count else None
                if avg_str:
                    w_label = f"W{w}" if str(w).isdigit() else str(w)
                    rest_chip_row.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text(w_label, size=10, color="white54"),
                                ft.Text(avg_str, size=14, weight="bold", color="cyan300"),
                            ], spacing=1, horizontal_alignment="center"),
                            bgcolor="white10", border_radius=8, padding=ft.Padding.symmetric(horizontal=12, vertical=6)
                        )
                    )
            col.controls.append(ft.Text("Avg Rest Between Sets", size=12, weight="bold", color="cyan200"))
            col.controls.append(rest_chip_row)
            col.controls.append(ft.Divider(height=1, color="white10"))
        
        for cat, weeks in category_data.items():
            cat_color = cat_colors.get(cat, "white50")
            max_sets = max(data['sets'] for data in weeks.values()) if weeks else 1
            cat_col = ft.Column(spacing=10)
            cat_col.controls.append(ft.Text(cat.upper(), size=14, weight="bold", color=cat_color))
            
            for w in sorted(weeks.keys(), key=week_sort_key):
                data = weeks[w]
                w_label = f"W{w}" if str(w).isdigit() else str(w)
                ratio = data['sets'] / max_sets if max_sets > 0 else 0
                bar_width = 220 * ratio
                
                row_content = ft.Column([
                    ft.Row([
                        ft.Text(w_label, size=12, weight="bold", color="white70", width=35),
                        ft.Text(f"{data['sets']} Sets", size=12, weight="bold", color="white", width=65),
                        ft.Text(f"|  {data['reps']} Reps  |  {data['vol']:,.0f} lbs", size=11, color="white54")
                    ], alignment="start", spacing=4),
                    ft.Container(width=bar_width, height=6, bgcolor=cat_color, border_radius=3)
                ], spacing=2)
                
                cat_col.controls.append(ft.Container(content=row_content, padding=8))
            col.controls.append(ft.Card(content=ft.Container(content=cat_col, padding=14, bgcolor="white10", border_radius=8)))
            
        self.analytics_content.content = col

    def render_analytics_e1rm(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT ws.exercise FROM workout_sessions ws JOIN workout_sets wst ON ws.id = wst.session_id WHERE ws.status='Completed' AND ws.meso_number=?", (self.current_meso,))
            exercises = [r[0] for r in cursor.fetchall()]
        
        if not exercises:
            self.analytics_content.content = ft.Text("No completed exercises to plot.", color="white54")
            return
            
        ex_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(x) for x in exercises],
            value=exercises[0],
            text_size=12,
            expand=True,
            on_select=self.update_e1rm_chart
        )
        self.e1rm_chart_container = ft.Container()
        
        self.analytics_content.content = ft.Column([
            ft.Text("Estimated 1-Rep Max History", size=14, weight="bold"),
            ft.Row([ex_dropdown]),
            self.e1rm_chart_container
        ])
        self.update_e1rm_chart(None, exercises[0])
        
    def update_e1rm_chart(self, e=None, default_ex=None):
        ex_name = default_ex if default_ex else e.control.value
        current_bw = get_user_bodyweight()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ws.date, wst.weight, wst.reps, ws.bodyweight_snapshot 
                FROM workout_sessions ws 
                JOIN workout_sets wst ON ws.id = wst.session_id 
                WHERE ws.exercise=? AND ws.status='Completed' AND ws.meso_number=?
                ORDER BY ws.date ASC
            """, (ex_name, self.current_meso))
            rows = cursor.fetchall()
            
        date_e1rm = {}
        for d, w, r, snap_bw in rows:
            is_bw = EXERCISE_METADATA.get(ex_name, {}).get("equipment") == "Bodyweight"
            bw_to_use = snap_bw if snap_bw is not None else current_bw
            
            max_val = calculate_e1rm(w, r, bw_to_use if is_bw else 0.0)
            if d not in date_e1rm or max_val > date_e1rm[d]:
                date_e1rm[d] = max_val
                
        if len(date_e1rm) == 0:
            self.e1rm_chart_container.content = ft.Text("Not enough data to plot.", color="white54")
            if e: self.page.update()
            return
            
        max_overall = max(date_e1rm.values()) if date_e1rm else 1
        history_col = ft.Column(spacing=8, scroll="auto", height=300)
        
        for date_str, val in date_e1rm.items():
            ratio = val / max_overall if max_overall > 0 else 0
            bar_width = 200 * ratio
            
            row = ft.Column([
                ft.Row([
                    ft.Text(date_str, size=11, color="white70"),
                    ft.Text(f"{val} lbs", size=12, weight="bold", color="cyan300")
                ], alignment="spaceBetween"),
                ft.Container(width=bar_width, height=8, bgcolor="cyan700", border_radius=4)
            ], spacing=2)
            
            history_col.controls.append(ft.Container(content=row, padding=10, bgcolor="white10", border_radius=8))
            
        self.e1rm_chart_container.content = history_col
        if e: self.page.update()

    def render_analytics_readiness(self):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(readiness_logs)")
            readiness_cols = {row[1] for row in cursor.fetchall()}
            pump_expr = "COALESCE(rl.pump, 0)" if "pump" in readiness_cols else "0"
            diet_expr = "COALESCE(rl.diet, 0)" if "diet" in readiness_cols else "0"

            cursor.execute(f"""
                SELECT
                    ws.date,
                    ws.week,
                    CASE WHEN rl.sleep IS NULL THEN 0 ELSE 1 END as readiness_logged,
                    rl.sleep,
                    rl.joints,
                    rl.drive,
                    {pump_expr} as pump,
                    {diet_expr} as diet,
                    wst.rpe
                FROM workout_sessions ws
                LEFT JOIN readiness_logs rl
                    ON ws.meso_number = rl.meso_number AND ws.week = rl.week AND ws.day_of_week = rl.day_of_week
                JOIN workout_sets wst
                    ON ws.id = wst.session_id
                WHERE ws.status = 'Completed' AND ws.meso_number = ?
            """, (self.current_meso,))
            rows = cursor.fetchall()

        if not rows:
            self.analytics_content.content = ft.Text(
                "No readiness data logged for this meso yet. Go train!",
                color="white54",
                italic=True,
            )
            try:
                self.analytics_content.update()
            except:
                pass
            return

        day_stats = {}
        missing_readiness_days = set()
        all_completed_days = set()

        for raw_d, raw_week, readiness_logged, s_score, j_score, d_score, p_score, diet_score, raw_rpe in rows:
            d = raw_d if raw_d else "Unknown Date"
            all_completed_days.add(d)

            if not readiness_logged:
                missing_readiness_days.add(d)
                continue

            if d not in day_stats:
                safe_s = int(s_score or 0)
                safe_j = int(j_score or 0)
                safe_d = int(d_score or 0)
                safe_p = float(p_score or 0)
                safe_diet = int(diet_score or 0)
                
                # Dynamic 10-Point Normalization (Ignores missing metrics like legacy Diet)
                max_pts = 0
                daily_sum = 0
                if safe_s > 0: daily_sum += safe_s; max_pts += 5
                if safe_j > 0: daily_sum += safe_j; max_pts += 5
                if safe_d > 0: daily_sum += safe_d; max_pts += 5
                if safe_diet > 0: daily_sum += safe_diet; max_pts += 5
                
                normalized_score = (daily_sum / max_pts * 10.0) if max_pts > 0 else 0.0

                day_stats[d] = {
                    "week": raw_week,
                    "score": normalized_score,
                    "sleep": safe_s,
                    "joints": safe_j,
                    "drive": safe_d,
                    "pump": safe_p,
                    "diet": safe_diet,
                    "total_rpe": 0.0,
                    "rpe_sets": 0,
                }

            try:
                rpe_val = float(raw_rpe)
                if rpe_val > 0:
                    day_stats[d]["total_rpe"] += rpe_val
                    day_stats[d]["rpe_sets"] += 1
            except:
                pass

        if not day_stats:
            skipped_count = len(missing_readiness_days) if missing_readiness_days else len(all_completed_days)
            self.analytics_content.content = ft.Column([
                ft.Text("No readiness analytics available yet.", color="white54", italic=True),
                ft.Text(
                    f"Completed workout days skipped because no readiness survey was logged: {skipped_count}",
                    size=11,
                    color="amber300",
                ),
            ], spacing=6)
            try:
                self.analytics_content.update()
            except:
                pass
            return

        def summarize_days(day_dicts):
            day_count = len(day_dicts)
            if day_count == 0:
                return {
                    "days": 0, "avg_readiness": 0.0, "avg_rpe": 0.0, "avg_pump": 0.0,
                    "avg_sleep": 0.0, "avg_joints": 0.0, "avg_drive": 0.0, "avg_diet": 0.0,
                }
            
            # Count only days where the specific metric was actively logged
            s_days = sum(1 for d in day_dicts if d["sleep"] > 0)
            j_days = sum(1 for d in day_dicts if d["joints"] > 0)
            d_days = sum(1 for d in day_dicts if d["drive"] > 0)
            diet_days = sum(1 for d in day_dicts if d["diet"] > 0)
            p_days = sum(1 for d in day_dicts if d["pump"] > 0)

            total_readiness = sum(d["score"] for d in day_dicts)
            total_rpe = sum(d["total_rpe"] for d in day_dicts)
            total_rpe_sets = sum(d["rpe_sets"] for d in day_dicts)

            return {
                "days": day_count,
                "avg_readiness": total_readiness / day_count,
                "avg_rpe": total_rpe / total_rpe_sets if total_rpe_sets else 0.0,
                "avg_pump": sum(d["pump"] for d in day_dicts) / p_days if p_days else 0.0,
                "avg_sleep": sum(d["sleep"] for d in day_dicts) / s_days if s_days else 0.0,
                "avg_joints": sum(d["joints"] for d in day_dicts) / j_days if j_days else 0.0,
                "avg_drive": sum(d["drive"] for d in day_dicts) / d_days if d_days else 0.0,
                "avg_diet": sum(d["diet"] for d in day_dicts) / diet_days if diet_days else 0.0,
            }

        # Extract all days, but completely banish "Deload" from the Meso Averages
        all_days = list(day_stats.values())
        meso_days = [d for d in all_days if str(d.get("week")).lower() != "deload"]
        week_days = [d for d in all_days if str(d.get("week")) == str(self.current_week)]

        meso_summary = summarize_days(meso_days)
        week_summary = summarize_days(week_days)

        col = ft.Column(spacing=15, scroll="auto", height=480)

        if missing_readiness_days:
            col.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"Excluded {len(missing_readiness_days)} completed day(s) with no readiness survey logged.",
                        size=11,
                        color="amber300",
                        weight="bold",
                    ),
                    bgcolor="white10",
                    padding=8,
                    border_radius=8,
                )
            )

        col.controls.append(ft.Text("Biofeedback Correlations", size=14, weight="bold"))
        col.controls.append(ft.Text("How your readiness influences perceived effort and pump.", size=11, color="white54"))
        col.controls.append(ft.Text("Readiness tiers: Optimal >8.5 • Moderate 7.0-8.5 • Fatigued <7.0", size=10, color="white54"))

        def readiness_color(val):
            return "green300" if val >= 8.5 else ("amber300" if val >= 7.0 else "red300")

        def make_avg_card(title, summary, empty_note):
            if summary["days"] == 0:
                return ft.Container(
                    content=ft.Column([
                        ft.Text(title, size=12, weight="bold", color="white"),
                        ft.Text(empty_note, size=11, color="white54"),
                    ], spacing=3),
                    expand=True,
                    bgcolor="white10",
                    padding=10,
                    border_radius=8,
                )

            return ft.Container(
                content=ft.Column([
                    ft.Text(title, size=12, weight="bold", color="white"),
                    ft.Text(
                        f"Avg Readiness: {summary['avg_readiness']:.1f} / 10",
                        size=13,
                        weight="bold",
                        color=readiness_color(summary["avg_readiness"]),
                    ),
                    ft.Text(f"Avg RPE: {summary['avg_rpe']:.1f} / 10", size=12, weight="bold", color="white"),
                    ft.Text(f"Avg Pump: {summary['avg_pump']:.1f} / 10", size=11, color="cyan300"),
                    ft.Text(f"Days logged: {summary['days']}", size=10, color="white54"),
                ], spacing=3),
                expand=True,
                bgcolor="white10",
                padding=10,
                border_radius=8,
            )

        col.controls.append(ft.Text("Running Averages", size=14, weight="bold"))
        col.controls.append(
            ft.Row([
                make_avg_card("Week to Date", week_summary, "No readiness days logged this week yet."),
                make_avg_card("Meso to Date", meso_summary, "No readiness days logged this meso yet."),
            ], spacing=6)
        )

        col.controls.append(ft.Container(height=5))
        col.controls.append(ft.Text("Biofeedback Inputs (Meso Grade)", size=14, weight="bold"))

        # Mapping 1-5 Averages to A-F Percentages
        def get_grade_info(val):
            if val == 0: return "N/A", 0, "white54"
            pct = (val / 5.0) * 100
            if pct >= 90: return "A", pct, "green400"
            elif pct >= 80: return "B", pct, "blue400"
            elif pct >= 70: return "C", pct, "amber400"
            elif pct >= 60: return "D", pct, "orange400"
            else: return "F", pct, "red400"
            
        def make_grade_card(label, avg_val):
            grade, pct, color = get_grade_info(avg_val)
            pct_str = f"{pct:.0f}%" if grade != "N/A" else "--"
            return ft.Container(
                content=ft.Column([
                    ft.Text(label, size=10, color="white54", weight="bold"),
                    ft.Text(grade, size=22, color=color, weight="bold"),
                    ft.Text(pct_str, size=11, color="white54")
                ], spacing=0, horizontal_alignment="center"),
                bgcolor="white5", padding=8, border_radius=6, expand=True
            )

        col.controls.append(
            ft.Row([
                make_grade_card("Sleep", meso_summary['avg_sleep']),
                make_grade_card("Joints", meso_summary['avg_joints']),
                make_grade_card("Drive", meso_summary['avg_drive']),
                make_grade_card("Diet", meso_summary['avg_diet']),
            ], spacing=6)
        )

        col.controls.append(ft.Container(height=5))
        col.controls.append(ft.Text("Daily Feedback Timeline", size=14, weight="bold"))

        timeline_col = ft.Column(spacing=10)
        for date_str in sorted(day_stats.keys(), key=lambda x: str(x)):
            data = day_stats[date_str]
            sc = data["score"] # Now a dynamic score out of 10
            pump = data["pump"]
            rpe = data["total_rpe"] / data["rpe_sets"] if data["rpe_sets"] > 0 else 0.0
            sc_ratio = sc / 10.0
            sc_color = "green400" if sc >= 8.5 else ("amber400" if sc >= 7.0 else "red400")
            
            diet_str = f" Dt:{data['diet']}" if data['diet'] > 0 else ""

            row_content = ft.Column([
                ft.Row([
                    ft.Text(date_str, size=11, color="white70", weight="bold"),
                    ft.Text(f"Score: {sc:.1f}/10", size=11, color=sc_color, weight="bold"),
                ], alignment="spaceBetween"),
                ft.Row([
                    ft.Text(
                        f"S:{data['sleep']} J:{data['joints']} Dr:{data['drive']}{diet_str}",
                        size=10,
                        color="white54",
                        font_family="monospace",
                    ),
                    ft.Text(
                        f"RPE: {rpe:.1f} | Pump: {pump:.1f}",
                        size=11,
                        color="white",
                        weight="bold",
                    ),
                ], alignment="spaceBetween"),
                ft.Container(width=220 * sc_ratio, height=4, bgcolor=sc_color, border_radius=2),
            ], spacing=4)

            timeline_col.controls.append(
                ft.Container(content=row_content, padding=10, bgcolor="white10", border_radius=8)
            )

        col.controls.append(timeline_col)
        col.controls.append(ft.Container(height=20))

        self.analytics_content.content = col
        try:
            self.analytics_content.update()
        except:
            pass

    def build_generator_view(self):
        self.generator_canvas.controls.clear()
        
        self.generator_canvas.controls.append(
            ft.Text("SPLIT ARCHITECT", size=18, weight="bold", color="orange300")
        )
        
        self.generator_canvas.controls.append(ft.Text("Step 1: Meso Length (Weeks)", size=12, color="white54"))
        length_slider = ft.Slider(min=3, max=8, divisions=5, value=self.gen_length, label="{value} Weeks", on_change=lambda e: setattr(self, 'gen_length', int(e.control.value)))
        self.generator_canvas.controls.append(length_slider)

        self.generator_canvas.controls.append(ft.Text("Step 2: Select Training Days", size=12, color="white54"))
        days_row = ft.Row(wrap=True, spacing=6)
        for day, is_active in self.gen_days.items():
            days_row.controls.append(
                ft.GestureDetector(
                    on_tap=lambda e, d=day: self.toggle_gen_day(d),
                    content=ft.Container(
                        content=ft.Text(day[:3], size=12, weight="bold", color="white" if is_active else "white54"),
                        padding=10, border_radius=8, bgcolor="orange700" if is_active else "white10"
                    )
                )
            )
        self.generator_canvas.controls.append(days_row)
        
        self.generator_canvas.controls.append(ft.Container(height=10))
        self.generator_canvas.controls.append(ft.Text("Step 3: Build Your Split", size=12, color="white54"))
        
        self.days_cards_column = ft.Column(spacing=10)
        self.render_blueprint_day_cards()
        self.generator_canvas.controls.append(self.days_cards_column)

        self.generator_canvas.controls.append(ft.Container(height=20))
        self.generator_canvas.controls.append(
            ft.Row([
                ft.TextButton("Cancel", on_click=self.cancel_generator_view),
                ft.ElevatedButton("Stamp Custom Meso", style=ft.ButtonStyle(bgcolor="orange600", color="white"), on_click=self.generate_and_stamp_blueprint)
            ], alignment="spaceBetween")
        )
        self.generator_canvas.controls.append(ft.Container(height=80))

    def toggle_gen_day(self, day_str):
        self.gen_days[day_str] = not self.gen_days[day_str]
        self.build_generator_view()
        self.main_canvas.update()

    def move_ex_up(self, day, idx):
        if idx > 0:
            self.gen_blueprint[day][idx], self.gen_blueprint[day][idx-1] = self.gen_blueprint[day][idx-1], self.gen_blueprint[day][idx]
            self.render_blueprint_day_cards()
            self.main_canvas.update()

    def move_ex_down(self, day, idx):
        if idx < len(self.gen_blueprint[day]) - 1:
            self.gen_blueprint[day][idx], self.gen_blueprint[day][idx+1] = self.gen_blueprint[day][idx+1], self.gen_blueprint[day][idx]
            self.render_blueprint_day_cards()
            self.main_canvas.update()

    def render_blueprint_day_cards(self):
        self.days_cards_column.controls.clear()
        if not hasattr(self, 'gen_blueprint'):
            self.gen_blueprint = {d: [] for d in self.gen_days.keys()}
            
        for day, is_active in self.gen_days.items():
            if not is_active: continue
            
            ex_list_col = ft.Column(spacing=2)
            for i, ex_name in enumerate(self.gen_blueprint.get(day, [])):
                controls_row = ft.Row([
                    ft.TextButton(content=ft.Text("✎", color="blue400", size=16), style=ft.ButtonStyle(padding=2), width=35, on_click=lambda e, d=day, idx=i: self.open_edit_blueprint_ex_dialog(d, idx)),
                    ft.TextButton(content=ft.Text("↑", color="white54", size=16), style=ft.ButtonStyle(padding=2), width=35, on_click=lambda e, d=day, idx=i: self.move_ex_up(d, idx)),
                    ft.TextButton(content=ft.Text("↓", color="white54", size=16), style=ft.ButtonStyle(padding=2), width=35, on_click=lambda e, d=day, idx=i: self.move_ex_down(d, idx)),
                    ft.TextButton(content=ft.Text("✕", color="red400", size=16), style=ft.ButtonStyle(padding=2), width=35, on_click=lambda e, d=day, idx=i: self.remove_ex_from_blueprint(d, idx))
                ], spacing=0)
                
                ex_list_col.controls.append(
                    ft.Row([
                        ft.Text(f"{i+1}. {ex_name}", size=12, color="white", expand=True),
                        controls_row
                    ], alignment="spaceBetween")
                )
                
            if not self.gen_blueprint.get(day):
                ex_list_col.controls.append(ft.Text("Rest Day (Intentional)", size=11, color="white30", italic=True))
                
            add_btn = ft.TextButton("+ Add Movement", on_click=lambda e, d=day: self.open_blueprint_ex_dialog(d))
            
            card = ft.Card(content=ft.Container(
                content=ft.Column([
                    ft.Text(day, size=14, weight="bold", color="cyan300"),
                    ex_list_col,
                    add_btn
                ]), padding=12, bgcolor="white10", border_radius=8
            ))
            self.days_cards_column.controls.append(card)

    def remove_ex_from_blueprint(self, day, idx):
        self.gen_blueprint[day].pop(idx)
        self.render_blueprint_day_cards()
        self.main_canvas.update()
        
    def open_blueprint_ex_dialog(self, day):
        self.active_blueprint_day = day

        ex_dict = self.load_exercise_dict()
        options = []
        for cat, exercises in ex_dict.items():
            options.append(ft.dropdown.Option(text=f"─── {cat.upper()} ───", disabled=True))
            for ex in exercises:
                options.append(ft.dropdown.Option(key=ex, text=ex))

        self.bp_dropdown = ft.Dropdown(label="Select Movement", options=options, expand=True, text_size=12)
        
        self.blueprint_dialog = ft.AlertDialog(
            title=ft.Text(f"Add to {day}", size=15, weight="bold"),
            content=ft.Container(width=280, content=self.bp_dropdown),
            actions=[
                ft.TextButton("Done", on_click=self.close_blueprint_dialog),
                ft.ElevatedButton("Add", style=ft.ButtonStyle(bgcolor="blue700", color="white"), on_click=self.confirm_blueprint_ex)
            ], actions_alignment="end"
        )
        self.safe_open(self.blueprint_dialog)
        
    def close_blueprint_dialog(self, e=None):
        if hasattr(self, 'blueprint_dialog'):
            self.safe_close(self.blueprint_dialog)
        
    def confirm_blueprint_ex(self, e):
        val = self.bp_dropdown.value
        if val:
            if self.active_blueprint_day not in self.gen_blueprint:
                self.gen_blueprint[self.active_blueprint_day] = []
                
            if val in self.gen_blueprint[self.active_blueprint_day]:
                self.show_snackbar(f"{val} is already in {self.active_blueprint_day}.", "red300")
            else:
                self.gen_blueprint[self.active_blueprint_day].append(val)
                self.show_snackbar(f"Added {val}", "green300")
                
                self.bp_dropdown.value = None
                try:
                    self.bp_dropdown.update()
                except:
                    pass
                
        self.render_blueprint_day_cards()
        self.main_canvas.update()

    def open_edit_blueprint_ex_dialog(self, day, idx):
        self.active_blueprint_day = day
        self.active_blueprint_idx = idx
        current_ex = self.gen_blueprint[day][idx]

        ex_dict = self.load_exercise_dict()
        options = []
        for cat, exercises in ex_dict.items():
            options.append(ft.dropdown.Option(text=f"─── {cat.upper()} ───", disabled=True))
            for ex in exercises:
                options.append(ft.dropdown.Option(key=ex, text=ex))

        self.bp_edit_dropdown = ft.Dropdown(label="Select Replacement", value=current_ex, options=options, expand=True, text_size=12)
        
        self.blueprint_edit_dialog = ft.AlertDialog(
            title=ft.Text(f"Replace Movement", size=15, weight="bold"),
            content=ft.Container(width=280, content=self.bp_edit_dropdown),
            actions=[
                ft.TextButton("Cancel", on_click=self.close_edit_blueprint_dialog),
                ft.ElevatedButton("Swap", style=ft.ButtonStyle(bgcolor="blue700", color="white"), on_click=self.confirm_edit_blueprint_ex)
            ], actions_alignment="end"
        )
        self.safe_open(self.blueprint_edit_dialog)
        
    def close_edit_blueprint_dialog(self, e=None):
        if hasattr(self, 'blueprint_edit_dialog'):
            self.safe_close(self.blueprint_edit_dialog)
        
    def confirm_edit_blueprint_ex(self, e):
        val = self.bp_edit_dropdown.value
        day = self.active_blueprint_day
        idx = self.active_blueprint_idx
        
        if val:
            current_ex = self.gen_blueprint[day][idx]
            if val != current_ex and val in self.gen_blueprint[day]:
                self.show_snackbar(f"{val} is already in {day}.", "red300")
            else:
                self.gen_blueprint[day][idx] = val
                
        self.close_edit_blueprint_dialog()
        self.render_blueprint_day_cards()
        self.main_canvas.update()

    def generate_and_stamp_blueprint(self, e):
        active_days = [day for day, active in self.gen_days.items() if active]
        
        if not active_days:
            self.show_snackbar("Please select at least one training day.", "red300")
            return
            
        has_exercises = any(len(self.gen_blueprint.get(d, [])) > 0 for d in active_days)
        if not has_exercises:
            self.show_snackbar("Please add at least one exercise somewhere in your split.", "red300")
            return

        blueprint_sessions = []
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        with get_db() as conn:
            cursor = conn.cursor()
            new_meso_num = get_next_meso_number(cursor)
            
            ex_pool = {}
            cursor.execute("SELECT name, category, movement_pattern FROM exercise_dict")
            for name, db_cat, pattern in cursor.fetchall():
                ex_pool[name] = {"category": db_cat, "pattern": pattern}

            for day in active_days:
                for ex_name in self.gen_blueprint.get(day, []):
                    cat = ex_pool.get(ex_name, {}).get("category", "General")
                    sw, sr, st = get_exercise_smart_defaults(ex_name, self.current_meso)
                    
                    blueprint_sessions.append((
                        today_str, ex_name, cat, day, '1', sw, sr, STATUS_PENDING, st, new_meso_num
                    ))
            
            if blueprint_sessions:
                cursor.executemany("""
                    INSERT INTO workout_sessions (date, exercise, category, day_of_week, week, target_weight, target_reps, status, movement_type, meso_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, blueprint_sessions)

            filtered_blueprint = {d: self.gen_blueprint.get(d, []) for d in active_days}

            upsert_meso_config(
                cursor,
                new_meso_num,
                self.gen_length,
                json.dumps(active_days),
                json.dumps({"mode": "manual"}), 
                0, 
                json.dumps(filtered_blueprint)
            )

            cursor.execute("INSERT INTO meso_names (meso_number, meso_label) VALUES (?, ?)", (new_meso_num, f"Custom Meso {new_meso_num}"))
            conn.commit()

        self.sets.clear()
        self.current_meso = new_meso_num
        self.current_week = '1'
        self.view_mode = "workout"
        self.set_active_position()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()
        self.show_snackbar(f"Custom Meso {new_meso_num} Stamped Successfully!", "green300")

    def save_wizard_addition(self, e):
        ex_name = self.wizard_custom_input.value.strip() or self.wizard_exercise_dropdown.value
        if not ex_name:
            self.show_snackbar("Please select or type an exercise.", "red300")
            return
            
        try:
            w = float(self.wizard_weight_input.value.strip())
            r = int(self.wizard_reps_input.value.strip())
        except ValueError:
            self.show_snackbar("Weight and Reps must be numeric.", "red300")
            return
            
        cat = self.wizard_cat_dropdown.value
        m_type = self.wizard_type_dropdown.value
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        with get_db() as conn:
            cursor = conn.cursor()
            if self.wizard_custom_input.value.strip():
                cursor.execute("INSERT OR IGNORE INTO exercise_dict (name, category, movement_pattern) VALUES (?, ?, 'General')", (ex_name, cat))
            
            cursor.execute(
                "INSERT INTO workout_sessions (date, exercise, category, day_of_week, week, target_weight, target_reps, status, movement_type, meso_number) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (today_str, ex_name, cat, self.current_day, self.current_week, w, r, STATUS_PENDING, m_type, self.current_meso)
            )
            conn.commit()
            
        self.show_add_form = False
        self.wizard_custom_input.value = ""
        self.rebuild_entire_display()

    def rebuild_navigation_headers(self):
        # Completed and inactive mesocycles now live in Menu > Mesocycle.
        # The workout header shows only the active mesocycle title.
        self.current_meso_title.value = self.current_meso_label()

        week_completions = {}
        day_completions = {}
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT week, COUNT(*), SUM(CASE WHEN status IN ('Completed', 'Skipped') THEN 1 ELSE 0 END) FROM workout_sessions WHERE meso_number = ? GROUP BY week", (self.current_meso,))
            for w, total, comp in cursor.fetchall():
                week_completions[str(w)] = (total > 0 and total == comp)
                
            cursor.execute("SELECT day_of_week, COUNT(*), SUM(CASE WHEN status IN ('Completed', 'Skipped') THEN 1 ELSE 0 END) FROM workout_sessions WHERE meso_number = ? AND week = ? GROUP BY day_of_week", (self.current_meso, self.current_week))
            for d_str, total, comp in cursor.fetchall():
                day_completions[d_str] = (total > 0 and total == comp)

        # 2. Sleek Week Tabs
        self.week_nav_row.controls.clear()
        for w in self.get_existing_weeks():
            is_done = week_completions.get(str(w), False)
            is_active = (str(w) == str(self.current_week))
            check_str = " ✓" if is_done else ""
            
            txt_color = "grey900" if is_active else ("green300" if is_done else "white70")
            bg_color = "amber300" if is_active else ("green900" if is_done else "white5")
            border_color = "amber200" if is_active else ("green700" if is_done else "white10")

            btn = ft.Container(
                content=ft.Text(f"W{w}{check_str}", size=13, weight="bold", color=txt_color),
                padding=8,
                bgcolor=bg_color,
                border=ft.Border(top=ft.BorderSide(1, border_color), right=ft.BorderSide(1, border_color), bottom=ft.BorderSide(1, border_color), left=ft.BorderSide(1, border_color)),
                border_radius=12,
                on_click=lambda e, wk=w: self.change_active_week(wk),
                ink=True
            )
            self.week_nav_row.controls.append(btn)
            
        # 3. Sleek Day Tabs
        self.day_nav_row.controls.clear()
        for d in self.ordered_day_names():
            is_done = day_completions.get(d, False)
            is_active = (d == self.current_day)
            check_str = "✓" if is_done else ""
            
            txt_color = "grey900" if is_active else ("green300" if is_done else "white54")
            weight = "bold" if (is_active or is_done) else "w500"
            bg_color = "amber300" if is_active else ("green900" if is_done else "transparent")
            border_color = "amber200" if is_active else ("green700" if is_done else "transparent")

            btn = ft.Container(
                content=ft.Text(f"{d[:3]} {check_str}".strip(), size=12, weight=weight, color=txt_color),
                padding=7,
                bgcolor=bg_color,
                border=ft.Border(top=ft.BorderSide(1, border_color), right=ft.BorderSide(1, border_color), bottom=ft.BorderSide(1, border_color), left=ft.BorderSide(1, border_color)),
                border_radius=12,
                on_click=lambda e, day_str=d: self.change_active_day(day_str),
                ink=True
            )
            self.day_nav_row.controls.append(btn)
        
        try:
            self.navigation_header_container.update()
        except:
            pass

    def change_active_meso(self, meso_num):
        self.current_meso = meso_num
        self.set_active_position()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def change_active_week(self, week_str):
        self.set_active_position(force_week=week_str)
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def change_active_day(self, day_str):
        self.current_day = day_str
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()

    def toggle_add_exercise_form(self, e):
        self.show_add_form = not self.show_add_form
        self.rebuild_entire_display()

    def update_wizard_stats(self, ex_name):
        w, r, mov_type = get_exercise_smart_defaults(ex_name, self.current_meso)
        self.wizard_weight_input.value = str(w)
        self.wizard_reps_input.value = str(r)
        self.wizard_type_dropdown.value = mov_type
        meta = EXERCISE_METADATA.get(ex_name, {})
        if meta:
            self.wizard_cat_dropdown.value = meta.get("category", "General")

    def rebuild_readiness_survey_layer(self):
        self.survey_panel.content = None
        if self.current_day not in self.current_week_days(): return
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM workout_sessions WHERE meso_number=? AND week=? AND day_of_week=? AND status='Pending'", (self.current_meso, self.current_week, self.current_day))
            if cursor.fetchone()[0] == 0: return
            cursor.execute("SELECT COUNT(*) FROM readiness_logs WHERE meso_number=? AND week=? AND day_of_week=?", (self.current_meso, self.current_week, self.current_day))
            if cursor.fetchone()[0] > 0: return

        def save_survey(e):
            with get_db() as conn:
                # Safely inserts Sleep, Joints, Drive, and our new Diet Discipline metric
                conn.cursor().execute(
                    "INSERT OR REPLACE INTO readiness_logs (date, sleep, joints, drive, diet, meso_number, week, day_of_week) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                    (datetime.now().strftime("%Y-%m-%d"), int(sleep_s.value), int(joint_s.value), int(drive_s.value), int(diet_s.value), self.current_meso, self.current_week, self.current_day)
                )
                conn.commit()
            self.rebuild_entire_display()

        # Cleaned up labels since the titles are now floating above them
        sleep_s = ft.Slider(min=1, max=5, divisions=4, value=3, label="{value}")
        joint_s = ft.Slider(min=1, max=5, divisions=4, value=3, label="{value}")
        drive_s = ft.Slider(min=1, max=5, divisions=4, value=3, label="{value}")
        diet_s = ft.Slider(min=1, max=5, divisions=4, value=3, label="{value}")
        
        self.survey_panel.content = ft.Card(
            content=ft.Container(
                padding=15, 
                content=ft.Column([
                    ft.Text("☀️ Daily Readiness Check", weight="bold", color="amber300", size=14),
                    ft.Divider(height=1, color="white10"),
                    
                    # Row 1: Sleep & Joints
                    ft.Row([
                        ft.Column([ft.Text("Sleep", size=11, color="white70", weight="bold"), sleep_s], expand=True, horizontal_alignment="center", spacing=0),
                        ft.Column([ft.Text("Joints", size=11, color="white70", weight="bold"), joint_s], expand=True, horizontal_alignment="center", spacing=0),
                    ], alignment="spaceBetween"),
                    
                    # Row 2: Drive & Diet
                    ft.Row([
                        ft.Column([ft.Text("Drive", size=11, color="white70", weight="bold"), drive_s], expand=True, horizontal_alignment="center", spacing=0),
                        ft.Column([ft.Text("Diet Discipline", size=11, color="cyan300", weight="bold"), diet_s], expand=True, horizontal_alignment="center", spacing=0),
                    ], alignment="spaceBetween"),
                    
                    ft.Container(height=2), # Tiny spacer
                    
                    # Full-width action button
                    ft.ElevatedButton("Log Readiness", on_click=save_survey, width=float('inf'), height=35, style=ft.ButtonStyle(bgcolor="blue700", color="white"))
                ], spacing=8, tight=True)
            )
        )

    def save_active_rename(self, e):
        new_name = self.input_rename_field.value.strip()
        if new_name:
            with get_db() as conn:
                conn.cursor().execute("UPDATE meso_names SET meso_label = ? WHERE meso_number = ?", (new_name, self.current_meso))
                conn.commit()
            self.close_rename_dialog()
            self.rebuild_navigation_headers()
            self.rebuild_entire_display()

    def delete_meso_final_confirmed(self, e):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workout_sessions WHERE meso_number = ?", (self.current_meso,))
            cursor.execute("DELETE FROM meso_configs WHERE meso_number = ?", (self.current_meso,))
            cursor.execute("DELETE FROM meso_names WHERE meso_number = ?", (self.current_meso,))
            cursor.execute("DELETE FROM readiness_logs WHERE meso_number = ?", (self.current_meso,))
            conn.commit()
            
            latest = get_latest_meso_number(cursor)
            self.current_meso = latest if latest else 1
            if not latest:
                seed_meso_week_one(self.current_meso)
        
        self.close_delete_confirm_dialog()
        self.set_active_position()
        self.rebuild_navigation_headers()
        self.rebuild_entire_display()
        self.show_snackbar("Mesocycle Wiped.", "red300")

    def run_progression_engine(self, mode):
        next_w = "Deload" if mode == "Deload" else str(int(self.current_week) + 1)
        try:
            with get_db() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT exercise, category, day_of_week, target_weight, target_reps, movement_type "
                    "FROM workout_sessions WHERE meso_number = ? AND week = ?",
                    (self.current_meso, self.current_week)
                )
                all_current_week_exercises = cursor.fetchall()

                if not all_current_week_exercises:
                    self.show_snackbar(
                        f"No exercises found for Week {self.current_week} (Meso {self.current_meso}). "
                        "Cannot advance — nothing to copy forward.",
                        "red300"
                    )
                    return

                new_sessions = []
                today_str = datetime.now().strftime("%Y-%m-%d")

                for ex, cat, day, tw, tr, mov_type in all_current_week_exercises:
                    try:
                        new_w, new_r, _ = get_exercise_smart_defaults(ex, self.current_meso)
                    except Exception as def_err:
                        # A single exercise's computation failing must never block
                        # the rest of the week -- fall back to its own stored target.
                        print(f"[run_progression_engine] smart defaults failed for '{ex}': {def_err}")
                        is_bw_fallback = EXERCISE_METADATA.get(ex, {}).get("equipment") == "Bodyweight"
                        new_w = float(tw) if tw is not None else (0.0 if is_bw_fallback else 45.0)
                        new_r = int(tr) if tr is not None else 10

                    if mode == "Deload":
                        is_bw = EXERCISE_METADATA.get(ex, {}).get("equipment") == "Bodyweight"
                        new_w = new_w * 0.65 if not is_bw else new_w
                        # tr is this week's stored target_reps -- guard against None
                        # before floor-dividing (a None here previously crashed silently).
                        safe_tr = int(tr) if tr is not None else 10
                        new_r = max(1, safe_tr // 2)

                    new_sessions.append((today_str, ex, cat, day, next_w, new_w, new_r, "Pending", mov_type, self.current_meso))

                if new_sessions:
                    cursor.executemany(
                        "INSERT INTO workout_sessions (date, exercise, category, day_of_week, week, target_weight, target_reps, status, movement_type, meso_number) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        new_sessions
                    )
                conn.commit()

        except Exception as engine_err:
            # This is the safety net: whatever goes wrong, the user sees it
            # instead of the button silently doing nothing.
            error_detail = traceback.format_exc()
            print(f"[run_progression_engine] FAILED:\n{error_detail}")
            self.show_snackbar(f"Progression engine failed: {engine_err}", "red300")
            return

        self.current_week = next_w

        try:
            self.set_active_position(force_week=self.current_week)
        except Exception as e:
            print(f"[run_progression_engine] set_active_position failed: {e}")

        try:
            self.rebuild_navigation_headers()
        except Exception as e:
            print(f"[run_progression_engine] rebuild_navigation_headers failed: {e}")

        # Unconditional -- runs regardless of what happened above, and has its
        # own internal crash-report display if rendering itself fails.
        self.rebuild_entire_display()
        self.show_snackbar(f"Advanced to Week {next_w}!", "green300")

    def rebuild_entire_display(self):
        try:
            self.main_canvas.controls.clear()    

            self.week_header_row.visible = (self.view_mode == "workout")
            self.day_header_row.visible = (self.view_mode == "workout")

            if self.view_mode == "generator":
                self.build_generator_view()
                self.main_canvas.controls.append(self.generator_canvas)
                self.main_canvas.update()
                self.page.update()
                return

            if self.view_mode == "history":
                self.build_history_view()
                self.main_canvas.controls.append(self.history_canvas)
                self.main_canvas.update()
                self.page.update()
                return
                
            if self.view_mode == "summary":
                self.build_summary_view()
                self.main_canvas.controls.append(self.summary_canvas)
                self.main_canvas.update()
                self.page.update()
                return

            if self.view_mode == "meso_report":
                self.build_meso_report_view()
                self.main_canvas.controls.append(self.meso_report_canvas)
                self.main_canvas.update()
                self.page.update()
                return

            if self.view_mode == "strength_standards":
                self.build_strength_standards_view()
                self.main_canvas.controls.append(self.strength_standards_canvas)
                self.main_canvas.update()
                self.page.update()
                return

            planned_days = self.current_week_days()
            current_day_is_planned = self.current_day in planned_days
            current_day_is_rest = self.is_planned_rest_day(self.current_day)

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM workout_sessions WHERE week = ? AND meso_number = ?", (self.current_week, self.current_meso))
                row_count = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT COUNT(*) FROM workout_sessions WHERE week = ? AND meso_number = ? AND day_of_week = ?",
                    (self.current_week, self.current_meso, self.current_day)
                )
                current_day_row_count = cursor.fetchone()[0]

            if row_count == 0 and self.current_week == "1" and not planned_days:
                seed_meso_week_one(self.current_meso)
                self.set_active_position()
                self.rebuild_navigation_headers()
                planned_days = self.current_week_days()
                current_day_is_planned = self.current_day in planned_days
                current_day_is_rest = self.is_planned_rest_day(self.current_day)

            self.rebuild_readiness_survey_layer()

            if self.survey_panel.content:
                self.main_canvas.controls.append(self.survey_panel)

            if current_day_is_planned and current_day_row_count == 0:
                title_text = "🌙 Planned Rest Day" if current_day_is_rest else "No Sessions Stamped Yet"
                body_text = (
                    "This selected day is intentionally empty in your split blueprint."
                    if current_day_is_rest
                    else "This day is selected in the meso blueprint, but no workout rows exist for this week yet."
                )
                self.main_canvas.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(title_text, size=14, weight="bold", color="blue200"),
                            ft.Text(body_text, size=11, color="white70"),
                        ], spacing=4),
                        bgcolor="white10",
                        padding=12,
                        border_radius=8
                    )
                )
                self.main_canvas.controls.append(ft.Container(height=4))

            # --- NEW DIET-AWARE READINESS BANNER ---
            with get_db() as conn:
                cursor = conn.cursor()
                # Safely check if diet exists for legacy compatibility
                cursor.execute("PRAGMA table_info(readiness_logs)")
                r_cols = {row[1] for row in cursor.fetchall()}
                diet_expr = "diet" if "diet" in r_cols else "0 as diet"

                cursor.execute(f"SELECT sleep, joints, drive, {diet_expr} FROM readiness_logs WHERE meso_number = ? AND week = ? AND day_of_week = ?", (self.current_meso, self.current_week, self.current_day))
                r_row = cursor.fetchone()
                
                if r_row:
                    sleep_s, joint_s, drive_s, diet_s = r_row
                    
                    # 1. Backend Math (Kept safely out of 15 for progression logic)
                    t_score = sleep_s + joint_s + drive_s 
                    
                    # 2. Frontend Math (Dynamic 10-point normalization)
                    max_pts = 0
                    daily_sum = 0
                    if sleep_s > 0: daily_sum += sleep_s; max_pts += 5
                    if joint_s > 0: daily_sum += joint_s; max_pts += 5
                    if drive_s > 0: daily_sum += drive_s; max_pts += 5
                    if diet_s > 0: daily_sum += diet_s; max_pts += 5
                    
                    normalized_score = (daily_sum / max_pts * 10.0) if max_pts > 0 else 0.0
                    
                    banner_texts = []
                    if t_score <= 7:
                        banner_texts.append("Fatigue: -10% Load")
                    if joint_s <= 2:
                        banner_texts.append("Joints: -15% Load Compound")
                    
                    score_color = "green300" if normalized_score >= 8.5 else ("amber300" if normalized_score >= 7.0 else "red400")

                    diet_string = f" • Diet: {diet_s}" if diet_s > 0 else ""

                    readiness_text = ft.Row([
                        ft.Text("✅ Readiness:", size=11, weight="bold", color="white70"),
                        ft.Text(f"{normalized_score:.1f}/10", size=11, weight="bold", color=score_color),
                        ft.Text(f"(Sleep: {sleep_s} • Joints: {joint_s} • Drive: {drive_s}{diet_string})", size=10, color="white54")
                    ], spacing=4, wrap=True)

                    content_col = [readiness_text]
                    
                    if banner_texts:
                        content_col.append(ft.Text("⚠️ Penalty: " + " • ".join(banner_texts), size=10, color="amber300", italic=True))
                    
                    summary_container = ft.Container(
                        content=ft.Column(content_col, spacing=1, tight=True),
                        bgcolor="white5",
                        padding=6,
                        border_radius=6
                    )
                    self.main_canvas.controls.append(summary_container)
            # --- END OF READINESS BANNER PATCH ---

            quick_nav = self.build_category_quick_nav()
            if quick_nav is not None:
                self.main_canvas.controls.append(quick_nav)

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM workout_sessions WHERE meso_number = ? AND week = ? AND status = 'Pending'", (self.current_meso, self.current_week))
                pending_week_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT MAX(week) FROM workout_sessions WHERE meso_number = ?", (self.current_meso,))
                max_w_row = cursor.fetchone()
                
                cursor.execute("SELECT length_weeks FROM meso_configs WHERE meso_number = ?", (self.current_meso,))
                cfg_row = cursor.fetchone()
                cfg_len = cfg_row[0] if cfg_row else 999
                
                is_latest_week = False
                if max_w_row and max_w_row[0]:
                    cursor.execute("SELECT DISTINCT week FROM workout_sessions WHERE meso_number = ?", (self.current_meso,))
                    all_weeks = [r[0] for r in cursor.fetchall()]
                    sorted_weeks = sorted(all_weeks, key=lambda w: 999 if w == 'Deload' else int(w))
                    if sorted_weeks and self.current_week == sorted_weeks[-1]:
                        is_latest_week = True

            self.engine_button_container.controls.clear()
            
            if pending_week_count == 0 and is_latest_week:
                if self.current_week != "Deload":
                    if self.current_week.isdigit() and int(self.current_week) < cfg_len:
                        self.engine_button_container.controls.append(ft.FilledButton(content=ft.Text("Next Week"), on_click=lambda e: self.run_progression_engine(mode="Normal")))
                    self.engine_button_container.controls.append(ft.FilledButton(content=ft.Text("Deload Week", color="cyan100"), on_click=lambda e: self.run_progression_engine(mode="Deload")))
                
                self.engine_button_container.controls.append(ft.ElevatedButton(content=ft.Text("Architect New Meso"), color="orange300", on_click=self.open_generator_view))
                self.engine_button_container.controls.append(ft.ElevatedButton(content=ft.Text("Repeat Previous Meso"), color="blue300", on_click=self.open_clone_meso_dialog))

            if self.show_add_form:
                cancel_btn = ft.TextButton(
                    content=ft.Text("Cancel", color="red300"),
                    on_click=lambda e: setattr(self, 'show_add_form', False) or self.rebuild_entire_display()
                )
                add_btn = ft.ElevatedButton(
                    content=ft.Text("Add"),
                    on_click=self.save_wizard_addition
                )

                wizard_card = ft.Card(content=ft.Container(content=ft.Column([
                    ft.Text("Quick Add", size=13, weight="bold", color="orange200"),
                    ft.Row([self.wizard_exercise_dropdown]),
                    ft.Row([self.wizard_custom_input]),
                    ft.Row([self.wizard_weight_input, self.wizard_reps_input], spacing=10),
                    ft.Row([self.wizard_type_dropdown, self.wizard_cat_dropdown], spacing=10),
                    ft.Row([
                        ft.Container(),
                        ft.Row([cancel_btn, add_btn], spacing=5)
                    ], alignment="spaceBetween")
                ], spacing=8), padding=8))
                self.main_canvas.controls.append(wizard_card)

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, exercise, target_weight, target_reps, status, movement_type, category "
                    "FROM workout_sessions WHERE day_of_week = ? AND week = ? AND meso_number = ? "
                    "ORDER BY category, CASE WHEN status = 'Pending' THEN 0 ELSE 1 END, id",
                    (self.current_day, self.current_week, self.current_meso)
                )
                current_rows = cursor.fetchall()
                
            # --- START DATA BATCHING ENGINE ---
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Preserve list order for UI consistency
                session_ids = [row[0] for row in current_rows]
                exercises = list(dict.fromkeys([row[1] for row in current_rows]))
                
                pre_saved_sets = {sid: [] for sid in session_ids}
                pre_past_records = {ex: [] for ex in exercises}
                pre_notes = {ex: "" for ex in exercises}
                pre_snap_bw = {sid: None for sid in session_ids}
                readiness_logged = False
                j_score, r_score = 5, 15
                
                if session_ids or exercises:
                    cursor.execute("SELECT sleep, joints, drive FROM readiness_logs WHERE meso_number=? AND week=? AND day_of_week=?", (self.current_meso, self.current_week, self.current_day))
                    r_row = cursor.fetchone()
                    if r_row:
                        readiness_logged = True
                        j_score = r_row[1] if r_row[1] is not None else 5
                        r_score = sum(v if v is not None else 5 for v in r_row[:3])
                        
                    if session_ids:
                        placeholders = ",".join("?" for _ in session_ids)
                        cursor.execute(f"SELECT session_id, weight, reps, rpe, rest_seconds, target_weight, target_reps, normal_target_weight, normal_target_reps, completed_at, is_complete FROM workout_sets WHERE session_id IN ({placeholders}) ORDER BY set_number ASC", session_ids)
                        for sid, w, r, rpe, rest_secs, target_w, target_r, normal_w, normal_r, completed_at, is_complete in cursor.fetchall():
                            pre_saved_sets[sid].append((w, r, rpe, rest_secs, target_w, target_r, normal_w, normal_r, completed_at, is_complete))
                            
                        cursor.execute(f"SELECT id, bodyweight_snapshot FROM workout_sessions WHERE id IN ({placeholders})", session_ids)
                        for sid, snap in cursor.fetchall():
                            pre_snap_bw[sid] = snap
                            
                    if exercises:
                        placeholders = ",".join("?" for _ in exercises)
                        cursor.execute(f"SELECT name, setup_notes FROM exercise_dict WHERE name IN ({placeholders})", exercises)
                        for name, note in cursor.fetchall():
                            pre_notes[name] = note if note else ""
                            
                        # ONE single optimized query for all past exercise records
                        cursor.execute(f"""
                            SELECT ws.exercise, ws.id, s.set_number, s.weight, s.reps, s.rpe, s.target_weight, s.target_reps, s.normal_target_weight, s.normal_target_reps 
                            FROM workout_sets s 
                            JOIN workout_sessions ws ON s.session_id = ws.id 
                            WHERE ws.exercise IN ({placeholders}) 
                              AND ws.meso_number = ? 
                              AND ws.status = 'Completed'
                            ORDER BY ws.date DESC, ws.id DESC, s.set_number ASC
                        """, (*exercises, self.current_meso))
                        
                        for ex_name, sid, set_number, hw, hr, hrpe, target_w, target_r, normal_w, normal_r in cursor.fetchall():
                            pre_past_records[ex_name].append((sid, set_number, hw, hr, hrpe, target_w, target_r, normal_w, normal_r))
            # --- END DATA BATCHING ENGINE ---

            if not current_rows and pending_week_count > 0:
                self.main_canvas.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text("Rest Day / No Scheduled Exercises", color="grey400", size=13, weight="bold", text_align="center"),
                                ft.Text("Enjoy your recovery, or add an ad-hoc workout below.", color="white54", size=11, text_align="center"),
                                ft.TextButton("+ Add Ad-Hoc Exercise", icon="add", icon_color="cyan300", on_click=self.toggle_add_exercise_form)
                            ], horizontal_alignment="center", spacing=10),
                            padding=20
                        )
                    )
                )

            grouped = {}
            category_order = []
            for row in current_rows:
                db_id, exercise, tgt_w, tgt_r, status, mov_type, db_cat = row
                if db_cat not in grouped:
                    grouped[db_cat] = []
                    category_order.append(db_cat)
                grouped[db_cat].append((db_id, exercise, tgt_w, tgt_r, status, mov_type, db_cat))

            # --- NEW: KINETIC CATEGORY SORTING ---
            # Keeps incomplete categories in their original order,
            # but pushes fully completed categories to the bottom of the list.
            original_category_index = {cat: idx for idx, cat in enumerate(category_order)}

            def category_completion_sort_key(cat):
                rows = grouped.get(cat, [])
                pending_count = sum(1 for row in rows if row[4] == STATUS_PENDING)
                is_group_completed = pending_count == 0
                return (
                    1 if is_group_completed else 0,
                    original_category_index.get(cat, 999)
                )

            category_order = sorted(category_order, key=category_completion_sort_key)
            # --- END NEW SORTING ---

            previous_week_order = self.get_previous_week_exercise_order()

            for category_name in category_order:
                rows_in_cat = grouped[category_name]
                active_id = self.active_exercise_by_category.get(self.category_key(category_name))
                original_row_index = {row[0]: idx for idx, row in enumerate(rows_in_cat)}
                rows_in_cat = sorted(
                    rows_in_cat,
                    key=lambda row: (
                        1 if row[4] != STATUS_PENDING else 0,
                        0 if row[0] == active_id and row[4] == STATUS_PENDING else 1,
                        original_row_index.get(row[0], 999),
                    )
                )
                
                self.main_canvas.controls.append(ft.Container(height=4))
                self.main_canvas.controls.append(self.make_category_header(category_name, rows_in_cat))

                if self.is_category_collapsed(category_name):
                    continue

                for row in rows_in_cat:
                    db_id, exercise, tgt_w, tgt_r, status, mov_type, db_cat = row
                    
                    # Pack the batched data for this specific card
                    ctx = {
                        "readiness_logged": readiness_logged,
                        "j_score": j_score,
                        "r_score": r_score,
                        "saved_sets": pre_saved_sets.get(db_id, []),
                        "past_records": pre_past_records.get(exercise, []),
                        "saved_note": pre_notes.get(exercise, ""),
                        "snap_bw": pre_snap_bw.get(db_id, None),
                        "category": db_cat,
                        "previous_week_order": previous_week_order.get((db_cat, exercise)),
                    }
                    
                    card = ExerciseCard(db_id, exercise, tgt_w, tgt_r, status, mov_type, self, context=ctx)
                    card.key = self.exercise_anchor_key(db_id)
                    self.main_canvas.controls.append(card)

            if pending_week_count == 0 and len(self.engine_button_container.controls) > 0:
                self.main_canvas.controls.append(self.engine_button_container)

            self.main_canvas.controls.append(ft.Container(height=80))

            self.main_canvas.update()
            self.page.update()
            if self.pending_scroll_key:
                focus_key = self.pending_scroll_key
                self.pending_scroll_key = None
                self.scroll_to_workout_key(focus_key)

        except Exception:
            error_log = traceback.format_exc()
            self.main_canvas.controls.clear()
            self.main_canvas.controls.append(
                ft.Container(
                    content=ft.Text(f"CRASH REPORT:\n\n{error_log}", color="white", size=10, font_family="monospace"),
                    bgcolor="red900",
                    padding=10,
                    border_radius=6
                )
            )
            self.main_canvas.update()
            self.page.update()

# --- APP EXECUTION ---
def main(page: ft.Page):
    page.theme_mode = "dark"
    
    try: 
        app = WorkoutTrackerApp(page)
        page.update()
    except Exception:
        err = traceback.format_exc()
        page.clean()
        page.add(ft.Text(f"CRASH:\n\n{err}", color="red", size=10))
        page.update()

ft.app(target=main)
