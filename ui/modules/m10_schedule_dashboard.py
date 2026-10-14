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

SPEC = ModuleSpec("10", "Schedule Dashboard", "Integrated view", needs_xer=True)


def render(ctx):
    snaps, docs, ingestion, current_key, current = ctx.snaps, ctx.docs, ctx.ingestion, ctx.current_key, ctx.current
    summary, graph, logic, constraints = ctx.summary, ctx.graph, ctx.logic, ctx.constraints
    wbs_lookup, df_activities, status = ctx.wbs_lookup, ctx.df_activities, ctx.status
    title("Project Schedule Overview",f"{current.project_name} · {current.filename} · original P6 data")
    cols=st.columns(6)
    for col,label,value in zip(cols,["Total Activities","Completed","In Progress","Not Started","Relationships","Calendars"],
          [summary["activities"],status.get("Completed",0),status.get("In Progress",0),status.get("Not Started",0),summary["relationships"],summary["calendar_count"]]):
        col.metric(label,f"{value:,}")
    left,right=st.columns([1.05,1])
    with left:
        kicker("ACTIVITY STATUS")
        stat_df=pd.DataFrame([{"Status":s,"Activities":status.get(s,0)} for s in STATUS_ORDER if status.get(s)])
        if not stat_df.empty:
            fig=px.bar(stat_df,x="Activities",y="Status",orientation="h",color="Status",
                       color_discrete_map=STATUS_COLORS,text="Activities")
            fig.update_layout(height=310,showlegend=False,margin=dict(t=15,b=30,l=0,r=20),yaxis=dict(categoryorder="array",categoryarray=list(reversed(STATUS_ORDER))))
            st.plotly_chart(fig,use_container_width=True)
    with right:
        kicker("RELATIONSHIP MIX")
        df_types=pd.DataFrame([{"Type":k,"Count":v} for k,v in logic.relationship_types.items()])
        if not df_types.empty:
            fig=px.pie(df_types,names="Type",values="Count",hole=.66,
                       color_discrete_sequence=["#2D6B95","#5CA19A","#C9A56D","#8897A7"])
            fig.update_layout(height=310,margin=dict(t=15,b=20,l=5,r=5),legend=dict(orientation="h",y=-.08))
            st.plotly_chart(fig,use_container_width=True)
    kicker("DIAGNOSTIC SNAPSHOT — observed evidence, not a certified score")
    diagnostic=[
       {"Check":"Disconnected components","Observed":summary["network_components"],"Interpretation":"Review" if summary["network_components"]>1 else "No warning"},
       {"Check":"Isolated activities","Observed":summary["isolated"],"Interpretation":"Review" if summary["isolated"] else "No warning"},
       {"Check":"Cyclic SCCs","Observed":summary["cyclic_sccs"],"Interpretation":"Review" if summary["cyclic_sccs"] else "No warning"},
       {"Check":"Negative Float (incomplete)","Observed":summary["negative_float"],"Interpretation":"P6 exported TF; investigate"},
       {"Check":"Positive lags","Observed":logic.positive_lags,"Interpretation":"Review where applicable"},
       {"Check":"Negative lags","Observed":logic.negative_lags,"Interpretation":"Review where applicable"},
       {"Check":"Activities with constraints","Observed":constraints.activities_with_constraints,"Interpretation":"Inventory; influence not yet tested"},
       {"Check":"Incomplete activities without TF","Observed":summary["remaining_without_float"],"Interpretation":"Data gap"},
    ]
    st.dataframe(pd.DataFrame(diagnostic),use_container_width=True,hide_index=True,height=300)
    with st.expander("File, provenance and limitations"):
        st.dataframe(pd.DataFrame(ingestion),use_container_width=True,hide_index=True)
        st.caption(f"PROJECT.last_recalc_date: {current.data_date or 'not available'}. Not a verified Data Date (confirm it in the sidebar).")
        st.caption("Structural diagnostics do not replace temporal validation or the P6 CPM calculation.")
