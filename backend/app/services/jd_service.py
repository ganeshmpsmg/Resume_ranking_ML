"""
app/services/jd_service.py
----------------------------
Job Description processor: extracts structured fields from raw JD text
(title, required skills, minimum experience, required education level).
Reuses the same skill extractor as the resume pipeline for consistency.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

from app.core.taxonomy import EDUCATION_RANKS
from app.utils.text_utils import clean_text
from app.services.skill_service import extract_skills

MIN_EXP_PATTERNS = [
    re.compile(r"(\d+)\s*\+?\s*(?:to|-)\s*(\d+)\s*years?", re.IGNORECASE),
    re.compile(r"(?:minimum|min\.?|at least)\s*(\d+)\s*\+?\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*\+\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*years?\s*(?:of)?\s*(?:relevant)?\s*experience", re.IGNORECASE),
]


@dataclass
class ParsedJD:
    raw_text: str = ""
    title: str = ""
    required_skills: list[str] = field(default_factory=list)
    skills_by_category: dict = field(default_factory=dict)
    min_experience_years: float = 0.0
    required_education: str | None = None
    required_education_rank: int = 0
    source: str = "custom"


def _extract_title(text: str) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) < 80:
            return line
    return "Untitled Position"


def _extract_min_experience(text: str) -> float:
    candidates: list[float] = []
    for pattern in MIN_EXP_PATTERNS:
        for m in pattern.finditer(text):
            nums = [float(g) for g in m.groups() if g and str(g).isdigit()]
            if nums:
                candidates.append(min(nums))
    return min(candidates) if candidates else 0.0


def _extract_education(text: str) -> tuple[str | None, int]:
    lowered = text.lower()
    best_level, best_rank = None, 0
    for keyword, rank in EDUCATION_RANKS.items():
        if keyword in lowered and rank > best_rank:
            best_level, best_rank = keyword, rank
    return best_level, best_rank


def process_jd(text: str, source: str = "custom") -> ParsedJD:
    raw = clean_text(text)
    skills_result = extract_skills(raw)
    edu_level, edu_rank = _extract_education(raw)

    return ParsedJD(
        raw_text=raw,
        title=_extract_title(raw),
        required_skills=skills_result["all_skills"],
        skills_by_category=skills_result["by_category"],
        min_experience_years=_extract_min_experience(raw),
        required_education=edu_level,
        required_education_rank=edu_rank,
        source=source,
    )
