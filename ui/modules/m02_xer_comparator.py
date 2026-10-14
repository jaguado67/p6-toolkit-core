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

SPEC = ModuleSpec("02", "XER Comparator", "Partially operational", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("XER Comparator","Changes between two versions: activities, relationships and attributes")
    before,diff=comparison_ui(ctx)
    metrics=st.columns(4)
    for c,k,v in zip(metrics,["Added","Removed","Field changes","Relation changes"],
                     [len(diff.added),len(diff.removed),len(diff.field_changes),len(diff.relationships_added)+len(diff.relationships_removed)]):c.metric(k,v)
    st.info("Matching is by Activity ID. Renamed IDs require manual review.")
    t1,t2,t3=st.tabs(["Attribute changes","Activity changes","Relationship changes"])
    with t1:
        df=pd.DataFrame([asdict(x) for x in diff.field_changes])
        if not df.empty:
            fields=sorted(df.field_name.unique())
            wanted=st.multiselect("Fields",fields,default=fields)
            df=df[df.field_name.isin(wanted)]
        report_table(df,"xer_field_changes.csv")
    with t2:
        report_table(pd.DataFrame([{"Change":"Added","Activity ID":x} for x in diff.added]+[{"Change":"Removed","Activity ID":x} for x in diff.removed]),"xer_activity_changes.csv")
    with t3:
        report_table(pd.DataFrame([{"Change":"Added","Predecessor":x[0],"Successor":x[1],"Type":x[2],"Lag (h)":x[3]} for x in diff.relationships_added]+
            [{"Change":"Removed","Predecessor":x[0],"Successor":x[1],"Type":x[2],"Lag (h)":x[3]} for x in diff.relationships_removed]),"xer_relationship_changes.csv")
    if diff.warnings:st.warning(" · ".join(diff.warnings))
