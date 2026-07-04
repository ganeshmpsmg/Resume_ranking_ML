"""
frontend/components/ui_components.py
--------------------------------------
Reusable Streamlit HTML components for consistent styling across pages.
"""

import streamlit as st

PRIMARY = "#2D5DA1"
ACCENT  = "#E07A3F"
SUCCESS = "#2E8B57"
WARNING = "#D4A017"
DANGER  = "#C0392B"


def inject_css() -> None:
    st.markdown(f"""
    <style>
      .main {{ background:#F6F7FA; }}
      .block-container {{ padding-top: 1.5rem; }}
      .metric-card {{
        background:white; border-radius:12px; padding:18px;
        border:1px solid #E5E7EB; margin-bottom:10px;
        box-shadow:0 1px 3px rgba(0,0,0,0.05);
      }}
      .candidate-card {{
        background:white; border-radius:12px; padding:18px 22px;
        border:1px solid #E5E7EB; margin-bottom:14px;
        box-shadow:0 1px 3px rgba(0,0,0,0.04);
      }}
      .rank-badge {{
        display:inline-block; background:{PRIMARY}; color:white;
        border-radius:50%; width:34px; height:34px; text-align:center;
        line-height:34px; font-weight:700; margin-right:10px;
      }}
      .skill-pill {{
        display:inline-block; background:#EAF1FB; color:{PRIMARY};
        padding:3px 10px; border-radius:14px; font-size:12.5px; margin:2px 4px 2px 0;
      }}
      .skill-missing {{
        display:inline-block; background:#FBEAEA; color:{DANGER};
        padding:3px 10px; border-radius:14px; font-size:12.5px; margin:2px 4px 2px 0;
      }}
      .conf-high   {{ color:{SUCCESS}; font-weight:600; }}
      .conf-medium {{ color:{WARNING}; font-weight:600; }}
      .conf-low    {{ color:{DANGER};  font-weight:600; }}
      .status-ok      {{ color:{SUCCESS}; }}
      .status-error   {{ color:{DANGER};  }}
    </style>
    """, unsafe_allow_html=True)


def skill_pills(skills: list[str], missing: bool = False) -> str:
    cls = "skill-missing" if missing else "skill-pill"
    if not skills:
        return "<i style='color:#aaa'>None</i>"
    return "".join(f'<span class="{cls}">{s}</span>' for s in skills)


def confidence_badge(label: str) -> str:
    cls = {"High": "conf-high", "Medium": "conf-medium", "Low": "conf-low"}.get(label, "")
    return f'<span class="{cls}">{label}</span>'


def score_bar(score_pct: float, color: str = PRIMARY) -> str:
    return (
        f'<div style="background:#EEE;border-radius:6px;height:8px;margin:4px 0;">'
        f'<div style="width:{score_pct:.0f}%;background:{color};height:8px;border-radius:6px;"></div>'
        f'</div>'
    )


def candidate_card(rank: int, candidate: dict) -> None:
    name       = candidate.get("name", "Unknown")
    filename   = candidate.get("filename", "")
    score      = candidate.get("final_score", 0) * 100
    confidence = candidate.get("confidence", "")
    exp        = candidate.get("years_experience", 0)
    edu        = candidate.get("education_level") or "N/A"

    st.markdown(f"""
    <div class="candidate-card">
      <span class="rank-badge">{rank}</span>
      <span style="font-size:17px;font-weight:700;">{name}</span>
      &nbsp; {confidence_badge(confidence)}
      <span style="float:right;font-size:21px;font-weight:800;color:{PRIMARY};">{score:.1f}%</span>
      <br><span style="color:#888;font-size:13px;">{filename} &nbsp;|&nbsp; {exp} yrs exp &nbsp;|&nbsp; {edu}</span>
      {score_bar(score)}
    </div>
    """, unsafe_allow_html=True)


def section_header(title: str, emoji: str = "") -> None:
    st.markdown(f"### {emoji} {title}" if emoji else f"### {title}")


def health_badge(ok: bool, label: str) -> str:
    icon  = "✅" if ok else "❌"
    color = SUCCESS if ok else DANGER
    return f'<span style="color:{color}">{icon} {label}</span>'
