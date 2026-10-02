# IronCycle 1.99.11 Android accessibility and layout acceptance

Record device model privately, Android version, viewport/orientation, system font size, display size, and pass/fail. Diagnostics itself records only viewport class.

## Device matrix
Run at minimum on a narrow phone-sized viewport and one large phone/tablet-sized viewport. Test portrait and landscape when rotation is supported.

1. At default text size, open Workout, Weeks and days, Quick Actions, Profile Settings, Diagnostics, Entitlement Acceptance, Backup Manager, and Accessibility Acceptance. Confirm no clipped critical action and all dialogs scroll.
2. Set Android font size to the largest practical setting and repeat. Confirm text wraps, primary actions remain reachable, and no horizontal overflow obscures data entry.
3. Test Standard, Focus, and Detailed modes. Confirm group labels, active set, Complete, weight, reps, and RPE remain understandable.
4. Check primary buttons for an approximately 48 dp usable target. Verify small icon actions have a text label, tooltip, or adjacent label.
5. Verify success, warning, error, completed, skipped, limited-mode, Billing, and OneDrive states communicate with words or symbols, not color alone.
6. Open numeric weight/reps/RPE fields. Confirm numeric keyboard, submit/blur handling, target restoration after deleting reps, and visibility above the keyboard.
7. Rotate with a field focused and with a dialog open. Confirm no crash, frozen control, duplicate dialog, or lost durable draft.
8. Verify SafeArea clearance from status and navigation bars in portrait and landscape.
9. On a clean install, complete First Setup using enlarged text; save equipment and starter plan; confirm the workout renders.
10. On an upgrade install, confirm existing-user onboarding remains preserved.
11. Verify Backup Manager, entitlement, Diagnostics, and recovery checklist remain readable and scrollable.
12. Recheck frozen workout behavior, normal A1-first superset flow, Billing, OneDrive, backup restore, force-stop/relaunch, and integrity `ok`.
