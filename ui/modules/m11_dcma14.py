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

SPEC = ModuleSpec("11", "DCMA-14 Checker", "Non-certified pre-check", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("DCMA-14 Checker","Coverage of the 14 checks; preliminary signals kept separate from formal compliance")
    checks=pd.DataFrame(dcma_precheck(current, ctx.data_date))
    if ctx.data_date is None:
        st.caption("Point 09 (Invalid Dates) is evaluated once the Data Date is confirmed in the sidebar.")
    st.metric("Checks with exploratory signals",int((checks["Coverage"]!="Not evaluated").sum()))
    st.warning("This screen does NOT issue a DCMA-14 certification or apply contractual thresholds. Inventories and exploratory signals are not pass/fail results.")
    report_table(checks,"dcma14_precheck.csv",height=575)
