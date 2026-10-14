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

SPEC = ModuleSpec("12", "Constraints Analyzer", "Inventory", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Constraints Analyzer","Explicit constraints taken from TASK, without inferring their effect on the network yet")
    c1,c2,c3=st.columns(3)
    c1.metric("Activities with constraints",constraints.activities_with_constraints)
    c2.metric("Constraint instances",constraints.constraint_instances)
    c3.metric("Missing constraint dates",constraints.missing_dates)
    if constraints.by_type:
        types=pd.DataFrame([{"Constraint type":x,"Count":y} for x,y in constraints.by_type.items()]).sort_values("Count",ascending=False)
        fig=px.bar(types,x="Constraint type",y="Count",color_discrete_sequence=["#477EA8"])
        fig.update_layout(height=270,margin=dict(t=10,l=0,b=15,r=0))
        st.plotly_chart(fig,use_container_width=True)
    report_table(pd.DataFrame(constraints.detail),"constraints_inventory.csv",height=480)
    st.caption("Constraints are listed without classifying them as hard or soft until the exact meaning of the exported codes is verified.")
