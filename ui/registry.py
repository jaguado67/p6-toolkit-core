"""Ordered module registry. To add a tool: create ui/modules/mNN_name.py with SPEC and render(ctx),
then list it here. Navigation order = list order; the scope table is sorted by SPEC.id."""
from __future__ import annotations
from importlib import import_module

NAV_ORDER = [
    "m10_schedule_dashboard",
    "m01_xer_explorer",
    "m02_xer_comparator",
    "m03_calendar_analyzer",
    "m04_network_integrity",
    "m05_logic_analyzer",
    "m06_schedule_health",
    "m07_critical_path",
    "m08_float_erosion",
    "m09_update_to_update",
    "m11_dcma14",
    "m12_constraints",
    "m14_progress_validator",
    "m13_relationship_converter",
]


def load_modules():
    return [import_module(f"ui.modules.{name}") for name in NAV_ORDER]
