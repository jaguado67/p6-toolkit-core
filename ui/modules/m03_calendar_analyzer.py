from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, time
from pathlib import Path
import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from p6toolkit import (parse_xer_bytes, list_projects, build_snapshot,
                       compare_snapshots, inspect_network, audit_logic,
                       audit_constraints, summarize_snapshot, dcma_precheck,
                       activity_status)
from p6toolkit.xer import XERParseError
from ui.common import (STATUS_ORDER, STATUS_COLORS, csv_bytes, report_table, title, kicker,
                       get_status_table, network_local, comparison_ui)
from ui.spec import ModuleSpec

SPEC = ModuleSpec("03", "Calendar Analyzer", "Inventory", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Calendar Analyzer","Inventory and assignments; full interpretation of shifts and exceptions is pending")
    count=Counter(a.calendar_id or "Unassigned" for a in current.activities)
    calendar_lookup={c.get("clndr_id"):c for c in current.calendars}
    rows=[]
    for cid,n in count.most_common():
        cal=calendar_lookup.get(cid,{})
        rows.append({"Calendar ID":cid,"Calendar name":cal.get("clndr_name","Not found"),
                     "Activities":n,"Declared day hours":cal.get("day_hr_cnt") or None,
                     "Declared week hours":cal.get("week_hr_cnt") or None,
                     "Raw calendar data": "Present" if cal.get("clndr_data") else "Not present"})
    st.metric("Calendars in use",len(count))
    report_table(pd.DataFrame(rows),"p6_calendar_inventory.csv")
    st.caption("'day_hr_cnt' is exported metadata; it is not used as a universal hours-to-days factor.")
    st.warning("Reliable working-hour, shift and exception calculations require validating the CALENDAR.clndr_data parser.")
