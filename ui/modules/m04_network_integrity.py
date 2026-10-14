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

SPEC = ModuleSpec("04", "Network Integrity Analyzer", "Structural diagnostics", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Network Integrity Analyzer","Components, open ends, cycles and exploration of the actual topology")
    c=st.columns(5)
    for col,label,n in zip(c,["Components","Isolated","Cyclic SCC","Start candidates","Finish candidates"],
               [len(graph.weak_components),len(graph.isolated_activities),len(graph.cyclic_sccs),len(graph.start_activities),len(graph.finish_activities)]):col.metric(label,n)
    left,right=st.columns([1,1])
    with left:
        kicker("TOPOLOGY FINDINGS")
        component_rows=[{"Component":i+1,"Size":len(component),"Sample activity IDs":", ".join(component[:5])}
                        for i,component in enumerate(graph.weak_components)]
        report_table(pd.DataFrame(component_rows),"network_components.csv",height=290)
        rows=([{"Finding":"Isolated","Activity ID":x} for x in graph.isolated_activities]+
              [{"Finding":"No predecessor","Activity ID":x} for x in graph.start_activities]+
              [{"Finding":"No successor","Activity ID":x} for x in graph.finish_activities])
        with st.expander("Open ends and isolated activities",expanded=True):
            report_table(pd.DataFrame(rows),"network_open_ends.csv",height=300)
        if graph.cyclic_sccs:
            with st.expander("Cyclic strongly connected components"):
                report_table(pd.DataFrame([{"Component":i+1,"Activities":", ".join(c)} for i,c in enumerate(graph.cyclic_sccs)]),"network_cycles.csv")
    with right:
        kicker("ACTIVITY LOCAL NETWORK")
        candidates=sorted(a.code for a in current.activities)
        focus=st.selectbox("Focus activity",candidates,index=0,key="focus_activity")
        depth=st.slider("Relationship depth",1,2,1)
        fig,edges=network_local(current,focus,depth)
        if fig:st.plotly_chart(fig,use_container_width=True)
        with st.expander("Relationships in this sub-network"):
            report_table(edges,"local_network.csv")
    st.caption("An isolated activity or an open end is a structural finding, not necessarily a scheduling error.")
