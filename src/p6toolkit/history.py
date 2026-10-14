"""Historical raw P6 Float tracking: hours, without asserting cause of erosion."""
from __future__ import annotations
from dataclasses import dataclass
from .snapshot import ProjectSnapshot


@dataclass(frozen=True)
class FloatObservation:
    activity_code: str
    filename: str
    data_date: str | None
    total_float_hours: float | None
    delta_hours: float | None


def check_version_order(data_dates: list) -> list[str]:
    """Problems that make an update sequence unreliable: missing, duplicated or decreasing Data Dates."""
    problems = []
    if any(d is None for d in data_dates):
        problems.append("Data Date not confirmed for every selected version")
        return problems
    if len(set(data_dates)) != len(data_dates):
        problems.append("Two or more versions share the same Data Date")
    if any(b < a for a, b in zip(data_dates, data_dates[1:])):
        problems.append("Versions are not in increasing Data Date order")
    return problems


def build_float_history(snapshots: list[ProjectSnapshot], task_code: str) -> tuple[FloatObservation, ...]:
    if not snapshots:
        return ()
    project_codes = {s.project_code for s in snapshots}
    if len(project_codes) != 1:
        raise ValueError("The updates belong to different projects")
    # Caller decides temporal order; missing or duplicated Data Dates must be reviewed.
    result: list[FloatObservation] = []
    previous: float | None = None
    for snap in snapshots:
        activity = snap.by_code().get(task_code)
        val = activity.total_float_hours if activity else None
        delta = val - previous if val is not None and previous is not None else None
        result.append(FloatObservation(task_code, snap.filename, snap.data_date, val, delta))
        previous = val
    return tuple(result)
