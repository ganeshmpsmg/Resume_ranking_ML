"""frontend/pages/dashboard.py — Rank & Analytics dashboard."""
from __future__ import annotations
import pandas as pd
import streamlit as st
import numpy as np
from collections import Counter

from services.api_client import list_jds, list_resumes, rank_resumes
from components.ui_components import candidate_card, skill_pills, section_header
from utils.charts import (
    ranking_bar_chart, similarity_distribution, experience_bar,
    skill_frequency_chart,
)

PRIMARY = "#2D5DA1"
DANGER  = "#C0392B"

def render():
    st.title("📊 Rank & Analytics Dashboard")

    jds     = list_jds()
    resumes = list_resumes()

    if not jds:
        st.warning("No job descriptions found. Go to **🏠 Home & Upload** to add one.")
        return
    if not resumes:
        st.warning("No resumes found. Go to **🏠 Home & Upload** to upload some.")
        return

    # ── Controls ─────────────────────────────────────────────────────────
    with st.expander("⚙️ Ranking Controls", expanded=True):
        jd_options = {f"{j['title']} ({j['source']})": j for j in jds}
        selected_jd_label = st.selectbox("Select Job Description", list(jd_options.keys()))
        selected_jd = jd_options[selected_jd_label]

        use_hybrid = st.toggle("Hybrid search (vector + BM25)", value=True)

        st.markdown("**Scoring Weights**")
        wc = st.columns(5)
        w_sem  = wc[0].number_input("Semantic", 0.0, 1.0, 0.40, 0.05)
        w_sk   = wc[1].number_input("Skill",    0.0, 1.0, 0.25, 0.05)
        w_exp  = wc[2].number_input("Exp",      0.0, 1.0, 0.20, 0.05)
        w_edu  = wc[3].number_input("Education",0.0, 1.0, 0.10, 0.05)
        w_proj = wc[4].number_input("Projects", 0.0, 1.0, 0.05, 0.05)
        total  = w_sem + w_sk + w_exp + w_edu + w_proj
        st.caption(f"Weights sum: **{total:.2f}** {'✅' if abs(total-1.0)<0.01 else '⚠️ will be normalised'}")

        # ── Fixed Slider Logic ─
        resume_count = len(resumes)
        top_k = st.slider(
            "Show top N candidates",
            min_value=1,
            max_value=resume_count,
            value=min(5, resume_count)
        )
        
        run   = st.button("🚀 Rank Resumes", type="primary")

    if not run and "last_rank_result" not in st.session_state:
        st.info("Configure controls above and click **Rank Resumes**.")
        return

    if run:
        weights = {
            "semantic_similarity": w_sem, "skill_match": w_sk,
            "experience_match": w_exp, "education_match": w_edu, "project_relevance": w_proj,
        }
        with st.spinner("Ranking resumes — computing embeddings and hybrid search…"):
            result = rank_resumes(
                jd_id=selected_jd["id"],
                weights=weights,
                top_k=top_k,
                use_hybrid=use_hybrid,
            )
        st.session_state["last_rank_result"] = result
        st.session_state["last_jd"]          = selected_jd

    # ── Metrics Safety Guard ─
    result = st.session_state["last_rank_result"]
    jd     = st.session_state.get("last_jd", selected_jd)
    ranked = result.get("results", [])

    if not ranked:
        st.warning("No ranking results available.")
        return

    if result.get("cached"):
        st.info("⚡ Results served from Redis cache.")

    # ── Summary metrics ───────────────────────────────────────────────────
    # ── Safe Metrics Calculation
    avg_score = np.mean([r["final_score"] * 100 for r in ranked]) if ranked else 0
    avg_skill = np.mean([r["skill_match"] * 100 for r in ranked]) if ranked else 0
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Candidates",   len(ranked))
    m2.metric("Avg Score",          f"{avg_score:.1f}%")
    m3.metric("High Confidence",    sum(1 for r in ranked if r["confidence"] == "High"))
    m4.metric("Avg Skill Match",    f"{avg_skill:.1f}%")
    m5.metric("Time",               f"{result.get('elapsed_seconds', 0):.2f}s")

    # ── Search + download ─────────────────────────────────────────────────
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        search = st.text_input("🔍 Search candidate", placeholder="Name or filename…")
    with sc2:
        df_exp = pd.DataFrame([{
            "Rank": i+1, "Name": r["name"], "Score(%)": round(r["final_score"]*100, 2),
            "Confidence": r["confidence"],
            "Semantic(%)": round(r["semantic_similarity"]*100, 2),
            "Skill(%)": round(r["skill_match"]*100, 2),
            "Exp(yrs)": r["years_experience"],
            "Education": r.get("education_level") or "",
            "Matching Skills": ", ".join(r.get("matching_skills", [])),
            "Missing Skills":  ", ".join(r.get("missing_skills", [])),
        } for i, r in enumerate(ranked)])
        st.download_button(
            "⬇️ Export CSV",
            df_exp.to_csv(index=False).encode(),
            file_name=f"ranking_{jd['id'][:8]}.csv",
            mime="text/csv",
        )

    if search:
        q = search.lower()
        ranked = [r for r in ranked if q in r["name"].lower() or q in r["filename"].lower()]

    tabs = st.tabs(["🏆 Ranked List", "📈 Analytics"])

    # ── Tab 1: Ranked list ────────────────────────────────────────────────
    with tabs[0]:
        for i, cand in enumerate(ranked, start=1):
            candidate_card(i, cand)
            with st.expander("Score breakdown & skills"):
                sc = st.columns(5)
                sc[0].metric("Semantic",   f"{cand['semantic_similarity']*100:.0f}%")
                sc[1].metric("Skill",      f"{cand['skill_match']*100:.0f}%")
                sc[2].metric("Experience", f"{cand['experience_match']*100:.0f}%")
                sc[3].metric("Education",  f"{cand['education_match']*100:.0f}%")
                sc[4].metric("Projects",   f"{cand['project_relevance']*100:.0f}%")
                s1, s2 = st.columns(2)
                s1.markdown("**✅ Matching Skills**")
                s1.markdown(skill_pills(cand.get("matching_skills", [])), unsafe_allow_html=True)
                s2.markdown("**⚠️ Missing Skills**")
                s2.markdown(skill_pills(cand.get("missing_skills", []), missing=True), unsafe_allow_html=True)

    # ── Tab 2: Analytics ──────────────────────────────────────────────────
    with tabs[1]:
        st.plotly_chart(ranking_bar_chart(ranked), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(similarity_distribution(ranked), use_container_width=True)
        with c2:
            st.plotly_chart(
                experience_bar(ranked, jd_min_exp=jd.get("min_experience_years", 0)),
                use_container_width=True,
            )

        # Skill frequency (fetch from stored resumes)
        all_skills = [r.get("skills", []) for r in resumes]
        freq: dict[str, int] = Counter()
        for skill_list in all_skills:
            for s in set(skill_list):
                freq[s] += 1
        st.plotly_chart(skill_frequency_chart(dict(freq)), use_container_width=True)

        # Skill gap analysis
        st.subheader("🔍 Skill Gap Analysis")
        jd_skills = set(jd.get("required_skills", []))
        pool_skills = set(s for sl in all_skills for s in sl)
        covered   = sorted(jd_skills & pool_skills)
        uncovered = sorted(jd_skills - pool_skills)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f"**✅ Covered ({len(covered)}/{len(jd_skills)})**")
            st.markdown(skill_pills(covered), unsafe_allow_html=True)
        with g2:
            st.markdown(f"**❌ Not in any resume ({len(uncovered)}/{len(jd_skills)})**")
            st.markdown(skill_pills(uncovered, missing=True), unsafe_allow_html=True)
