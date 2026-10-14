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

SPEC = ModuleSpec("09", "Update-to-Update Analyzer", "Partial comparison", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Update-to-Update Analyzer","Variation between two snapshots; multi-cycle series under development")
    before,diff=comparison_ui(ctx, update=True)
    st.caption(f"Previous: {before.filename} → Current: {current.filename}")
    pairs=[("Activities added",len(diff.added)),("Activities removed",len(diff.removed)),
           ("Activity field changes",len(diff.field_changes)),("Relationships added",len(diff.relationships_added)),
           ("Relationships removed",len(diff.relationships_removed))]
    c=st.columns(5)
    for col,(name,val) in zip(c,pairs):col.metric(name,val)
    changes=pd.DataFrame([asdict(x) for x in diff.field_changes])
    if not changes.empty:
        bucket=changes.groupby("field_name",as_index=False).size().sort_values("size",ascending=False).head(20)
        fig=px.bar(bucket,x="size",y="field_name",orientation="h",color_discrete_sequence=["#477EA8"])
        fig.update_layout(height=420,yaxis=dict(autorange="reversed"),margin=dict(l=0,r=10,t=10,b=10))
        st.plotly_chart(fig,use_container_width=True)
    report_table(changes,"update_to_update.csv",height=450)
    st.caption("Comparison is by Activity ID; dates and hours are shown exactly as in each XER.")
