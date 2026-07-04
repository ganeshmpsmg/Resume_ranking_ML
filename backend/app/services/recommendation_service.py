"""
app/services/recommendation_service.py
----------------------------------------
Rule-based resume recommendation engine.

Generates ATS score prediction, strengths, weaknesses, and concrete
improvement suggestions from a RankedCandidate + raw resume text + JD data.
"""

from __future__ import annotations
import re
from app.schemas.schemas import RankedCandidate, FeedbackOut


def predict_ats_score(raw_text: str, sections: dict) -> tuple[float, dict]:
    """
    Heuristic ATS-friendliness score (0–100) based on:
      - Contact completeness   20 pts
      - Section coverage       30 pts
      - Skills richness        20 pts
      - Quantifiable content   15 pts
      - Resume length          15 pts
    """
    bd: dict[str, float] = {}

    # 1. Contact info
    has_email = bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw_text))
    has_phone = bool(re.search(r"\+?\d[\d\s\-().]{7,}\d", raw_text))
    bd["contact_info"] = (10 if has_email else 0) + (10 if has_phone else 0)

    # 2. Section coverage
    expected = ["education", "experience", "skills", "projects"]
    present = sum(1 for s in expected if sections.get(s))
    bd["section_coverage"] = round((present / len(expected)) * 30, 1)

    # 3. Skills richness
    skills_text = sections.get("skills", "")
    bd["skills_richness"] = min(20.0, round(len(skills_text.split()) / 2, 1))

    # 4. Quantifiable achievements
    hits = len(re.findall(r"\b\d+%|\b\d+\+|\$\d+|\b\d{2,}\b", raw_text))
    bd["quantifiable_achievements"] = min(15.0, float(hits * 2))

    # 5. Length appropriateness
    wc = len(raw_text.split())
    if 300 <= wc <= 1200:
        bd["length_appropriateness"] = 15.0
    elif wc < 300:
        bd["length_appropriateness"] = max(0.0, round(wc / 300 * 15, 1))
    else:
        bd["length_appropriateness"] = max(5.0, 15.0 - round((wc - 1200) / 200, 1))

    total = min(100.0, sum(bd.values()))
    return total, bd


def generate_rule_based_feedback(
    raw_text: str,
    sections: dict,
    ranked: RankedCandidate,
    jd_min_experience: float,
    jd_edu_rank: int,
) -> FeedbackOut:
    strengths:   list[str] = []
    weaknesses:  list[str] = []
    suggestions: list[str] = []

    # Semantic alignment
    if ranked.semantic_similarity >= 0.65:
        strengths.append(
            "Strong semantic alignment with the job description's language and responsibilities."
        )
    elif ranked.semantic_similarity < 0.40:
        weaknesses.append("Low overall semantic overlap with the job description.")
        suggestions.append(
            "Mirror the job description's terminology in your summary and bullet points."
        )

    # Skill match
    if ranked.skill_match >= 0.70:
        strengths.append(
            f"Covers {len(ranked.matching_skills)} of the JD's required skills."
        )
    if ranked.missing_skills:
        top_missing = ranked.missing_skills[:8]
        weaknesses.append(
            f"Missing {len(ranked.missing_skills)} required skill(s): "
            + ", ".join(top_missing)
            + ("…" if len(ranked.missing_skills) > 8 else "")
        )
        suggestions.append(
            "Add missing skills to your Skills section if you have experience with them, "
            "or include them naturally in project/experience descriptions."
        )

    # Experience
    if jd_min_experience > 0:
        if ranked.years_experience >= jd_min_experience:
            strengths.append(
                f"Meets the experience requirement "
                f"({ranked.years_experience} yrs ≥ {jd_min_experience} yrs required)."
            )
        else:
            weaknesses.append(
                f"Experience ({ranked.years_experience} yrs) below the "
                f"JD requirement ({jd_min_experience} yrs)."
            )
            suggestions.append(
                "Highlight internships, freelance work, and side projects to "
                "compensate for fewer formal years of employment."
            )

    # Education
    if jd_edu_rank > 0:
        if ranked.education_match >= 1.0:
            strengths.append("Education level meets or exceeds the job requirement.")
        else:
            weaknesses.append("Education level may be below the JD's stated requirement.")
            suggestions.append(
                "Mention relevant certifications or bootcamp training to "
                "offset education-level gaps."
            )

    # Projects
    if ranked.project_relevance >= 0.55:
        strengths.append("Projects section is highly relevant to the target role.")
    elif ranked.project_relevance < 0.30:
        weaknesses.append("Projects show limited relevance to this role.")
        suggestions.append(
            "Add 1–2 projects directly using the JD's core tech stack "
            "and link to a GitHub repo."
        )

    # ATS heuristics
    ats_score, ats_bd = predict_ats_score(raw_text, sections)
    if ats_bd.get("contact_info", 0) < 20:
        weaknesses.append("Incomplete contact information (missing email or phone).")
        suggestions.append("Place email and phone clearly at the top of the resume.")
    if ats_bd.get("section_coverage", 0) < 20:
        weaknesses.append("One or more standard sections (Education / Experience / Skills / Projects) are missing.")
        suggestions.append("Use clear, standard section headers so ATS parsers can segment your resume.")
    if ats_score < 50:
        suggestions.append(
            "Overall ATS score is low — avoid tables/graphics for key content; "
            "use plain text and standard fonts."
        )

    if not strengths:
        strengths.append("Resume parsed successfully; review detailed scores in the dashboard.")
    if not suggestions:
        suggestions.append(
            "Resume is already well-aligned — minor keyword tailoring is all that's needed."
        )

    return FeedbackOut(
        resume_id=ranked.resume_id,
        strengths=strengths,
        weaknesses=weaknesses,
        matching_skills=ranked.matching_skills,
        missing_skills=ranked.missing_skills,
        suggestions=suggestions,
        ats_score=round(ats_score, 1),
        ats_breakdown=ats_bd,
        llm_generated=False,
    )
