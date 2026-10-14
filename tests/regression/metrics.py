"""Metrics recorded for real-file regression. Kept small and readable so a planner can check each
number against P6 by hand before marking a golden file as validated."""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from pathlib import Path
from p6toolkit import (parse_xer_file, build_snapshot, list_projects, inspect_network, audit_logic,
                       audit_constraints, summarize_snapshot, convert_workbook)
from p6toolkit.progress import validate_progress


def xer_metrics(path: Path, data_date: str | None = None) -> dict:
    doc = parse_xer_file(path)
    out = {"kind": "xer", "tables": {name: len(t.rows) for name, t in sorted(doc.tables.items())},
           "encoding": doc.encoding, "projects": {}}
    for pid, code, _ in list_projects(doc):
        snap = build_snapshot(doc, pid)
        net, logic, cons, summ = inspect_network(snap), audit_logic(snap), audit_constraints(snap), summarize_snapshot(snap)
        item = {
            "activities": len(snap.activities),
            "relationships": len(snap.relationships),
            "external_links": len(snap.external_links),
            "status": dict(sorted(summ["status"].items())),
            "relationship_types": dict(sorted(logic.relationship_types.items())),
            "positive_lags": logic.positive_lags, "negative_lags": logic.negative_lags,
            "components": len(net.weak_components), "isolated": len(net.isolated_activities),
            "no_predecessor": len(net.start_activities), "no_successor": len(net.finish_activities),
            "cyclic_sccs": len(net.cyclic_sccs),
            "constraints": dict(sorted(cons.by_type.items())),
            "negative_float": summ["negative_float"],
        }
        if data_date:
            rep = validate_progress(snap, datetime.fromisoformat(data_date))
            item["progress"] = {c.check_id: c.findings for c in rep.checks}
        out["projects"][code or pid] = item
    return out


def layout_metrics(path: Path) -> dict:
    r = convert_workbook(path.read_bytes())
    return {"kind": "layout_xlsx", "activities": r.activity_count, "relationships": r.relationship_count,
            "dropped_rows": r.dropped_rows, "relationship_types": dict(sorted(r.relationship_types.items())),
            "lagged": r.lagged_relationships, "activity_types": dict(sorted(r.activity_types.items())),
            "issues": dict(sorted(Counter(i.check for i in r.issues).items()))}


def metrics_for(path: Path, data_date: str | None = None) -> dict:
    return xer_metrics(path, data_date) if path.suffix.lower() == ".xer" else layout_metrics(path)
