"""Read-only, field-level differences with conservative identity matching."""
from __future__ import annotations
from dataclasses import dataclass
from .snapshot import ProjectSnapshot, Activity


@dataclass(frozen=True)
class FieldChange:
    activity_code: str
    field_name: str
    before: object
    after: object


@dataclass(frozen=True)
class Comparison:
    baseline_file: str
    current_file: str
    added: tuple[str, ...]
    removed: tuple[str, ...]
    field_changes: tuple[FieldChange, ...]
    relationships_added: tuple[tuple, ...]
    relationships_removed: tuple[tuple, ...]
    warnings: tuple[str, ...]


def _relationship_key(snapshot: ProjectSnapshot) -> set[tuple]:
    activity_ids = snapshot.by_id()
    return {
        (activity_ids[r.predecessor_id].code, activity_ids[r.successor_id].code,
         r.kind, r.lag_hours)
        for r in snapshot.relationships
    }


def compare_snapshots(before: ProjectSnapshot, after: ProjectSnapshot,
                      confirm_same_project: bool = False) -> Comparison:
    different_projects = before.project_code != after.project_code
    if different_projects and not confirm_same_project:
        raise ValueError("Different project codes; confirm explicitly that they belong to the same project")
    first = before.by_code()
    second = after.by_code()
    common = first.keys() & second.keys()
    changes: list[FieldChange] = []
    attrs = ("name", "wbs_id", "calendar_id", "status", "total_float_hours",
             "remaining_hours", "original_hours")
    # Compare original XER date fields as source data; no attempt to re-schedule.
    date_fields = ("target_start_date", "target_end_date", "early_start_date", "early_end_date",
                   "late_start_date", "late_end_date", "act_start_date", "act_end_date",
                   "restart_date", "reend_date", "cstr_type", "cstr_date")
    for code in sorted(common):
        a, b = first[code], second[code]
        for name in attrs:
            old, new = getattr(a, name), getattr(b, name)
            if old != new:
                changes.append(FieldChange(code, name, old, new))
        for name in date_fields:
            old, new = a.raw.get(name), b.raw.get(name)
            if old != new:
                changes.append(FieldChange(code, name, old, new))
    left, right = _relationship_key(before), _relationship_key(after)
    warnings: list[str] = []
    if different_projects:
        warnings.append("Different project codes: match confirmed manually; validate activity identity")
    if set(first) ^ set(second):
        warnings.append("An activity whose Activity ID changed may appear as both added and removed")
    if before.external_links or after.external_links:
        warnings.append("External relationships exist and are not part of the internal comparison")
    return Comparison(before.filename, after.filename,
                      tuple(sorted(set(second) - set(first))),
                      tuple(sorted(set(first) - set(second))),
                      tuple(changes), tuple(sorted(right - left)), tuple(sorted(left - right)),
                      tuple(warnings))
