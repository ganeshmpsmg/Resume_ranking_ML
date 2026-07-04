"""frontend/pages/compare.py"""
import streamlit as st
from services.api_client import compare_resumes
from components.ui_components import skill_pills
from utils.charts import comparison_bar


def render():
    st.title("⚖️ Resume vs Resume Comparison")

    if "last_rank_result" not in st.session_state:
        st.warning("Run **📊 Rank & Dashboard** first.")
        return

    result  = st.session_state["last_rank_result"]
    ranked  = result.get("results", [])
    job_id  = result.get("ranking_job_id")

    if len(ranked) < 2:
        st.warning("Need at least 2 ranked candidates to compare.")
        return

    opts    = {f"#{i+1} {r['name']} ({r['filename']})": r for i, r in enumerate(ranked)}
    labels  = list(opts.keys())

    c1, c2 = st.columns(2)
    with c1:
        label_a = st.selectbox("Candidate A", labels, index=0)
    with c2:
        remaining = [l for l in labels if l != label_a]
        label_b   = st.selectbox("Candidate B", remaining, index=0)

    cand_a = opts[label_a]
    cand_b = opts[opts[label_a] != opts.get(label_b) and label_b or remaining[0]]
    cand_b = opts[label_b]

    if st.button("⚖️ Compare", type="primary"):
        with st.spinner("Comparing…"):
            comparison = compare_resumes(job_id, cand_a["resume_id"], cand_b["resume_id"])
        st.session_state["last_comparison"] = comparison

    if "last_comparison" not in st.session_state:
        return

    comp = st.session_state["last_comparison"]
    ca   = comp["candidate_a"]
    cb   = comp["candidate_b"]

    # Winner banner
    winner_name = ca["name"] if comp["winner_resume_id"] == ca["resume_id"] else cb["name"]
    st.success(f"🏆 **{winner_name}** has the higher overall match score.")

    st.plotly_chart(comparison_bar(ca, cb), use_container_width=True)

    # Score table
    import pandas as pd
    factors = ["final_score","semantic_similarity","skill_match",
               "experience_match","education_match","project_relevance"]
    labels_f = ["Final Score","Semantic","Skill","Experience","Education","Projects"]
    df = pd.DataFrame({
        "Factor":   labels_f,
        ca["name"]: [f"{ca[f]*100:.1f}%" for f in factors],
        cb["name"]: [f"{cb[f]*100:.1f}%" for f in factors],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Skill sets
    st.divider()
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"**Only {ca['name']}**")
        st.markdown(skill_pills(comp["only_a_skills"]), unsafe_allow_html=True)
    with s2:
        st.markdown("**Common Skills**")
        st.markdown(skill_pills(comp["common_skills"]), unsafe_allow_html=True)
    with s3:
        st.markdown(f"**Only {cb['name']}**")
        st.markdown(skill_pills(comp["only_b_skills"]), unsafe_allow_html=True)

    # Key facts
    st.divider()
    fc1, fc2 = st.columns(2)
    for col, cand in [(fc1, ca), (fc2, cb)]:
        col.markdown(f"**{cand['name']}**")
        col.markdown(f"- Experience: **{cand['years_experience']} yrs**")
        col.markdown(f"- Education: **{cand.get('education_level') or 'N/A'}**")
        col.markdown(f"- Confidence: **{cand['confidence']}**")
        col.markdown(f"- Missing skills: **{len(cand['missing_skills'])}**")
