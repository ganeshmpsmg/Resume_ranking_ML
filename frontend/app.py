"""
frontend/app.py
----------------
Resume Ranking System — Streamlit Frontend.

Run with:
    streamlit run app.py

Expects the FastAPI backend at API_BASE_URL (default http://localhost:8000).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from components.ui_components import inject_css, health_badge
from services.api_client import get_health

st.set_page_config(
    page_title="Resume Ranking System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Navigation ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 Resume Ranking System")
    st.caption("AI-powered semantic resume screening")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "🏠 Home & Upload",
            "📊 Rank & Dashboard",
            "🔍 Candidate Profile",
            "📈 Evaluation",
            "⚖️ Compare Resumes",
            "🤖 AI Feedback (LLM)",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # Live health status widget
    with st.expander("🛠 System Health", expanded=False):
        h = get_health()
        st.markdown(health_badge(h.get("database", False),    "PostgreSQL"),  unsafe_allow_html=True)
        st.markdown(health_badge(h.get("redis", False),       "Redis"),       unsafe_allow_html=True)
        st.markdown(health_badge(h.get("chroma", False),      "ChromaDB"),    unsafe_allow_html=True)
        st.markdown(health_badge(h.get("embedding_model_loaded", False), "SBERT Model"), unsafe_allow_html=True)

    st.caption("Backend: " + os.getenv("API_BASE_URL", "http://localhost:8000"))

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "🏠 Home & Upload":
    from pages.home import render
elif page == "📊 Rank & Dashboard":
    from pages.dashboard import render
elif page == "🔍 Candidate Profile":
    from pages.profile import render
elif page == "📈 Evaluation":
    from pages.evaluation import render
elif page == "⚖️ Compare Resumes":
    from pages.compare import render
elif page == "🤖 AI Feedback (LLM)":
    from pages.llm_feedback import render
else:
    from pages.home import render

render()
