"""
app/services/llm_service.py
-----------------------------
LLM-powered resume feedback (bonus feature).

Uses LangChain with the OpenAI chat model to generate rich, personalised
feedback comparing a candidate's resume to a job description.

Only active when settings.LLM_FEEDBACK_ENABLED is True (i.e. an
OPENAI_API_KEY is provided in the environment). All callers must check
this flag before calling generate_llm_feedback().
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging_config import get_logger
from app.schemas.schemas import FeedbackOut, RankedCandidate

logger = get_logger(__name__)

try:
    from langchain_community.chat_models import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from langchain.schema import HumanMessage, SystemMessage
    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False


_SYSTEM_PROMPT = """
You are a senior technical recruiter and career coach specialising in AI/ML roles.
You will be given a candidate's resume text and a job description.
Your task is to provide structured, actionable feedback in JSON format.

Respond ONLY with valid JSON matching this exact schema:
{
  "strengths": ["string", ...],
  "weaknesses": ["string", ...],
  "suggestions": ["string", ...],
  "overall_assessment": "string (2-3 sentences)"
}

Be specific, honest, and constructive. Reference actual content from the resume.
"""

_HUMAN_PROMPT = """
## Job Description
{jd_text}

## Candidate Resume
{resume_text}

## Score Summary
- Semantic Similarity: {semantic_sim:.0%}
- Skill Match: {skill_match:.0%}
- Experience Match: {exp_match:.0%}
- Education Match: {edu_match:.0%}
- Project Relevance: {proj_rel:.0%}
- Missing Skills: {missing_skills}

Provide detailed feedback on why this candidate does or does not fit this role.
"""


async def generate_llm_feedback(
    resume_id: str,
    resume_text: str,
    jd_text: str,
    ranked: RankedCandidate,
    base_feedback: FeedbackOut,
) -> FeedbackOut:
    """
    Generate LLM-augmented feedback. Enriches the rule-based FeedbackOut
    with LLM strengths/weaknesses/suggestions and an overall assessment.

    Falls back to the rule-based feedback gracefully on any LLM error.
    """
    if not settings.LLM_FEEDBACK_ENABLED:
        logger.warning("LLM feedback requested but OPENAI_API_KEY not set.")
        return base_feedback

    if not _HAS_LANGCHAIN:
        logger.warning("langchain not installed; returning rule-based feedback.")
        return base_feedback

    import json
    try:
        llm = ChatOpenAI(
            model_name=settings.OPENAI_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=1200,
        )

        human_text = _HUMAN_PROMPT.format(
            jd_text=jd_text[:3000],
            resume_text=resume_text[:3000],
            semantic_sim=ranked.semantic_similarity,
            skill_match=ranked.skill_match,
            exp_match=ranked.experience_match,
            edu_match=ranked.education_match,
            proj_rel=ranked.project_relevance,
            missing_skills=", ".join(ranked.missing_skills[:10]) or "None",
        )

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=human_text),
        ]

        response = await llm.ainvoke(messages)
        raw_content = response.content.strip()

        # Strip markdown fences if present
        if raw_content.startswith("```"):
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:]
        raw_content = raw_content.strip()

        llm_data = json.loads(raw_content)

        # Merge: LLM output enriches rule-based output
        merged = FeedbackOut(
            resume_id=resume_id,
            strengths=llm_data.get("strengths", base_feedback.strengths),
            weaknesses=llm_data.get("weaknesses", base_feedback.weaknesses),
            matching_skills=base_feedback.matching_skills,
            missing_skills=base_feedback.missing_skills,
            suggestions=llm_data.get("suggestions", base_feedback.suggestions),
            ats_score=base_feedback.ats_score,
            ats_breakdown=base_feedback.ats_breakdown,
            llm_generated=True,
            llm_feedback_text=llm_data.get("overall_assessment"),
        )
        logger.info(f"LLM feedback generated for resume {resume_id}")
        return merged

    except Exception as exc:
        logger.error(f"LLM feedback failed for {resume_id}: {exc}. Returning rule-based.")
        return base_feedback
