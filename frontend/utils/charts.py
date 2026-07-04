"""
frontend/utils/charts.py
--------------------------
Plotly chart builders for the analytics dashboard.
"""

from __future__ import annotations
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

PRIMARY = "#2D5DA1"
ACCENT  = "#E07A3F"
SUCCESS = "#2E8B57"
WARNING = "#D4A017"
DANGER  = "#C0392B"


def ranking_bar_chart(results: list[dict]) -> go.Figure:
    df = pd.DataFrame({
        "Candidate":   [r["name"] for r in results],
        "Final Score": [r["final_score"] * 100 for r in results],
        "Confidence":  [r["confidence"] for r in results],
    })
    fig = px.bar(
        df, x="Final Score", y="Candidate", color="Confidence", orientation="h",
        color_discrete_map={"High": SUCCESS, "Medium": WARNING, "Low": DANGER},
        title="Candidate Ranking by Final Score",
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), height=max(350, 32 * len(results)))
    return fig


def similarity_distribution(results: list[dict]) -> go.Figure:
    sims = [r["semantic_similarity"] * 100 for r in results]
    fig  = px.histogram(
        x=sims, nbins=15, labels={"x": "Semantic Similarity (%)"},
        title="Semantic Similarity Distribution",
        color_discrete_sequence=[PRIMARY],
    )
    fig.update_layout(bargap=0.1)
    return fig


def experience_bar(results: list[dict], jd_min_exp: float = 0.0) -> go.Figure:
    df = pd.DataFrame({
        "Candidate":          [r["name"] for r in results],
        "Years of Experience":[r["years_experience"] for r in results],
    }).sort_values("Years of Experience", ascending=False)
    fig = px.bar(df, x="Candidate", y="Years of Experience",
                  color_discrete_sequence=[ACCENT], title="Experience Comparison")
    if jd_min_exp > 0:
        fig.add_hline(y=jd_min_exp, line_dash="dash", line_color=DANGER,
                       annotation_text=f"Minimum Required ({jd_min_exp} yrs)")
    return fig


def skill_frequency_chart(freq: dict[str, int], top_n: int = 20) -> go.Figure:
    items = list(freq.items())[:top_n]
    if not items:
        return go.Figure()
    skills, counts = zip(*items)
    df = pd.DataFrame({"Skill": list(skills), "Candidates": list(counts)})
    fig = px.bar(df, x="Candidates", y="Skill", orientation="h",
                  color_discrete_sequence=[PRIMARY], title="Skill Frequency Across Candidates")
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig


def radar_chart(candidate: dict) -> go.Figure:
    factors = ["Semantic\nSimilarity", "Skill\nMatch", "Experience\nMatch",
                "Education\nMatch", "Project\nRelevance"]
    values  = [
        candidate["semantic_similarity"] * 100,
        candidate["skill_match"] * 100,
        candidate["experience_match"] * 100,
        candidate["education_match"] * 100,
        candidate["project_relevance"] * 100,
    ]
    fig = go.Figure(go.Scatterpolar(r=values, theta=factors, fill="toself",
                                     line_color=PRIMARY))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        showlegend=False, height=350,
        title="Score Breakdown",
    )
    return fig


def gauge_chart(score_pct: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_pct,
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar":  {"color": PRIMARY},
            "steps": [
                {"range": [0, 50],  "color": "#FBEAEA"},
                {"range": [50, 75], "color": "#FDF3DC"},
                {"range": [75, 100],"color": "#E6F4EA"},
            ],
            "threshold": {"line": {"color": DANGER, "width": 3}, "thickness": 0.75, "value": 75},
        },
    ))
    fig.update_layout(height=240, margin=dict(l=15, r=15, t=30, b=15))
    return fig


def comparison_bar(cand_a: dict, cand_b: dict) -> go.Figure:
    factors = ["Semantic Sim.", "Skill Match", "Experience",
               "Education", "Projects", "Final Score"]
    def vals(c):
        return [c["semantic_similarity"]*100, c["skill_match"]*100,
                c["experience_match"]*100,   c["education_match"]*100,
                c["project_relevance"]*100,  c["final_score"]*100]

    fig = go.Figure()
    fig.add_trace(go.Bar(name=cand_a["name"], x=factors, y=vals(cand_a), marker_color=PRIMARY))
    fig.add_trace(go.Bar(name=cand_b["name"], x=factors, y=vals(cand_b), marker_color=ACCENT))
    fig.update_layout(barmode="group", height=420, title="Head-to-Head Comparison")
    return fig


def evaluation_metrics_chart(metrics: dict, k_values: list[int]) -> go.Figure:
    rows = []
    for k in k_values:
        rows.append({"K": k, "Metric": f"Precision@{k}", "Score": metrics.get(f"precision@{k}", 0)})
        rows.append({"K": k, "Metric": f"Recall@{k}",    "Score": metrics.get(f"recall@{k}", 0)})
    df = pd.DataFrame(rows)
    fig = px.bar(df, x="K", y="Score", color="Metric", barmode="group",
                  color_discrete_sequence=[PRIMARY, ACCENT],
                  title="Precision & Recall @ K")
    return fig
