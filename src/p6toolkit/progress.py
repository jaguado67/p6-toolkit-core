"""M14 — Progress Validator.

Checks the status update of a snapshot against a Data Date confirmed by the user.
Only exported values are compared (actual dates, status, remaining duration,
early dates); no CPM recalculation and no calendar arithmetic are performed.

Out-of-sequence progress is evaluated per relationship type and ignores lags
(a lag can only make a violation *larger*, never remove one, for lag >= 0;
negative lags are reported separately because they can legitimately allow
overlap). Each check reports its eligible population so counts are auditable.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from .snapshot import ProjectSnapshot, Activity
from .diagnostics import activity_status

_DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def parse_xer_date(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class ProgressFinding:
    check_id: str
    check: str
    activity_id: str
    activity_name: str
    detail: str


@dataclass(frozen=True)
class ProgressCheck:
    check_id: str
    check: str
    population: str
    eligible: int
    findings: int
    dcma_reference: str | None


@dataclass(frozen=True)
class ProgressReport:
    data_date: datetime
    checks: tuple[ProgressCheck, ...]
    findings: tuple[ProgressFinding, ...]
    unparsed_dates: int


CHECKS = {
    "P01": ("Actual start after Data Date", "Activities with actual start", "DCMA 09a"),
    "P02": ("Actual finish after Data Date", "Activities with actual finish", "DCMA 09a"),
    "P03": ("Forecast start before Data Date (not started)", "Not Started with early start", "DCMA 09b"),
    "P04": ("Forecast finish before Data Date (not completed)", "Incomplete with early finish", "DCMA 09b"),
    "P05": ("Status inconsistent with actual dates", "All activities", None),
    "P06": ("Actual finish earlier than actual start", "Activities with both actual dates", None),
    "P07": ("Completed with remaining duration > 0", "Completed activities", None),
    "P08": ("Out-of-sequence progress", "Relationships with a started/finished successor", None),
    "P09": ("Negative lag on out-of-sequence candidate (review)", "Relationships with lag < 0", None),
    "P10": ("Same-day sequence overlap (depends on time of day, review)",
            "Relationships with a started/finished successor", None),
}


def _dates(a: Activity) -> dict[str, datetime | None]:
    raw = a.raw
    return {
        "as": parse_xer_date(raw.get("act_start_date")),
        "af": parse_xer_date(raw.get("act_end_date")),
        "es": parse_xer_date(raw.get("early_start_date") or raw.get("restart_date")),
        "ef": parse_xer_date(raw.get("early_end_date") or raw.get("reend_date")),
    }


def validate_progress(snapshot: ProjectSnapshot, data_date: datetime) -> ProgressReport:
    findings: list[ProgressFinding] = []
    eligible = {k: 0 for k in CHECKS}
    unparsed = 0
    info: dict[str, tuple[Activity, str, dict]] = {}

    def add(cid: str, a: Activity, detail: str) -> None:
        findings.append(ProgressFinding(cid, CHECKS[cid][0], a.code, a.name, detail))

    for a in snapshot.activities:
        st = activity_status(a.status)
        d = _dates(a)
        for key, field in (("as", "act_start_date"), ("af", "act_end_date")):
            if a.raw.get(field) and d[key] is None:
                unparsed += 1
        # Event dates for sequencing: a milestone's start and finish are one event.
        ev = dict(d)
        if (a.raw.get("task_type") or "").upper() in {"TT_MILE", "TT_FINMILE"}:
            ev["as"] = ev["af"] = d["as"] or d["af"]
        info[a.task_id] = (a, st, ev)

        if d["as"]:
            eligible["P01"] += 1
            if d["as"] > data_date:
                add("P01", a, f"Actual start {d['as']:%Y-%m-%d %H:%M} > DD")
        if d["af"]:
            eligible["P02"] += 1
            if d["af"] > data_date:
                add("P02", a, f"Actual finish {d['af']:%Y-%m-%d %H:%M} > DD")
        if st == "Not Started" and d["es"]:
            eligible["P03"] += 1
            if d["es"] < data_date:
                add("P03", a, f"Early start {d['es']:%Y-%m-%d %H:%M} < DD")
        if st != "Completed" and d["ef"]:
            eligible["P04"] += 1
            if d["ef"] < data_date:
                add("P04", a, f"Early finish {d['ef']:%Y-%m-%d %H:%M} < DD")

        eligible["P05"] += 1
        task_type = (a.raw.get("task_type") or "").upper()
        if st == "Completed":
            if task_type == "TT_MILE":
                bad = d["as"] is None
            elif task_type == "TT_FINMILE":
                bad = d["af"] is None
            else:
                bad = d["as"] is None or d["af"] is None
            if bad:
                add("P05", a, "Completed without the required actual date(s)")
        elif st == "In Progress" and (d["as"] is None or d["af"] is not None):
            add("P05", a, "In Progress needs actual start and no actual finish")
        elif st == "Not Started" and (d["as"] is not None or d["af"] is not None):
            add("P05", a, "Not Started with actual dates")

        if d["as"] and d["af"]:
            eligible["P06"] += 1
            if d["af"] < d["as"]:
                add("P06", a, f"AF {d['af']:%Y-%m-%d} < AS {d['as']:%Y-%m-%d}")
        if st == "Completed":
            eligible["P07"] += 1
            if a.remaining_hours and a.remaining_hours > 0:
                add("P07", a, f"Remaining {a.remaining_hours:g} h")

    # Out-of-sequence: successor progressed while predecessor has not reached the
    # event the relationship ties it to.
    for rel in snapshot.relationships:
        if rel.predecessor_id not in info or rel.successor_id not in info:
            continue
        p, _, pd_ = info[rel.predecessor_id]
        s, _, sd = info[rel.successor_id]
        succ_event = sd["as"] if rel.kind in ("FS", "SS") else sd["af"]
        if succ_event is None:
            continue
        eligible["P08"] += 1
        eligible["P10"] += 1
        pred_event = pd_["af"] if rel.kind in ("FS", "FF") else pd_["as"]
        label = {"FS": ("finished", "started"), "SS": ("started", "started"),
                 "FF": ("finished", "finished"), "SF": ("started", "finished")}[rel.kind]
        lag = rel.lag_hours or 0
        if lag < 0:
            eligible["P09"] += 1
        if pred_event is None:
            cid = "P09" if lag < 0 else "P08"
            findings.append(ProgressFinding(cid, CHECKS[cid][0], s.code, s.name,
                f"{p.code} -> {s.code} {rel.kind}: successor {label[1]}, predecessor not {label[0]}"))
        elif succ_event < pred_event and lag >= 0:
            # Same calendar day: only the time of day decides; exports often drop it.
            cid = "P10" if succ_event.date() == pred_event.date() else "P08"
            findings.append(ProgressFinding(cid, CHECKS[cid][0], s.code, s.name,
                f"{p.code} -> {s.code} {rel.kind}: successor {label[1]} {succ_event:%Y-%m-%d} "
                f"before predecessor {label[0]} {pred_event:%Y-%m-%d}"))

    counts: dict[str, int] = {k: 0 for k in CHECKS}
    for f in findings:
        counts[f.check_id] += 1
    checks = tuple(ProgressCheck(k, v[0], v[1], eligible[k], counts[k], v[2]) for k, v in CHECKS.items())
    return ProgressReport(data_date, checks, tuple(findings), unparsed)


def data_date_candidates(snapshot: ProjectSnapshot) -> list[tuple[str, datetime]]:
    """Exported values that may hold the Data Date. None of them is authoritative.

    Oracle's XER data map labels ``last_recalc_date`` only as "Last Recalc Date"; the open-source
    xerparser library uses max(last_recalc_date, plan_start_date). The user confirms the value.
    """
    out = []
    for field_name in ("last_recalc_date", "next_data_date", "plan_start_date"):
        value = parse_xer_date(snapshot.project.get(field_name)) if snapshot.project else None
        if value is None and field_name == "last_recalc_date":
            value = parse_xer_date(snapshot.data_date)
        if value is not None:
            out.append((f"PROJECT.{field_name}", value))
    return out


def suggested_data_date(snapshot: ProjectSnapshot) -> datetime | None:
    """Candidate only; the UI must ask the user to confirm it.

    Uses last_recalc_date, but never earlier than plan_start_date (a Data Date cannot precede
    the project start), which reproduces the xerparser convention.
    """
    found = dict(data_date_candidates(snapshot))
    recalc = found.get("PROJECT.last_recalc_date")
    start = found.get("PROJECT.plan_start_date")
    if recalc and start:
        return max(recalc, start)
    return recalc or start
