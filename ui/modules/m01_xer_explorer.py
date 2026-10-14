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

SPEC = ModuleSpec("01", "XER Explorer", "Partially operational", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("XER Explorer","Search, filters and traceability of attributes and records")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Activities",summary["activities"]);c2.metric("Relationships",summary["relationships"])
    c3.metric("Used calendars",summary["calendar_count"]);c4.metric("XER documents",len(docs))
    search=st.text_input("Search Activity ID or name",placeholder="DH1100, Commissioning, M1010...")
    filters=st.columns(3)
    st_values=sorted(df_activities["Status"].unique())
    status_sel=filters[0].multiselect("Status",st_values,default=st_values)
    wbs_values=sorted(df_activities["WBS"].unique())
    wbs_sel=filters[1].multiselect("WBS",wbs_values,default=[],placeholder="All")
    cal_values=sorted(df_activities["Calendar"].unique())
    cal_sel=filters[2].multiselect("Calendar",cal_values,default=[],placeholder="All")
    view=df_activities[df_activities["Status"].isin(status_sel)]
    if search: view=view[view["Activity ID"].str.contains(search,case=False,regex=False)|view["Activity Name"].str.contains(search,case=False,regex=False)]
    if wbs_sel:view=view[view["WBS"].isin(wbs_sel)]
    if cal_sel:view=view[view["Calendar"].isin(cal_sel)]
    st.caption(f"Showing {len(view):,} of {len(df_activities):,} activities")
    report_table(view,"p6_explorer.csv",height=570)
    with st.expander("XER details and warnings"):
        st.dataframe(pd.DataFrame(ingestion),use_container_width=True,hide_index=True)
        for msg in current.warnings: st.caption("• "+msg)
        st.write("External / non-exported relationships:",len(current.external_links))
