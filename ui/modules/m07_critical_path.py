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

SPEC = ModuleSpec("07", "Critical Path Analyzer", "P6 data exploration", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Critical Path Analyzer","Exploration of Float exported by P6; not a Critical Path reconstruction")
    active=df_activities[df_activities["Status"]!="Completed"].copy()
    fl=active[active["Total Float (h)"].notna()].copy()
    c1,c2,c3=st.columns(3)
    c1.metric("Incomplete with TF",len(fl));c2.metric("Negative TF",int((fl["Total Float (h)"]<0).sum()))
    c3.metric("No TF available",len(active)-len(fl))
    if not fl.empty:
        fig=px.histogram(fl,x="Total Float (h)",nbins=45,labels={"Total Float (h)":"P6 Total Float (hours)"})
        fig.update_traces(marker_color="#477EA8")
        fig.update_layout(height=320,margin=dict(t=20,b=30,l=0,r=10))
        st.plotly_chart(fig,use_container_width=True)
        st.markdown("**Activities with lowest exported Total Float**")
        report_table(fl.sort_values("Total Float (h)").head(150),"criticality_low_float.csv",height=390)
    st.warning("Negative Total Float alone does not define the Longest Path. Without recreating scheduling options, calendars and constraints, this is NOT claimed to be the P6 critical path.")
