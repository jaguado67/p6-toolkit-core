"""Canonical project snapshot derived from a full XER document.

Raw rows remain available in XERDocument. Snapshot stores no interpretations
of P6-derived floats, driving paths or calendars beyond extracted attributes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping
from .xer import XERDocument


@dataclass(frozen=True)
class Activity:
    task_id: str
    project_id: str
    code: str
    name: str
    wbs_id: str | None
    calendar_id: str | None
    status: str | None
    total_float_hours: float | None
    remaining_hours: float | None
    original_hours: float | None
    raw: Mapping[str, str] = field(repr=False)


@dataclass(frozen=True)
class Relationship:
    relationship_id: str
    predecessor_id: str
    successor_id: str
    kind: str
    lag_hours: float | None
    raw: Mapping[str, str] = field(repr=False)


@dataclass(frozen=True)
class ProjectSnapshot:
    project_id: str
    project_code: str
    project_name: str
    data_date: str | None
    date_reference_source: str | None
    filename: str
    sha256: str
    activities: tuple[Activity, ...]
    relationships: tuple[Relationship, ...]  # Only links internal to this project
    external_links: tuple[Mapping[str, str], ...]
    calendars: tuple[Mapping[str, str], ...]
    warnings: tuple[str, ...]
    project: Mapping[str, str] = field(default_factory=dict, repr=False)  # raw PROJECT row

    def by_id(self) -> dict[str, Activity]:
        return {a.task_id: a for a in self.activities}

    def by_code(self) -> dict[str, Activity]:
        return {a.code: a for a in self.activities}


def _number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    import math
    return result if math.isfinite(result) else None


def list_projects(document: XERDocument) -> list[tuple[str, str, str]]:
    return [(r.get("proj_id", ""), r.get("proj_short_name", ""),
             r.get("proj_name", "")) for r in document.rows("PROJECT")]


def build_snapshot(document: XERDocument, project_id: str | None = None) -> ProjectSnapshot:
    projects = list(document.rows("PROJECT"))
    if not projects:
        raise ValueError("The XER has no PROJECT table with projects")
    if project_id is None:
        if len(projects) != 1:
            raise ValueError("The XER contains several projects: specify project_id")
        project = projects[0]
    else:
        found = [p for p in projects if p.get("proj_id") == str(project_id)]
        if len(found) != 1:
            raise ValueError(f"Unknown or ambiguous project: {project_id}")
        project = found[0]
    pid = project.get("proj_id", "")
    warnings: list[str] = list(document.warnings)
    activity_rows = [r for r in document.rows("TASK") if r.get("proj_id") == pid]
    if not activity_rows:
        warnings.append("The project has no TASK activities")
    activities: list[Activity] = []
    for r in activity_rows:
        activities.append(Activity(
            task_id=r.get("task_id", ""), project_id=pid,
            code=r.get("task_code", ""), name=r.get("task_name", ""),
            wbs_id=r.get("wbs_id") or None, calendar_id=r.get("clndr_id") or None,
            status=r.get("status_code") or None,
            total_float_hours=_number(r.get("total_float_hr_cnt")),
            remaining_hours=_number(r.get("remain_drtn_hr_cnt") or r.get("remain_dur_hr_cnt")),
            original_hours=_number(r.get("target_drtn_hr_cnt") or r.get("orig_dur_hr_cnt")),
            raw=r
        ))
    ids = [a.task_id for a in activities]
    codes = [a.code for a in activities]
    if len(ids) != len(set(ids)) or "" in ids:
        raise ValueError("Empty or duplicated TASK.task_id in the project")
    if len(codes) != len(set(codes)) or "" in codes:
        raise ValueError("Empty or duplicated TASK.task_code: cannot compare")
    own_ids = set(ids)
    all_ids = {r.get("task_id", "") for r in document.rows("TASK")}
    relationships: list[Relationship] = []
    external: list[Mapping[str, str]] = []
    for r in document.rows("TASKPRED"):
        successor = r.get("task_id", "")
        predecessor = r.get("pred_task_id", "")
        if successor not in own_ids and predecessor not in own_ids:
            continue
        if successor not in own_ids or predecessor not in own_ids:
            external.append(r)
            if predecessor not in all_ids:
                warnings.append(f"Predecessor {predecessor} not exported; relationship to {successor}")
            if successor not in all_ids:
                warnings.append(f"Successor {successor} not exported; relationship from {predecessor}")
            continue
        kind = (r.get("pred_type", "").upper().removeprefix("PR_"))
        if kind not in {"FS", "SS", "FF", "SF"}:
            warnings.append(f"Unknown relationship type: {kind} ({predecessor}->{successor})")
        relationships.append(Relationship(
            r.get("task_pred_id", ""), predecessor, successor, kind,
            _number(r.get("lag_hr_cnt")), r
        ))
    used_calendars = {a.calendar_id for a in activities if a.calendar_id}
    calendars = tuple(r for r in document.rows("CALENDAR") if r.get("clndr_id") in used_calendars)
    available = {c.get("clndr_id") for c in calendars}
    for missing in sorted(used_calendars - available):
        warnings.append(f"Referenced calendar not exported: {missing}")
    data_date = project.get("last_recalc_date") or None
    if data_date is None:
        warnings.append("PROJECT.last_recalc_date not found; Data Date not verified")
    else:
        warnings.append("PROJECT.last_recalc_date is the Last Recalc Date; confirm the Data Date against P6")
    return ProjectSnapshot(
        project_id=pid,
        project_code=project.get("proj_short_name", "") or pid,
        project_name=project.get("proj_name", "") or project.get("proj_short_name", "") or pid,
        data_date=data_date, date_reference_source=("PROJECT.last_recalc_date" if data_date else None),
        filename=document.filename, sha256=document.sha256,
        activities=tuple(activities), relationships=tuple(relationships),
        external_links=tuple(external), calendars=calendars, warnings=tuple(warnings),
        project=project
    )
