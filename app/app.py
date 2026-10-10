"""Corporate Catering Hunter — Netflix-style UI (Streamlit).

Run from the project root:   streamlit run app/app.py

All browsing (home → section → company folder → lead) happens inside frontend/index.html,
a two-way Streamlit component, so transitions stay smooth. When you ask Gemini to analyse
a section, a folder or one lead, the component sends that request here; Python runs Gemini on
just those leads and sends the updated data back without resetting where you are.
"""
from pathlib import Path

import json

import streamlit as st
import streamlit.components.v1 as components

from data import analyze_new, analyze_with_gemini, gemini_enabled, load_leads

st.set_page_config(page_title="Catering Hunter", page_icon="🍴", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
header[data-testid="stHeader"], #MainMenu, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], .stApp { background: #0d0d0d; }
iframe { display: block; }
.st-key-topbar { position: fixed; top: 16px; right: 40px; z-index: 1000; width: 210px !important; }
.st-key-topbar button { border: 0; color: #fff; font-weight: 500; border-radius: 6px; white-space: nowrap;
  background: rgba(109,109,110,.6); }
.st-key-topbar button:hover { background: rgba(109,109,110,.4); color: #fff; }
.st-key-progress { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 1000;
  width: 420px !important; background: #181818; border: 1px solid #333; border-radius: 10px; padding: 10px 16px; }
.st-key-progress:empty { display: none; }
</style>
""",
    unsafe_allow_html=True,
)

_ui = components.declare_component("catering_ui", path=str(Path(__file__).parent / "frontend"))

if "leads" not in st.session_state:
    st.session_state["leads"], st.session_state["using_mock"] = load_leads()
ai_on = gemini_enabled() and not st.session_state["using_mock"]

# ---------------------------------------------------------------- paste a new announcement
with st.container(key="topbar"):
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
                with st.spinner("Gemini is reading the announcement…" if ai_on else "Running agents…"):
                    lead = analyze_new(text.strip(), url.strip() or None)
                st.session_state["leads"] = [lead] + [l for l in st.session_state["leads"] if l["id"] != lead["id"]]
                st.session_state["open_lead"] = lead["id"]
                st.rerun()

# ---------------------------------------------------------------- the UI component
request = _ui(
    data=json.dumps(st.session_state["leads"], ensure_ascii=False),
    mock=st.session_state["using_mock"],
    gemini=ai_on,
    ack=st.session_state.get("ack"),
    open_lead=st.session_state.pop("open_lead", None),
    key="catering_ui",
    default=None,
)

# A Gemini request from the UI: {"action": "analyze", "ids": [...], "label": "...", "nonce": ...}
if (isinstance(request, dict) and request.get("action") == "analyze"
        and request.get("nonce") != st.session_state.get("ack")):
    ids = request.get("ids") or []
    with st.container(key="progress"):
        bar = st.progress(0.0, text=f"✨ Gemini is analysing {request.get('label', 'leads')}…")
        st.session_state["leads"], st.session_state["using_mock"] = analyze_with_gemini(
            ids, progress=lambda done, total: bar.progress(done / max(total, 1), text=f"✨ Gemini: {done}/{total} leads")
        )
    st.session_state["ack"] = request.get("nonce")
    st.rerun()
