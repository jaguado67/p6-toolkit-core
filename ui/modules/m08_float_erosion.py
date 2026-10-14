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
from p6toolkit.history import check_version_order

SPEC = ModuleSpec("08", "Float Erosion Tracker", "Conditional history", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Float Erosion Tracker","History of exported Total Float, in hours, in a user-confirmed order")
    versions=list(snaps)
    if len(versions)<2:
        st.info("Only one version is loaded. At least two updates are needed to study Float erosion.")
        st.markdown("**Current Float distribution of incomplete activities:**")
        fl=df_activities[(df_activities["Status"]!="Completed") & df_activities["Total Float (h)"].notna()]
        if not fl.empty:
            fig=px.histogram(fl,x="Total Float (h)",nbins=40)
            fig.update_layout(height=340)
            st.plotly_chart(fig,use_container_width=True)
    else:
        dated=all(k in ctx.data_dates for k in versions)
        default=sorted(versions,key=lambda k:ctx.data_dates[k]) if dated else versions
        if dated:
            st.caption("Default order follows the Data Dates confirmed in the sidebar.")
        order=st.multiselect("Select the versions in order BL → current UP",versions,default=default,
                             help="The Toolkit never orders by last_recalc_date as a substitute for the Data Date.")
        problems=check_version_order([ctx.data_dates.get(k) for k in order])
        for p in problems:
            st.warning(p)
        confirmed=st.checkbox("I confirm the time order and that all XER files belong to the same project")
        task=st.selectbox("Activity ID",sorted(a.code for a in current.activities))
        if confirmed and len(order)>=2:
            rows=[];prior=None
            for position,k in enumerate(order):
                snap=snaps[k];a=snap.by_code().get(task)
                val=a.total_float_hours if a else None
                rows.append({"Update":position+1,"Version":k,"Data Date":ctx.data_dates.get(k),"Total Float (h)":val,
                             "Delta (h)":val-prior if val is not None and prior is not None else None})
                prior=val
            h=pd.DataFrame(rows)
            report_table(h,"float_history.csv",height=240)
            points=h.dropna(subset=["Total Float (h)"])
            if len(points)>=2:
                fig=px.line(points,x="Version",y="Total Float (h)",markers=True)
                fig.update_layout(height=370,xaxis_tickangle=-25)
                st.plotly_chart(fig,use_container_width=True)
            else:st.info("This activity does not have enough Total Float values to plot a trend.")
            st.caption("Observed changes may come from logic, calendars, constraints or progress. No cause is inferred automatically.")
        else:st.info("Select at least two versions and confirm their order and identity.")
