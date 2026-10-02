# IronCycle 1.99.12

## Portrait layout and display-mode access

- Reserves a fixed 44 dp exercise-actions lane so long exercise names cannot cover the `...` menu.
- Limits titles to two lines with ellipsis and keeps the full title discoverable through a tooltip.
- Moves prior-order and status badges to a separate wrapping row.
- Restores a visible `View: Standard/Focus/Detailed` control on the main Workout screen.
- Centralizes Standard, Focus, and Detailed mode mapping and persists the same settings used by prior releases.
- Replaces the separate Profile Settings focus switch/density dropdown with one synchronized Display mode selector.
- Makes Profile Settings independently scrollable above its fixed action footer, uses viewport-aware height, responsive profile fields, and bottom clearance.
- Leaves workout logic, entitlement, backup/recovery, Billing, OneDrive, current superset ordering, and schema 20 unchanged.
