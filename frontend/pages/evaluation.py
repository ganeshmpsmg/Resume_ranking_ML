"""frontend/pages/evaluation.py"""
import streamlit as st
from services.api_client import compute_metrics, list_resumes
from utils.charts import evaluation_metrics_chart


def render():
    st.title("📈 Ranking Evaluation")
    st.caption("Measure ranking quality with Precision@K, Recall@K, and MRR.")

    if "last_rank_result" not in st.session_state:
        st.warning("Run **📊 Rank & Dashboard** first to generate a ranking result.")
        return

    result   = st.session_state["last_rank_result"]
    ranked   = result.get("results", [])
    job_id   = result.get("ranking_job_id")
    resumes  = list_resumes()

    st.markdown(f"**Ranking Job ID:** `{job_id}`  |  **Candidates ranked:** {len(ranked)}")
    st.divider()

    # Ground-truth selection
    st.subheader("1️⃣ Mark Relevant Resumes (Ground Truth)")
    st.caption("Select resumes a human recruiter would shortlist for this role.")

    name_map = {r["resume_id"]: r["name"] for r in ranked}
    options  = [f"{r['name']} ({r['filename']})" for r in ranked]
    id_list  = [r["resume_id"] for r in ranked]

    selected_labels = st.multiselect("Relevant / shortlisted resumes", options)
    selected_ids    = [id_list[options.index(l)] for l in selected_labels]

    k_input  = st.text_input("K values (comma-separated)", value="3,5,10")
    try:
        k_values = [int(x.strip()) for x in k_input.split(",") if x.strip().isdigit()]
    except Exception:
        k_values = [3, 5, 10]

    if not selected_ids:
        st.info("Select at least one relevant resume above.")
        return

    if st.button("📐 Compute Metrics", type="primary"):
        with st.spinner("Computing evaluation metrics…"):
            metrics = compute_metrics(job_id, selected_ids, k_values)
        st.session_state["eval_metrics"] = metrics
        st.session_state["eval_k"]       = k_values

    if "eval_metrics" not in st.session_state:
        return

    metrics  = st.session_state["eval_metrics"]
    k_values = st.session_state["eval_k"]

    st.divider()
    st.subheader("2️⃣ Results")

    c1, c2, c3 = st.columns(3)
    c1.metric("MRR (Mean Reciprocal Rank)", f"{metrics['mrr']:.4f}")
    c2.metric("Avg Cosine Similarity",      f"{metrics['average_cosine_similarity']*100:.1f}%")
    c3.metric("Relevant Resumes Selected",  len(selected_ids))

    # Precision / Recall table
    import pandas as pd
    rows = []
    for k in k_values:
        rows.append({
            "K":            k,
            "Precision@K":  metrics["metrics"].get(f"precision@{k}", 0),
            "Recall@K":     metrics["metrics"].get(f"recall@{k}", 0),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.style.format({"Precision@K": "{:.4f}", "Recall@K": "{:.4f}"}),
                 use_container_width=True, hide_index=True)

    st.plotly_chart(
        evaluation_metrics_chart(metrics["metrics"], k_values),
        use_container_width=True,
    )

    st.divider()
    st.subheader("3️⃣ Ranked List vs Ground Truth")
    for i, r in enumerate(ranked, 1):
        is_relevant = r["resume_id"] in selected_ids
        icon = "✅" if is_relevant else "⬜"
        st.markdown(
            f"{icon} **#{i}** {r['name']} — Score: `{r['final_score']*100:.1f}%`"
            + (" ← **RELEVANT**" if is_relevant else "")
        )
