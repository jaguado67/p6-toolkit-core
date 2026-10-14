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

SPEC = ModuleSpec("06", "Schedule Health Index", "Profile, no score", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Schedule Health Index","Verifiable profile of observations — no premature composite score")
    diag=[
        {"Dimension":"XER Integrity","Observation":"Parser warnings","Count":len(current.warnings),"Evidence":"Warnings from import"},
        {"Dimension":"Network","Observation":"Isolated activities","Count":len(graph.isolated_activities),"Evidence":"Network analysis"},
        {"Dimension":"Network","Observation":"Cyclic SCCs","Count":len(graph.cyclic_sccs),"Evidence":"Tarjan / NetworkX"},
        {"Dimension":"Network","Observation":"Disconnected components","Count":max(0,len(graph.weak_components)-1),"Evidence":"Weak connectivity"},
        {"Dimension":"Logic","Observation":"Negative lags","Count":logic.negative_lags,"Evidence":"TASKPRED"},
        {"Dimension":"Logic","Observation":"Identical duplicate relationships","Count":len(logic.duplicate_identical),"Evidence":"TASKPRED"},
        {"Dimension":"Temporal","Observation":"Activities with constraints","Count":constraints.activities_with_constraints,"Evidence":"TASK"},
        {"Dimension":"Data completeness","Observation":"Incomplete activities without TF","Count":summary["remaining_without_float"],"Evidence":"TASK"},
    ]
    report_table(pd.DataFrame(diag),"health_profile.csv")
    st.info("No 0–100 Health Score is shown: there are no validated weights or enough temporal-fitness tests to issue one yet.")
