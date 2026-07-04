"""frontend/pages/profile.py — Candidate Profile deep-dive."""
from __future__ import annotations
import streamlit as st

from services.api_client import get_resume, get_feedback, list_resumes, list_jds
from components.ui_components import skill_pills, section_header, confidence_badge
from utils.charts import radar_chart, gauge_chart


def render():
    st.title("🔍 Candidate Profile")

    resumes = list_resumes()
    jds     = list_jds()

    if not resumes:
        st.warning("No resumes uploaded yet. Go to **🏠 Home & Upload**.")
        return
    if not jds:
        st.warning("No job descriptions added yet. Go to **🏠 Home & Upload**.")
        return

    # ── Selectors ─────────────────────────────────────────────────────────
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        resume_opts = {f"{r.get('name') or r.get('filename')} — {r['filename']}": r
                       for r in resumes}
        sel_resume_label = st.selectbox("Select Candidate", list(resume_opts.keys()))
        sel_resume       = resume_opts[sel_resume_label]

    with col_sel2:
        jd_opts = {f"{j['title']} ({j['source']})": j for j in jds}
        sel_jd_label = st.selectbox("Select Job Description", list(jd_opts.keys()))
        sel_jd       = jd_opts[sel_jd_label]

    resume_detail = get_resume(sel_resume["id"])

    # ── Try to get ranking result from session state ───────────────────────
    rank_result = None
    last_result = st.session_state.get("last_rank_result")
    if last_result:
        for rc in last_result.get("results", []):
            if rc["resume_id"] == sel_resume["id"]:
                rank_result = rc
                break

    # ── Main layout ───────────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown(f"## {resume_detail.get('name') or 'Unknown Candidate'}")
        info_rows = [
            ("📄 File",       resume_detail.get("filename", "")),
            ("📧 Email",      resume_detail.get("email") or "Not detected"),
            ("📱 Phone",      resume_detail.get("phone") or "Not detected"),
            ("🎓 Education",  resume_detail.get("education_level") or "Not detected"),
            ("💼 Experience", f"{resume_detail.get('years_experience', 0)} years"),
        ]
        if resume_detail.get("linkedin"):
            info_rows.append(("🔗 LinkedIn", resume_detail["linkedin"]))
        if resume_detail.get("github"):
            info_rows.append(("💻 GitHub", resume_detail["github"]))

        for label, value in info_rows:
            st.markdown(f"**{label}:** {value}")

        if rank_result:
            st.divider()
            st.markdown("### 🎯 Match Score")
            st.plotly_chart(
                gauge_chart(rank_result["final_score"] * 100),
                use_container_width=True,
            )
            conf_html = confidence_badge(rank_result.get("confidence", ""))
            st.markdown(f"Confidence: {conf_html}", unsafe_allow_html=True)
        else:
            st.info("Run **📊 Rank & Dashboard** first to see this candidate's score.")

    with col_right:
        if rank_result:
            st.plotly_chart(radar_chart(rank_result), use_container_width=True)

            st.markdown("### 📊 Score Breakdown")
            score_data = {
                "Semantic Similarity": rank_result["semantic_similarity"],
                "Skill Match":         rank_result["skill_match"],
                "Experience Match":    rank_result["experience_match"],
                "Education Match":     rank_result["education_match"],
                "Project Relevance":   rank_result["project_relevance"],
                "Final Score":         rank_result["final_score"],
            }
            for label, val in score_data.items():
                col_a, col_b = st.columns([2, 3])
                col_a.markdown(f"**{label}**")
                col_b.progress(float(val))

        # ── Skills by category ────────────────────────────────────────────
        st.divider()
        section_header("Skills by Category", "🧰")
        skills_by_cat = resume_detail.get("skills_by_category", {})
        if skills_by_cat:
            cats = list(skills_by_cat.keys())
            cat_cols = st.columns(min(len(cats), 3))
            for i, (cat, skills) in enumerate(skills_by_cat.items()):
                with cat_cols[i % len(cat_cols)]:
                    st.markdown(f"**{cat}**")
                    st.markdown(skill_pills(skills), unsafe_allow_html=True)
        else:
            st.info("No categorized skills detected.")

    st.divider()

    # ── ATS Feedback ──────────────────────────────────────────────────────
    section_header("Resume Feedback & ATS Score", "📝")

    if rank_result:
        if st.button("📊 Generate Feedback", type="primary"):
            with st.spinner("Analyzing resume against job description…"):
                feedback = get_feedback(sel_resume["id"], sel_jd["id"])
            st.session_state[f"fb_{sel_resume['id']}_{sel_jd['id']}"] = feedback

        fb_key = f"fb_{sel_resume['id']}_{sel_jd['id']}"
        if fb_key in st.session_state:
            feedback = st.session_state[fb_key]

            ats_col1, ats_col2 = st.columns([1, 2])
            with ats_col1:
                st.metric("🤖 ATS Score", f"{feedback.get('ats_score', 0):.0f} / 100")
                import plotly.graph_objects as go
                ats_bd = feedback.get("ats_breakdown", {})
                if ats_bd:
                    fig = go.Figure(go.Bar(
                        x=list(ats_bd.values()),
                        y=list(ats_bd.keys()),
                        orientation="h",
                        marker_color="#E07A3F",
                    ))
                    fig.update_layout(height=220, margin=dict(l=5, r=5, t=20, b=5),
                                       title="ATS Score Breakdown")
                    st.plotly_chart(fig, use_container_width=True)

            with ats_col2:
                fb_tabs = st.tabs(["💪 Strengths", "⚠️ Weaknesses", "💡 Suggestions",
                                    "✅ Matching Skills", "❌ Missing Skills"])
                with fb_tabs[0]:
                    for s in feedback.get("strengths", []):
                        st.markdown(f"- {s}")
                with fb_tabs[1]:
                    items = feedback.get("weaknesses", [])
                    if items:
                        for w in items:
                            st.markdown(f"- {w}")
                    else:
                        st.success("No significant weaknesses identified.")
                with fb_tabs[2]:
                    for s in feedback.get("suggestions", []):
                        st.markdown(f"- {s}")
                with fb_tabs[3]:
                    st.markdown(
                        skill_pills(feedback.get("matching_skills", [])),
                        unsafe_allow_html=True,
                    )
                with fb_tabs[4]:
                    st.markdown(
                        skill_pills(feedback.get("missing_skills", []), missing=True),
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Run **📊 Rank & Dashboard** first, then come back here for detailed feedback.")

    # ── Raw resume text ────────────────────────────────────────────────────
    with st.expander("📜 View Raw Resume Text"):
        st.text(resume_detail.get("raw_text", "")[:3000])
        if len(resume_detail.get("raw_text", "")) > 3000:
            st.caption("… (truncated to 3000 chars for display)")
