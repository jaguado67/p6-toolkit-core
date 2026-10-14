"""Data Date confirmation, shared by every module that needs it (M08, M11, M14).

The XER does not carry an unambiguous Data Date field (see p6toolkit.progress.data_date_candidates),
so the user confirms it once per snapshot. Confirmations live in st.session_state and survive
switching between snapshots in the same session.
"""
from __future__ import annotations
from datetime import datetime, time
import streamlit as st
from p6toolkit.progress import data_date_candidates, suggested_data_date

_STORE = "confirmed_data_dates"


def confirmed_data_dates() -> dict[str, datetime]:
    if _STORE not in st.session_state:
        st.session_state[_STORE] = {}
    return st.session_state[_STORE]


def data_date_sidebar(snapshot_key: str, snapshot) -> datetime | None:
    store = confirmed_data_dates()
    st.sidebar.markdown("**Data Date**")
    current = store.get(snapshot_key) or suggested_data_date(snapshot)
    tag = snapshot.sha256[:8]
    c1, c2 = st.sidebar.columns([3, 2])
    day = c1.date_input("Data Date", value=current.date() if current else None, key=f"dd_day_{tag}",
                        label_visibility="collapsed")
    hour = c2.time_input("Time", value=current.time() if current else time(8, 0), key=f"dd_time_{tag}",
                         label_visibility="collapsed")
    ok = st.sidebar.checkbox("Confirmed against P6 (Project › Dates)", value=snapshot_key in store,
                             key=f"dd_ok_{tag}")
    if ok and day:
        store[snapshot_key] = datetime.combine(day, hour)
    else:
        store.pop(snapshot_key, None)
    with st.sidebar.expander("Where does the suggestion come from?"):
        for source, value in data_date_candidates(snapshot):
            st.caption(f"{source}: {value:%Y-%m-%d %H:%M}")
        st.caption("Oracle's XER map labels last_recalc_date only as 'Last Recalc Date'. Compare with the Data "
                   "Date shown in P6 before confirming.")
    return store.get(snapshot_key)
