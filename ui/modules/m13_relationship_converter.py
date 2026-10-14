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
from p6toolkit.converter import (ConverterError, REQUIRED_COLUMNS, TASK_FIELDS,
                                 TASKPRED_FIELDS, convert_workbook, to_import_workbook)

SPEC = ModuleSpec("13", "P6 Relationship Converter", "Operational · validated on a real export", needs_xer=False)


@st.cache_data(show_spinner=False, max_entries=6)
def convert_cached(data: bytes, sheet: str):
    result = convert_workbook(data, sheet)
    return result, to_import_workbook(result)


def render_converter():
    title("P6 Relationship Converter",
          "P6 layout exported to Excel (data sheet) → import workbook TASK + TASKPRED + Validation")
    upload = st.file_uploader("Excel exported from a P6 layout", type=["xlsx"], key="converter_upload")
    sheet = st.text_input("Source sheet", value="data")
    with st.expander("Expected format and rules applied"):
        st.markdown("**Required columns:** " + ", ".join(f"`{c}`" for c in REQUIRED_COLUMNS))
        st.markdown("**Columns used for TASK when present:** `Orig Dur`, `Rem Dur`, `Start`, `Finish`, "
                    "`Actual Start`, `Actual Finish`, `Primary Constraint`, `Primary Constraint Date`.")
        st.markdown("Logic is read from *Predecessor Details* (`A1980: FS, M1210: SS 57`). "
                    "*Successor Details* is only used to check that both columns describe the same network.")
    if upload is None:
        st.info("Upload the weekly Excel. The result is a workbook ready for File › Import › Spreadsheet in P6.")
        return
    try:
        result, workbook = convert_cached(upload.getvalue(), sheet.strip() or "data")
    except ConverterError as exc:
        st.error(str(exc))
        return
    blocking = [i for i in result.issues if not i.check.startswith("Dropped row")]
    cols = st.columns(5)
    for col, label, value in zip(cols, ["Activities", "Relationships", "Lagged relationships", "Dropped rows", "Issues"],
                                 [result.activity_count, result.relationship_count, result.lagged_relationships,
                                  result.dropped_rows, len(blocking)]):
        col.metric(label, f"{value:,}")
    if blocking:
        st.warning(f"{len(blocking)} issue(s) worth reviewing before importing (see the Validation tab).")
    else:
        st.success("Predecessor and Successor Details match; no unknown IDs or unreadable relationships.")
    name = Path(upload.name).stem + " - P6 Import.xlsx"
    st.download_button("Download P6 import workbook (.xlsx)", workbook, file_name=name,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary", key="converter_download")
    t1, t2, t3, t4 = st.tabs(["Validation", "Relationship mix", "TASKPRED preview", "TASK preview"])
    with t1:
        report_table(pd.DataFrame([{"Check": i.check, "Activity ID": i.activity_id, "Detail": i.detail}
                                   for i in result.issues]), "converter_validation.csv",
                     empty="No issues found.")
        st.markdown("**Declared assumptions**")
        for a in result.assumptions:
            st.caption("• " + a)
    with t2:
        mix = pd.DataFrame([{"Type": k, "Count": v} for k, v in sorted(result.relationship_types.items())])
        types = pd.DataFrame([{"Activity Type": k, "Count": v} for k, v in result.activity_types.items()])
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(mix, hide_index=True, use_container_width=True)
        with c2:
            st.dataframe(types, hide_index=True, use_container_width=True)
    with t3:
        st.dataframe(pd.DataFrame(result.taskpred_rows[:500], columns=TASKPRED_FIELDS),
                     hide_index=True, use_container_width=True, height=420)
        st.caption(f"First 500 of {result.relationship_count:,} relationships. The downloaded file contains all of them.")
    with t4:
        st.dataframe(pd.DataFrame(result.task_rows[:500], columns=TASK_FIELDS),
                     hide_index=True, use_container_width=True, height=420)
        st.caption(f"First 500 of {result.activity_count:,} activities.")



def render(ctx=None):
    render_converter()
