"""P6 Toolkit Core v0.2.2 — operational Streamlit workbench.

All diagnostics are descriptive unless expressly validated against P6.
Thin shell: modules live in ui/modules (see ui/registry.py).
Run on Windows: py -m streamlit run app.py
"""
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
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))  # make the ui package importable from any cwd
from ui.common import load_xer, title
from ui.context import build_context
from ui.datadate import data_date_sidebar, confirmed_data_dates
from ui.registry import load_modules
from ui.auth import require_login

st.set_page_config(page_title="P6 Toolkit | Schedule Engineering", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{max-width:1650px;padding-top:1.5rem;padding-bottom:3rem}
h1,h2,h3{letter-spacing:-.035em}h1{color:#182A43!important;font-size:2.1rem!important}
[data-testid="stMetric"]{background:#F5F7FA;border:1px solid #E4E9F1;border-radius:12px;padding:15px 16px}
[data-testid="stMetricLabel"]{font-weight:550!important}
section[data-testid="stSidebar"]{background:#F3F6FA}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{line-height:1.35}
div[data-testid="stDataFrame"]{border:1px solid #E3E8F0;border-radius:8px}
.mini{font-size:13px;color:#5C6F87}
.kicker{font-size:11px;text-transform:uppercase;letter-spacing:.13em;font-weight:750;color:#376996}
.rule{height:1px;background:#E6EBF2;margin:16px 0}
</style>""", unsafe_allow_html=True)

USER = require_login()      # stops here until signed in (when access control is configured)

TOOLS = load_modules()
BY_NAME = {m.SPEC.name: m for m in TOOLS}
NAV = [m.SPEC.name for m in TOOLS]
MODULES = sorted(((m.SPEC.id, m.SPEC.name, m.SPEC.maturity) for m in TOOLS), key=lambda x: x[0])


def footer():
    st.markdown('<div class="rule"></div>',unsafe_allow_html=True)
    with st.expander(f"Scope · {len(MODULES)} modules and implementation maturity"):
        st.dataframe(pd.DataFrame(MODULES,columns=["Module","Tool","Implementation"]),hide_index=True,use_container_width=True)
    st.caption("P6 Toolkit Core · v0.2.2 · Read-only XER analytics · Results do not replace scheduling and validation in Primavera P6.")



# Sidebar and source selection.
st.sidebar.markdown("### 🧭 P6 TOOLKIT")
st.sidebar.caption("Schedule Engineering Workbench · 0.2.2")
page=st.sidebar.radio("Tool", NAV, index=0)
st.sidebar.divider()
tool=BY_NAME[page]
if not tool.SPEC.needs_xer:
    tool.render(None)
    footer()
    st.stop()
user_files=st.sidebar.file_uploader("XER schedules (BL / UP)",type=["xer"],accept_multiple_files=True)
use_demo=st.sidebar.checkbox("Use demo project",value=False)
source_files=[]
if user_files:
    source_files=[(x.name,x.getvalue()) for x in user_files]
elif use_demo:
    source_files=[(p.name,p.read_bytes()) for p in sorted((Path(__file__).parent/"examples").glob("*.xer"))]

if not source_files:
    title("P6 Toolkit — Schedule Engineering",f"{len(MODULES)} modules · Schedule analysis and diagnostics")
    st.info("Load one or more XER files from the sidebar, or enable the demo project to explore the Toolkit. "
            "The P6 Relationship Converter does not need an XER: pick it in the menu.")
    st.markdown("**Core design:** Data management → Network quality → Logic → Trends → Dashboard.")
    st.stop()

docs={}; snaps={}; ingestion=[]
for name,payload in source_files:
    try:
        doc,parts=load_xer(payload,name)
        docs[(name,doc.sha256)]=doc
        ingestion.append({"File":name,"Projects":len(parts),"Tables":len(doc.tables),"Encoding":doc.encoding,"SHA256":doc.sha256[:12]})
        for part in parts:
            key=f"{name} · {part.project_code} · {doc.sha256[:8]}"
            snaps[key]=part
    except (XERParseError,ValueError) as exc:
        st.sidebar.error(f"{name}: {exc}")
if not snaps:
    st.error("No project could be read from the loaded files.")
    st.stop()

st.sidebar.divider()
current_key=st.sidebar.selectbox("Project / snapshot",list(snaps),key="current_snapshot")
current=snaps[current_key]
st.sidebar.divider()
data_date_sidebar(current_key,current)
st.sidebar.divider()
st.sidebar.caption(f"{len(snaps)} snapshot(s) loaded · {len(current.activities):,} activities")
st.sidebar.caption("Read-only · never writes or modifies XER files")

ctx=build_context(snaps,docs,ingestion,current_key,confirmed_data_dates())
tool.render(ctx)

footer()
