"""Per-run analysis context shared by XER-based modules."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import pandas as pd
from ui.common import analytics, get_status_table


@dataclass
class Context:
    snaps: dict
    docs: dict
    ingestion: list
    current_key: str
    current: Any = None
    summary: dict = field(default_factory=dict)
    graph: Any = None
    logic: Any = None
    constraints: Any = None
    wbs_lookup: dict = field(default_factory=dict)
    df_activities: pd.DataFrame | None = None
    status: dict = field(default_factory=dict)
    data_date: Any = None                                   # confirmed Data Date of the current snapshot
    data_dates: dict = field(default_factory=dict)          # snapshot key -> confirmed Data Date


def build_context(snaps, docs, ingestion, current_key, data_dates=None) -> Context:
    current = snaps[current_key]
    summary,graph,logic,constraints=analytics(current)
    name_to_code={a.task_id:a.code for a in current.activities}
    # Reconstruct human-readable WBS paths using the actual PROJWBS hierarchy.
    source_doc=next(doc for (_,sha),doc in docs.items() if sha==current.sha256)
    wbs_rows={r.get("wbs_id"):r for r in source_doc.rows("PROJWBS") if r.get("proj_id")==current.project_id}
    def wbs_path(wbs_id):
        if not wbs_id or wbs_id not in wbs_rows:return wbs_id or "—"
        seen=set();parts=[];node=wbs_id
        while node and node in wbs_rows and node not in seen and len(parts)<20:
            seen.add(node);row=wbs_rows[node]
            parts.append(row.get("wbs_name") or row.get("wbs_short_name") or node)
            node=row.get("parent_wbs_id")
        return " / ".join(reversed(parts))
    wbs_lookup={wid:wbs_path(wid) for wid in wbs_rows}
    df_activities=get_status_table(current,wbs_lookup)
    status=summary["status"]
    data_dates = dict(data_dates or {})
    return Context(snaps, docs, ingestion, current_key, current, summary, graph, logic, constraints,
                   wbs_lookup, df_activities, status, data_dates.get(current_key), data_dates)
