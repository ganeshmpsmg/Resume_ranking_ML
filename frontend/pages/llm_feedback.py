"""frontend/pages/llm_feedback.py"""
import streamlit as st
from services.api_client import get_llm_feedback, list_resumes, list_jds
from components.ui_components import skill_pills


def render():
    st.title("🤖 AI Feedback (LLM-Powered)")
    st.caption(
        "Uses **LangChain + OpenAI GPT** to generate rich, personalised resume feedback. "
        "Requires `OPENAI_API_KEY` set in the backend `.env` file."
    )

    resumes = list_resumes()
    jds     = list_jds()

    if not resumes:
        st.warning("Upload resumes first → **🏠 Home & Upload**")
        return
    if not jds:
        st.warning("Add a job description first → **🏠 Home & Upload**")
        return
    if "last_rank_result" not in st.session_state:
        st.warning("Run **📊 Rank & Dashboard** first so ranking scores are available.")
        return

    result = st.session_state["last_rank_result"]
    ranked = result.get("results", [])

    resume_opts = {f"{r.get('name') or r.get('filename')}": r for r in resumes}
    jd_opts     = {f"{j['title']} ({j['source']})": j for j in jds}

    c1, c2 = st.columns(2)
    with c1:
        sel_r = st.selectbox("Candidate", list(resume_opts.keys()))
    with c2:
        sel_j = st.selectbox("Job Description", list(jd_opts.keys()))

    resume = resume_opts[sel_r]
    jd     = jd_opts[sel_j]

    regenerate = st.checkbox("Force regenerate (bypass cache)", value=False)

    if st.button("🤖 Generate AI Feedback", type="primary"):
        with st.spinner("Calling GPT — this may take 10–20 seconds…"):
            try:
                feedback = get_llm_feedback(resume["id"], jd["id"], regenerate=regenerate)
                st.session_state["llm_fb"] = feedback
            except Exception as e:
                st.error(f"LLM feedback failed: {e}")
                return

    if "llm_fb" not in st.session_state:
        st.info("Click **Generate AI Feedback** to start.")
        return

    fb = st.session_state["llm_fb"]

    if fb.get("llm_generated"):
        st.success("✅ AI-generated feedback (GPT)")
    else:
        st.info("ℹ️ Rule-based feedback (LLM unavailable or key not set)")

    if fb.get("llm_feedback_text"):
        st.markdown("### 🧠 Overall Assessment")
        st.info(fb["llm_feedback_text"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💪 Strengths")
        for s in fb.get("strengths", []):
            st.markdown(f"- {s}")

        st.markdown("### ✅ Matching Skills")
        st.markdown(skill_pills(fb.get("matching_skills", [])), unsafe_allow_html=True)

    with col2:
        st.markdown("### ⚠️ Weaknesses")
        for w in fb.get("weaknesses", []):
            st.markdown(f"- {w}")

        st.markdown("### ❌ Missing Skills")
        st.markdown(skill_pills(fb.get("missing_skills", []), missing=True), unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💡 Suggestions to Improve ATS Score")
    for s in fb.get("suggestions", []):
        st.markdown(f"- {s}")

    st.markdown(f"### 🤖 ATS Score: `{fb.get('ats_score', 0):.0f} / 100`")
    ats_bd = fb.get("ats_breakdown", {})
    if ats_bd:
        import pandas as pd
        df = pd.DataFrame(list(ats_bd.items()), columns=["Component", "Points"])
        st.dataframe(df, use_container_width=True, hide_index=True)
