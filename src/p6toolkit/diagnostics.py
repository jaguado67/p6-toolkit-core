"""Descriptive, auditable diagnostics for P6 XER snapshots.

These diagnostics DO NOT implement the complete DCMA 14-point method,
P6 CPM, or a certified temporal-validity calculation. Report denominators
are explicit, and suspect patterns are called candidates, not defects.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any
from .snapshot import ProjectSnapshot
from .network import inspect_network


@dataclass(frozen=True)
class LogicAudit:
    relationship_types: dict[str, int]
    positive_lags: int
    negative_lags: int
    missing_lags: int
    zero_lags: int
    duplicate_identical: tuple[tuple[str, str, str, float | None], ...]
    parallel_pair_candidates: tuple[tuple[str, str, int], ...]
    unusual_types: tuple[tuple[str, str, str], ...]
    relationship_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ConstraintAudit:
    activities_with_constraints: int
    constraint_instances: int
    by_type: dict[str, int]
    missing_dates: int
    detail: tuple[dict[str, Any], ...]


def audit_logic(snapshot: ProjectSnapshot) -> LogicAudit:
    ids = snapshot.by_id()
    types: Counter[str] = Counter()
    identical: Counter[tuple[str, str, str, float | None]] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    pos = neg = missing = zeros = 0
    rows: list[dict[str, Any]] = []
    unusual: list[tuple[str, str, str]] = []
    for rel in snapshot.relationships:
        pred = ids[rel.predecessor_id]
        succ = ids[rel.successor_id]
        key = (pred.code, succ.code, rel.kind, rel.lag_hours)
        identical[key] += 1
        pair_counts[(pred.code, succ.code)] += 1
        types[rel.kind] += 1
        if rel.lag_hours is None:
            missing += 1
        elif rel.lag_hours > 0:
            pos += 1
        elif rel.lag_hours < 0:
            neg += 1
        else:
            zeros += 1
        if rel.kind not in {"FS", "SS", "FF", "SF"}:
            unusual.append((pred.code, succ.code, rel.kind))
        rows.append({
            "Predecessor": pred.code,
            "Successor": succ.code,
            "Type": rel.kind,
            "Lag (h)": rel.lag_hours,
            "Predecessor name": pred.name,
            "Successor name": succ.name,
        })
    return LogicAudit(
        dict(types), pos, neg, missing, zeros,
        tuple(sorted((k for k, v in identical.items() if v > 1))),
        tuple(sorted((a, b, n) for (a, b), n in pair_counts.items() if n > 1)),
        tuple(sorted(unusual)), tuple(rows)
    )


def audit_constraints(snapshot: ProjectSnapshot) -> ConstraintAudit:
    types: Counter[str] = Counter()
    detail = []
    missing = 0
    activities = 0
    for activity in snapshot.activities:
        found = 0
        # P6 exports may hold primary/secondary constraint types and dates.
        for type_field, date_field in (("cstr_type", "cstr_date"),
                                       ("cstr_type2", "cstr_date2")):
            ctype = (activity.raw.get(type_field) or "").strip()
            if ctype and ctype.upper() not in {"CS_NONE", "NONE", "NO_CONSTRAINT"}:
                cdate = (activity.raw.get(date_field) or "").strip()
                types[ctype] += 1
                missing += not bool(cdate)
                detail.append({"Activity ID": activity.code,
                               "Activity Name": activity.name,
                               "Constraint": ctype,
                               "Constraint date": cdate or None,
                               "Field": type_field})
                found += 1
        if found:
            activities += 1
    return ConstraintAudit(activities, len(detail), dict(types), missing, tuple(detail))


def activity_status(status: str | None) -> str:
    return {
        "TK_COMPLETE": "Completed", "TK_ACTIVE": "In Progress",
        "TK_NOTSTART": "Not Started", "TK_NOTSTARTED": "Not Started",
    }.get((status or "").upper(), "Other")


def summarize_snapshot(snapshot: ProjectSnapshot) -> dict[str, Any]:
    statuses = Counter(activity_status(a.status) for a in snapshot.activities)
    active = [a for a in snapshot.activities if activity_status(a.status) != "Completed"]
    floats = [a.total_float_hours for a in active if a.total_float_hours is not None]
    network = inspect_network(snapshot)
    return {
        "activities": len(snapshot.activities),
        "relationships": len(snapshot.relationships),
        "calendar_count": len({a.calendar_id for a in snapshot.activities if a.calendar_id}),
        "status": dict(statuses),
        "remaining_with_float": len(floats),
        "remaining_without_float": len(active) - len(floats),
        "negative_float": sum(v < 0 for v in floats),
        "zero_float": sum(v == 0 for v in floats),
        "network_components": len(network.weak_components),
        "isolated": len(network.isolated_activities),
        "cyclic_sccs": len(network.cyclic_sccs),
        "open_start_candidates": len(network.start_activities),
        "open_finish_candidates": len(network.finish_activities),
    }


def dcma_precheck(snapshot: ProjectSnapshot, data_date=None) -> list[dict[str, Any]]:
    """Exploratory signals only; NEVER label as formal DCMA compliance.

    ``data_date`` must be a Data Date confirmed by the user; only then is point 09 evaluated.
    """
    logic = audit_logic(snapshot)
    constraints = audit_constraints(snapshot)
    summary = summarize_snapshot(snapshot)
    non_completed = summary["activities"] - summary["status"].get("Completed", 0)
    checks = [
        ("01", "Logic", "Open ends without an internal relationship (candidates, not defects)",
         summary["open_start_candidates"] + summary["open_finish_candidates"], "Exploratory"),
        ("02", "Leads", "Relationships with negative lag", logic.negative_lags, "Exploratory"),
        ("03", "Lags", "Relationships with positive lag", logic.positive_lags, "Exploratory"),
        ("04", "Relationship Types", "Non-FS relationships",
         sum(v for k, v in logic.relationship_types.items() if k != "FS"), "Exploratory"),
        ("05", "Hard Constraints", "Constraints of any type (no hard/soft classification)",
         constraints.constraint_instances, "Inventory"),
        ("06", "High Float", "Requires a threshold and validated calendars", None, "Not evaluated"),
        ("07", "Negative Float", "Incomplete activities with TF < 0 (P6 hours)",
         summary["negative_float"], "Exploratory"),
        ("08", "High Duration", "Requires a threshold and validated calendars", None, "Not evaluated"),
        _invalid_dates(snapshot, data_date),
        ("10", "Resources", "Requires a resource assignment audit", None, "Not evaluated"),
        ("11", "Missed Tasks", "Requires a comparable baseline and Data Date", None, "Not evaluated"),
        ("12", "Critical Path Test", "Requires a validated temporal engine", None, "Not evaluated"),
        ("13", "CPLI", "Requires a critical path and validated dates", None, "Not evaluated"),
        ("14", "BEI", "Requires a confirmed baseline and Data Date", None, "Not evaluated"),
    ]
    return [{"Point": i, "DCMA check": name, "Current signal": desc,
             "Observed": value, "Coverage": coverage} for i, name, desc, value, coverage in checks]


def _invalid_dates(snapshot: ProjectSnapshot, data_date) -> tuple:
    if data_date is None:
        return ("09", "Invalid Dates", "Requires a confirmed Data Date", None, "Not evaluated")
    from .progress import validate_progress
    report = validate_progress(snapshot, data_date)
    n = sum(c.findings for c in report.checks if c.check_id in ("P01", "P02", "P03", "P04"))
    return ("09", "Invalid Dates",
            f"Actuals after / forecasts before Data Date {data_date:%Y-%m-%d %H:%M} (Progress Validator P01-P04)",
            n, "Exploratory")
