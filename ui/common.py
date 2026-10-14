"""Shared UI helpers for all modules."""
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
from p6toolkit.export import dataframe_to_xlsx

STATUS_ORDER = ["Completed", "In Progress", "Not Started", "Other"]
STATUS_COLORS = {"Completed":"#368B7B", "In Progress":"#D2A253", "Not Started":"#8298B0", "Other":"#AAADB5"}

@st.cache_data(show_spinner=False, max_entries=12)
def load_xer(data:bytes, name:str):
    doc=parse_xer_bytes(data,name)
    snaps=[build_snapshot(doc,pid) for pid,_,_ in list_projects(doc)]
    return doc,snaps

@st.cache_data(show_spinner=False, max_entries=24)
def xlsx_bytes(df:pd.DataFrame, sheet:str)->bytes:
    return dataframe_to_xlsx(df, sheet)

def csv_bytes(df:pd.DataFrame)->bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

def report_table(df, name:str, *, height=390, empty="No records found."):
    if not isinstance(df,pd.DataFrame):
        df=pd.DataFrame(df)
    if df.empty:
        st.info(empty)
        return
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(height,max(110,35*(len(df)+1))))
    stem = name[:-4] if name.lower().endswith(".csv") else name
    c1, c2, _ = st.columns([1, 1, 6])
    with c1:
        st.download_button("Excel (.xlsx)", xlsx_bytes(df, stem), file_name=stem + ".xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"download_xlsx_{name}")
    with c2:
        st.download_button("CSV", csv_bytes(df), file_name=stem + ".csv", mime="text/csv", key=f"download_{name}")

def title(text,subtitle):
    st.markdown(f'<div class="kicker">P6 Toolkit · Core v0.2.2</div>',unsafe_allow_html=True)
    st.title(text)
    st.caption(subtitle)

def kicker(text):
    st.markdown(f'<div class="kicker">{text}</div>',unsafe_allow_html=True)

@st.cache_data(show_spinner=False, max_entries=18)
def analytics(snapshot):
    return summarize_snapshot(snapshot), inspect_network(snapshot), audit_logic(snapshot), audit_constraints(snapshot)


def get_status_table(snapshot, wbs_lookup=None):
    wbs_lookup = wbs_lookup or {}
    return pd.DataFrame([{"Activity ID":a.code,"Activity Name":a.name,
         "Status":activity_status(a.status),"WBS":wbs_lookup.get(a.wbs_id, a.wbs_id or "—"), "Calendar":a.calendar_id or "—",
         "Total Float (h)":a.total_float_hours, "Remaining (h)":a.remaining_hours,
         "Original (h)":a.original_hours, "Task type":a.raw.get("task_type", ""),
         "Early Start":a.raw.get("early_start_date") or a.raw.get("restart_date") or "",
         "Early Finish":a.raw.get("early_end_date") or a.raw.get("reend_date") or ""}
        for a in snapshot.activities])


def network_local(snapshot, code, radius=1, maximum=48):
    lookup=snapshot.by_id(); bycode=snapshot.by_code()
    if code not in bycode:return None,None
    g=nx.DiGraph()
    g.add_nodes_from(a.code for a in snapshot.activities)
    for r in snapshot.relationships:
        if r.predecessor_id in lookup and r.successor_id in lookup:
            g.add_edge(lookup[r.predecessor_id].code,lookup[r.successor_id].code,
                       kind=r.kind, lag=r.lag_hours)
    seen={code}; front={code}
    for _ in range(radius):
        adj=set()
        for n in front:
            adj.update(g.predecessors(n));adj.update(g.successors(n))
        front=adj-seen
        seen.update(front)
        if len(seen)>maximum:break
    if len(seen)>maximum:
        st.warning(f"The sub-network has {len(seen)} nodes; showing at most {maximum}. Reduce the depth.")
        seen={code}|set(sorted(seen-{code})[:maximum-1])
    sub=g.subgraph(seen).copy()
    if not sub.nodes:return None,None
    positions=nx.spring_layout(sub, seed=13, k=1.5/(max(2,len(sub))**0.5),iterations=75)
    edge_x,edge_y=[],[]
    for p,s in sub.edges:
        x1,y1=positions[p];x2,y2=positions[s]
        edge_x.extend([x1,x2,None]);edge_y.extend([y1,y2,None])
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=edge_x,y=edge_y,mode="lines",line=dict(color="#BBC8D8",width=1.5),hoverinfo="skip",showlegend=False))
    nodes=list(sub.nodes)
    fig.add_trace(go.Scatter(x=[positions[n][0] for n in nodes],y=[positions[n][1] for n in nodes],
        mode="markers+text",text=[n for n in nodes],textposition="top center",
        textfont=dict(size=10,color="#233850"),
        marker=dict(size=[18 if n==code else 10 for n in nodes],color=["#E39D4B" if n==code else "#477EA8" for n in nodes],
                    line=dict(width=1,color="white")),
        hovertext=[bycode[n].name for n in nodes],hovertemplate="%{text}: %{hovertext}<extra></extra>",showlegend=False))
    fig.update_layout(height=430,margin=dict(l=4,r=4,t=12,b=4),paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",xaxis=dict(visible=False),yaxis=dict(visible=False))
    rows=[{"Predecessor":p,"Successor":s,"Type":sub[p][s].get("kind"),"Lag (h)":sub[p][s].get("lag")} for p,s in sub.edges]
    return fig,pd.DataFrame(rows)

def comparison_ui(ctx, *, update=False):
    snaps, current, current_key = ctx.snaps, ctx.current, ctx.current_key
    if len(snaps)<2:
        st.info("To compare versions, load at least two XER files of the same project (e.g. BL and UP).")
        st.stop()
    keys=[k for k in snaps if k!=current_key]
    before_key=st.selectbox("Previous version",keys,key="before_update" if update else "before_compare")
    before=snaps[before_key]
    different=before.project_code!=current.project_code
    authorized=True
    if different:
        authorized=st.checkbox("I confirm both XER files belong to the same project even though their codes differ",key="confirm_up" if update else "confirm_comp")
    if not authorized:
        st.warning("Confirm the project identity to run this comparison.")
        st.stop()
    try:
        diff=compare_snapshots(before,current,confirm_same_project=different)
    except ValueError as ex:
        st.error(str(ex));st.stop()
    return before,diff
