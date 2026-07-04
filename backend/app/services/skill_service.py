"""
app/services/skill_service.py
------------------------------
Extracts and categorises technical skills from resume/JD text using
a regex-compiled skill dictionary built from the master taxonomy.
"""

from __future__ import annotations
import re
from collections import defaultdict

from app.core.taxonomy import SKILL_LOOKUP, ALL_SKILLS_SORTED
from app.utils.text_utils import normalize_for_matching


def _build_skill_regex() -> re.Pattern:
    escaped = [re.escape(s) for s in ALL_SKILLS_SORTED]
    pattern = r"(?<![a-zA-Z0-9])(" + "|".join(escaped) + r")(?![a-zA-Z0-9])"
    return re.compile(pattern, re.IGNORECASE)


_SKILL_REGEX = _build_skill_regex()


def extract_skills(text: str) -> dict:
    """
    Return:
        all_skills   – deduplicated canonical list
        by_category  – {category: [skill, ...]}
    """
    if not text:
        return {"all_skills": [], "by_category": {}}

    normalized = normalize_for_matching(text)
    found: set[str] = set()
    for match in _SKILL_REGEX.finditer(normalized):
        found.add(match.group(0).lower().strip())

    by_category: dict[str, list[str]] = defaultdict(list)
    all_skills: list[str] = []

    for hit in found:
        if hit in SKILL_LOOKUP:
            canonical, category = SKILL_LOOKUP[hit]
            by_category[category].append(canonical)
            all_skills.append(canonical)

    for cat in by_category:
        by_category[cat] = sorted(set(by_category[cat]))

    return {
        "all_skills": sorted(set(all_skills)),
        "by_category": dict(by_category),
    }


def skill_match_score(
    resume_skills: list[str], jd_skills: list[str]
) -> dict:
    """
    Returns matching, missing, extra skills and a normalised score [0,1].
    """
    resume_set = {s.lower() for s in resume_skills}
    jd_set = {s.lower() for s in jd_skills}

    if not jd_set:
        return {"score": 0.0, "matching": [], "missing": [], "extra": list(resume_skills)}

    matching_lower = resume_set & jd_set
    missing_lower  = jd_set - resume_set
    extra_lower    = resume_set - jd_set

    def _to_canonical(lower_set: set, source: list) -> list[str]:
        lkp = {s.lower(): s for s in source}
        return sorted(lkp[l] for l in lower_set if l in lkp)

    return {
        "score":    round(len(matching_lower) / len(jd_set), 4),
        "matching": _to_canonical(matching_lower, jd_skills),
        "missing":  _to_canonical(missing_lower,  jd_skills),
        "extra":    _to_canonical(extra_lower,     resume_skills),
    }


def skill_frequency(skill_lists: list[list[str]]) -> dict[str, int]:
    """Aggregate skill frequency counts across a resume batch."""
    freq: dict[str, int] = defaultdict(int)
    for skills in skill_lists:
        for s in set(skills):
            freq[s] += 1
    return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))
