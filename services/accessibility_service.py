"""Privacy-safe accessibility and responsive-layout acceptance helpers."""
from dataclasses import dataclass

MIN_TOUCH_TARGET_DP = 48
NARROW_WIDTH_DP = 360
TABLET_WIDTH_DP = 600
SHORT_HEIGHT_DP = 640

@dataclass(frozen=True)
class LayoutAcceptanceSnapshot:
    width: float
    height: float
    orientation: str
    width_class: str
    height_class: str
    safe_area_required: bool
    scrollable_dialogs_required: bool
    minimum_touch_target_dp: int = MIN_TOUCH_TARGET_DP


def classify_layout(width, height):
    """Classify device geometry without collecting device identity."""
    try: width = max(0.0, float(width or 0))
    except (TypeError, ValueError): width = 0.0
    try: height = max(0.0, float(height or 0))
    except (TypeError, ValueError): height = 0.0
    orientation = "landscape" if width > height and height > 0 else "portrait"
    width_class = "narrow" if width and width < NARROW_WIDTH_DP else ("tablet" if width >= TABLET_WIDTH_DP else "phone")
    height_class = "short" if height and height < SHORT_HEIGHT_DP else "regular"
    return LayoutAcceptanceSnapshot(width, height, orientation, width_class, height_class, True, True)


def acceptance_matrix():
    return (
        "System text scaling",
        "Portrait orientation",
        "Landscape orientation",
        "Narrow phone width",
        "Large phone and tablet width",
        "Standard, Focus, and Detailed display modes",
        "48 dp minimum primary touch targets",
        "Text labels or tooltips for icon actions",
        "Status communication not dependent on color alone",
        "Scrollable dialogs at constrained height",
        "Numeric keyboard and focus-loss behavior",
        "Safe-area and Android system-navigation clearance",
        "First Setup clean-install completion",
        "Backup, entitlement, and Diagnostics readability",
    )
