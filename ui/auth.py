"""Username/password gate. Users and password hashes come from Streamlit secrets:

    # .streamlit/secrets.toml   (never commit this file)
    [auth]
    enabled = true
    [auth.users.jaguado]
    name = "Jair Aguado"
    password = "pbkdf2_sha256$600000$...$..."      # python -m p6toolkit hash-password

Without an [auth] section the app runs open (local use) and says so on screen. Set the environment
variable P6TOOLKIT_REQUIRE_AUTH=1 on any shared server so a missing configuration blocks the app
instead of exposing it.
"""
from __future__ import annotations
import os
import time
import streamlit as st
from p6toolkit.auth import authenticate, normalize_users

MAX_ATTEMPTS = 5
_KEY = "auth_user"


def _auth_config() -> dict | None:
    try:
        section = st.secrets.get("auth") if hasattr(st.secrets, "get") else None
    except Exception:          # no secrets file at all
        section = None
    if not section or not section.get("enabled", True):
        return None
    return {"users": normalize_users(section.get("users", {}))}


def require_login() -> dict | None:
    """Stops the script until a valid user signs in. Returns the user (or None in open local mode)."""
    config = _auth_config()
    if config is None:
        if os.environ.get("P6TOOLKIT_REQUIRE_AUTH") == "1":
            st.error("Access control is required on this server but no users are configured. "
                     "Add an [auth] section to .streamlit/secrets.toml.")
            st.stop()
        st.sidebar.warning("Access control is off (local mode). Configure users before sharing the link.")
        return None
    user = st.session_state.get(_KEY)
    if user:
        st.sidebar.caption(f"Signed in as **{user['name']}**")
        if st.sidebar.button("Sign out", key="auth_sign_out"):
            st.session_state.pop(_KEY, None)
            st.rerun()
        return user
    if not config["users"]:
        st.error("Access control is enabled but no users are defined in [auth.users].")
        st.stop()
    attempts = st.session_state.get("auth_attempts", 0)
    st.title("P6 Toolkit")
    st.caption("Sign in to continue")
    if attempts >= MAX_ATTEMPTS:
        st.error("Too many failed attempts. Close this tab and try again later.")
        st.stop()
    with st.form("login", clear_on_submit=False):
        username = st.text_input("Username", key="auth_username")
        password = st.text_input("Password", type="password", key="auth_password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        found = authenticate(config["users"], username, password)
        if found:
            st.session_state[_KEY] = found
            st.session_state["auth_attempts"] = 0
            st.rerun()
        st.session_state["auth_attempts"] = attempts + 1
        time.sleep(min(2 ** attempts, 8))      # slows down guessing within a session
        st.error("Invalid username or password.")
    st.stop()
