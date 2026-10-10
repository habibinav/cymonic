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

from data import analyze_new, gemini_enabled, load_verdicts, run_analysis

st.set_page_config(page_title="Catering Hunter", page_icon="🍴", layout="wide", initial_sidebar_state="collapsed")

# Strip Streamlit's padding/header so the UI fills the page
st.markdown(
    """
<style>
header[data-testid="stHeader"], #MainMenu, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], .stApp { background: #0d0d0d; }
iframe { display: block; }
.st-key-topbar { position: fixed; top: 16px; right: 40px; z-index: 1000; width: 370px !important; }
.st-key-topbar button { border: 0; color: #fff; font-weight: 500; border-radius: 6px; white-space: nowrap; }
.st-key-analyze button { background: #e5484d; }
.st-key-analyze button:hover { background: #ff5a5f; color: #fff; }
.st-key-newlead button { background: rgba(109,109,110,.6); }
.st-key-newlead button:hover { background: rgba(109,109,110,.4); color: #fff; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- data
if "announcements" not in st.session_state:
    st.session_state["announcements"], st.session_state["using_mock"] = load_verdicts()

with st.container(key="topbar"):
    c_new, c_all = st.columns([1.35, 1], gap="small")
    with c_new, st.container(key="newlead"):
        with st.popover("＋ New announcement", use_container_width=True):
            st.markdown("**Paste a corporate event announcement**")
            with st.form("new_lead", clear_on_submit=True, border=False):
                text = st.text_area(
                    "Announcement", height=160, label_visibility="collapsed",
                    placeholder="e.g. Keralytics is hosting a 2-day tech summit in Kochi, Kerala, India on "
                                "2026-12-05 for 500 attendees. Lunch and refreshments will be served.",
                )
                url = st.text_input("Source URL (optional)")
                if st.form_submit_button("Analyze", type="primary", use_container_width=True) and text.strip():
                    with st.spinner("Gemini is reading the announcement…" if gemini_enabled() else "Running agents…"):
                        lead = analyze_new(text.strip(), url.strip() or None)
                    st.session_state["announcements"] = [lead] + st.session_state["announcements"]
                    st.session_state["open_lead"] = lead["id"]
                    st.rerun()
    with c_all, st.container(key="analyze"):
        ai_on = gemini_enabled()
        if st.button("✨ Analyze all" if ai_on else "▶ Analyze all", use_container_width=True,
                     help="Gemini writes reasoning + proposals for every lead it has not analysed yet (results are saved)" if ai_on
                     else "Rule-based. Add GEMINI_API_KEY to .env to use Gemini"):
            bar = st.progress(0.0, text="Gemini is analysing leads…" if ai_on else "Running agents…")
            st.session_state["announcements"], st.session_state["using_mock"] = run_analysis(
                progress=lambda done, total: bar.progress(done / max(total, 1), text=f"Gemini: {done}/{total} leads")
            )
            bar.empty()

# ---------------------------------------------------------------- UI
template = (Path(__file__).parent / "ui.html").read_text(encoding="utf-8")
payload = json.dumps(st.session_state["announcements"], ensure_ascii=False).replace("</", "<\\/")
open_id = json.dumps(st.session_state.pop("open_lead", None))   # auto-open a just-analysed lead once
page = (
    template.replace("__DATA__", payload)
    .replace("__MOCK__", "true" if st.session_state["using_mock"] else "false")
    .replace("__OPEN__", open_id)
)

components.html(page, height=920, scrolling=False)
