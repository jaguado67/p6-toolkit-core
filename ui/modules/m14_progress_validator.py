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
from p6toolkit.progress import validate_progress, suggested_data_date

SPEC = ModuleSpec("14", "Progress Validator", "Diagnostics with confirmed Data Date", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Progress Validator","Progress consistency against the Data Date: actual dates, status and sequence")
    if ctx.data_date is None:
        st.info("Confirm this snapshot's Data Date in the sidebar to run the checks.")
    else:
        st.caption(f"Confirmed Data Date: {ctx.data_date:%Y-%m-%d %H:%M}")
        rep=validate_progress(current,ctx.data_date)
        checks=pd.DataFrame([{"ID":c.check_id,"Check":c.check,"Eligible population":c.population,
                              "Eligible":c.eligible,"Findings":c.findings,
                              "Share":(f"{c.findings/c.eligible:.1%}" if c.eligible else "—"),
                              "Related":c.dcma_reference or ""} for c in rep.checks])
        m=st.columns(4)
        m[0].metric("Activities",len(current.activities))
        m[1].metric("Checks with findings",int((checks["Findings"]>0).sum()))
        m[2].metric("Out-of-sequence (P08)",int(checks.loc[checks.ID=="P08","Findings"].iloc[0]))
        m[3].metric("Invalid dates (P01–P04)",int(checks.loc[checks.ID.isin(["P01","P02","P03","P04"]),"Findings"].sum()))
        if rep.unparsed_dates:
            st.warning(f"{rep.unparsed_dates} actual date(s) in an unrecognised format were left out of the checks.")
        report_table(checks,"progress_checks.csv",height=420)
        findings=pd.DataFrame([asdict(f) for f in rep.findings])
        if not findings.empty:
            chosen=st.multiselect("Filter findings by check",sorted(findings.check_id.unique()),
                                  default=sorted(findings.check_id.unique()))
            findings=findings[findings.check_id.isin(chosen)]
        report_table(findings,"progress_findings.csv",height=480,empty="No issues found.")
        st.caption("P08 compares actual dates and the relationship type only; positive lags cannot remove a violation "
                   "and negative lags are separated into P09. P10 groups same-day overlaps: when the export has no time "
                   "of day it is impossible to decide whether they violate the logic.")
