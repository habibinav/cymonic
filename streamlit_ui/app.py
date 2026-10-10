"""Corporate Catering Hunter — Netflix-style verdicts UI (Streamlit).

Run:  cd streamlit_ui && streamlit run app.py

The whole browsing experience (home → category → lead detail) lives in ui.html
so the transitions stay smooth (no Streamlit reruns between clicks).
Python only loads the data and handles "Analyze all".
"""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from data import load_verdicts, run_analysis

st.set_page_config(page_title="Catering Hunter", page_icon="🍴", layout="wide", initial_sidebar_state="collapsed")

# Strip Streamlit's padding/header so the UI fills the page
st.markdown(
    """
<style>
header[data-testid="stHeader"], #MainMenu, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], .stApp { background: #0d0d0d; }
iframe { display: block; }
.st-key-topbar { position: fixed; top: 16px; right: 40px; z-index: 1000; width: auto !important; }
.st-key-topbar button { background: #e5484d; border: 0; color: #fff; font-weight: 500; border-radius: 6px; }
.st-key-topbar button:hover { background: #ff5a5f; color: #fff; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- data
if "announcements" not in st.session_state:
    st.session_state["announcements"], st.session_state["using_mock"] = load_verdicts()

with st.container(key="topbar"):
    if st.button("▶ Analyze all"):
        with st.spinner("Running agents…"):
            st.session_state["announcements"], st.session_state["using_mock"] = run_analysis()

# ---------------------------------------------------------------- UI
template = (Path(__file__).parent / "ui.html").read_text(encoding="utf-8")
payload = json.dumps(st.session_state["announcements"], ensure_ascii=False).replace("</", "<\\/")
page = template.replace("__DATA__", payload).replace("__MOCK__", "true" if st.session_state["using_mock"] else "false")

components.html(page, height=920, scrolling=False)
