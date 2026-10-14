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

SPEC = ModuleSpec("05", "Logic Analyzer", "Descriptive diagnostics", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Logic Analyzer","Relationship types, lags and patterns that need review")
    cols=st.columns(5)
    for col,l,v in zip(cols,["Relationships","FS","SS / FF / SF","Positive lag","Negative lag"],
                        [summary["relationships"],logic.relationship_types.get("FS",0),sum(v for k,v in logic.relationship_types.items() if k in {"SS","FF","SF"}),logic.positive_lags,logic.negative_lags]):col.metric(l,v)
    t1,t2=st.tabs(["Relationship inventory","Logic exceptions"])
    with t1:
        selection=st.multiselect("Relationship type",sorted(logic.relationship_types),default=sorted(logic.relationship_types))
        d=pd.DataFrame(logic.relationship_rows)
        if not d.empty:
            d=d[d["Type"].isin(selection)]
            chk=st.checkbox("Only relationships with lag ≠ 0",key="lag_filter")
            if chk:d=d[d["Lag (h)"].fillna(0)!=0]
        report_table(d,"logic_relations.csv",height=540)
    with t2:
        st.markdown("**Identical duplicate relationships**")
        report_table(pd.DataFrame([{"Predecessor":a,"Successor":b,"Type":t,"Lag (h)":lag} for a,b,t,lag in logic.duplicate_identical]),"logic_duplicates.csv")
        st.markdown("**Multiple relationships between the same activities**")
        report_table(pd.DataFrame([{"Predecessor":a,"Successor":b,"Number":n} for a,b,n in logic.parallel_pair_candidates]),"logic_parallel_pairs.csv")
        st.caption("Several relationships between two activities can be valid; they are not automatically treated as wrong duplicates.")
    st.warning("Constructability review, temporal redundancy and driving relationships still require the event and calendar engines.")
