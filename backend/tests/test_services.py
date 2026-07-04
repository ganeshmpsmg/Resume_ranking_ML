"""
backend/tests/test_services.py
--------------------------------
Unit tests for core services — parser, skill extractor, JD processor,
ranking engine, evaluation metrics, recommendation engine.
These run without Postgres / Redis / Chroma (all external deps are mocked
or bypassed so the suite works in CI without Docker).
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

# ── Parser service ────────────────────────────────────────────────────────────

from app.services.parser_service import (
    detect_name, detect_contact_info, segment_sections,
    estimate_years_experience, detect_education_level,
)

SAMPLE_RESUME_TEXT = """
Ananya Sharma
ananya.sharma@example.com | +91-9876543210
linkedin.com/in/ananyasharma | github.com/ananyasharma

Summary
Machine Learning Engineer with 4 years of experience.

Education
M.Tech in Computer Science, IIT Bombay, 2020

Experience
ML Engineer, Flipkart (Jul 2021 - Present)
- Built semantic search using Sentence-BERT and FAISS

Skills
Python, PyTorch, TensorFlow, FAISS, AWS, Docker

Projects
Resume Ranking System using BERT embeddings
"""


class TestParser:
    def test_detect_name(self):
        name = detect_name(SAMPLE_RESUME_TEXT, "Ananya_Sharma_Resume.txt")
        assert name == "Ananya Sharma"

    def test_detect_email(self):
        info = detect_contact_info(SAMPLE_RESUME_TEXT)
        assert info["email"] == "ananya.sharma@example.com"

    def test_detect_phone(self):
        info = detect_contact_info(SAMPLE_RESUME_TEXT)
        assert info["phone"] is not None

    def test_detect_linkedin(self):
        info = detect_contact_info(SAMPLE_RESUME_TEXT)
        assert info["linkedin"] is not None

    def test_segment_sections(self):
        sections = segment_sections(SAMPLE_RESUME_TEXT)
        assert "education" in sections
        assert "experience" in sections
        assert "skills" in sections
        assert "projects" in sections

    def test_experience_years(self):
        text = "I have 4 years of experience in machine learning."
        years = estimate_years_experience(text)
        assert years == 4.0

    def test_experience_years_range(self):
        text = "Worked at Google from 2019 to 2023."
        years = estimate_years_experience(text)
        assert years >= 4.0

    def test_education_level_mtech(self):
        level, rank = detect_education_level(SAMPLE_RESUME_TEXT)
        assert rank >= 4  # M.Tech = 4

    def test_education_level_phd(self):
        _, rank = detect_education_level("PhD in Computer Science, IISc Bangalore")
        assert rank == 5

    def test_no_name_fallback(self):
        name = detect_name("no name here", "John_Doe_Resume.txt")
        assert "John" in name or name is not None


# ── Skill extraction ──────────────────────────────────────────────────────────

from app.services.skill_service import extract_skills, skill_match_score, skill_frequency


class TestSkillExtraction:
    def test_extract_known_skills(self):
        text = "Proficient in Python, PyTorch, TensorFlow, Docker and AWS."
        result = extract_skills(text)
        assert "Python" in result["all_skills"]
        assert "PyTorch" in result["all_skills"]
        assert "AWS" in result["all_skills"]

    def test_categorization(self):
        text = "Python, AWS, PostgreSQL, Pandas, PyTorch"
        result = extract_skills(text)
        cats = result["by_category"]
        assert "Programming Languages" in cats
        assert "Cloud / DevOps" in cats
        assert "Databases" in cats

    def test_case_insensitive(self):
        result = extract_skills("python tensorflow aws")
        assert "Python" in result["all_skills"]

    def test_skill_match_score_full(self):
        resume_skills = ["Python", "PyTorch", "AWS", "Docker"]
        jd_skills     = ["Python", "PyTorch"]
        result = skill_match_score(resume_skills, jd_skills)
        assert result["score"] == 1.0
        assert "Python" in result["matching"]
        assert result["missing"] == []

    def test_skill_match_score_partial(self):
        resume_skills = ["Python"]
        jd_skills     = ["Python", "PyTorch", "TensorFlow"]
        result = skill_match_score(resume_skills, jd_skills)
        assert 0 < result["score"] < 1.0
        assert len(result["missing"]) == 2

    def test_skill_match_empty_jd(self):
        result = skill_match_score(["Python"], [])
        assert result["score"] == 0.0

    def test_skill_frequency(self):
        lists = [["Python", "AWS"], ["Python", "Docker"], ["AWS"]]
        freq  = skill_frequency(lists)
        assert freq["Python"] == 2
        assert freq["AWS"] == 2
        assert freq["Docker"] == 1


# ── JD service ────────────────────────────────────────────────────────────────

from app.services.jd_service import process_jd

JD_TEXT = """
Machine Learning Engineer

We need an ML Engineer with 3+ years of experience.
Must have: Python, PyTorch, TensorFlow, AWS, Docker.
Bachelor's degree required; Master's preferred.
"""


class TestJDService:
    def test_title_extraction(self):
        jd = process_jd(JD_TEXT)
        assert "Machine Learning" in jd.title

    def test_skill_extraction(self):
        jd = process_jd(JD_TEXT)
        assert "Python" in jd.required_skills

    def test_min_experience(self):
        jd = process_jd(JD_TEXT)
        assert jd.min_experience_years == 3.0

    def test_education_extraction(self):
        jd = process_jd(JD_TEXT)
        assert jd.required_education_rank >= 3  # at least bachelor

    def test_source_field(self):
        jd = process_jd(JD_TEXT, source="linkedin")
        assert jd.source == "linkedin"


# ── Ranking components ────────────────────────────────────────────────────────

from app.services.ranking_service import (
    _experience_score, _education_score, _confidence,
)


class TestRankingComponents:
    def test_exp_meets_requirement(self):
        assert _experience_score(5.0, 3.0) == 1.0

    def test_exp_below_requirement(self):
        score = _experience_score(1.5, 3.0)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_exp_no_requirement(self):
        assert _experience_score(0.0, 0.0) == 1.0

    def test_edu_meets(self):
        assert _education_score(4, 3) == 1.0

    def test_edu_below(self):
        score = _education_score(2, 4)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_edu_no_requirement(self):
        assert _education_score(0, 0) == 1.0

    def test_confidence_high(self):
        assert _confidence(0.80) == "High"

    def test_confidence_medium(self):
        assert _confidence(0.60) == "Medium"

    def test_confidence_low(self):
        assert _confidence(0.30) == "Low"


# ── Evaluation metrics ────────────────────────────────────────────────────────

from app.services.evaluation_service import (
    precision_at_k, recall_at_k, mean_reciprocal_rank, evaluate,
)


class TestEvaluation:
    RANKED   = ["r1", "r2", "r3", "r4", "r5"]
    RELEVANT = {"r1", "r3"}

    def test_precision_at_1(self):
        assert precision_at_k(self.RANKED, self.RELEVANT, 1) == 1.0

    def test_precision_at_2(self):
        assert precision_at_k(self.RANKED, self.RELEVANT, 2) == 0.5

    def test_precision_at_5(self):
        assert precision_at_k(self.RANKED, self.RELEVANT, 5) == pytest.approx(0.4)

    def test_recall_at_2(self):
        assert recall_at_k(self.RANKED, self.RELEVANT, 2) == 0.5

    def test_recall_at_3(self):
        assert recall_at_k(self.RANKED, self.RELEVANT, 3) == 1.0

    def test_mrr_first_hit(self):
        assert mean_reciprocal_rank(self.RANKED, self.RELEVANT) == 1.0

    def test_mrr_no_hit(self):
        assert mean_reciprocal_rank(["x", "y"], self.RELEVANT) == 0.0

    def test_mrr_second(self):
        assert mean_reciprocal_rank(["x", "r1"], self.RELEVANT) == pytest.approx(0.5)

    def test_evaluate_full(self):
        result = evaluate(self.RANKED, self.RELEVANT, k_values=[1, 3, 5])
        assert "mrr" in result
        assert "precision@3" in result["metrics"]
        assert "recall@5" in result["metrics"]
        assert 0 <= result["mrr"] <= 1.0


# ── Recommendation service ────────────────────────────────────────────────────

from app.services.recommendation_service import predict_ats_score, generate_rule_based_feedback
from app.schemas.schemas import RankedCandidate


class TestRecommendation:
    def _make_candidate(self, **kwargs) -> RankedCandidate:
        defaults = dict(
            resume_id="r1", name="Test", filename="test.pdf",
            final_score=0.70, confidence="Medium",
            semantic_similarity=0.65, skill_match=0.60,
            experience_match=0.80, education_match=1.0, project_relevance=0.50,
            matching_skills=["Python", "PyTorch"],
            missing_skills=["TensorFlow"],
            extra_skills=["Excel"],
            years_experience=3.0, education_level="bachelor",
        )
        defaults.update(kwargs)
        return RankedCandidate(**defaults)

    def test_ats_score_range(self):
        score, bd = predict_ats_score(SAMPLE_RESUME_TEXT, {
            "education": "M.Tech...", "experience": "...", "skills": "Python PyTorch AWS",
            "projects": "Resume Ranking System"
        })
        assert 0 <= score <= 100

    def test_ats_has_breakdown_keys(self):
        _, bd = predict_ats_score(SAMPLE_RESUME_TEXT, {"skills": "Python AWS"})
        expected_keys = {"contact_info", "section_coverage", "skills_richness",
                         "quantifiable_achievements", "length_appropriateness"}
        assert expected_keys == set(bd.keys())

    def test_feedback_has_all_fields(self):
        cand = self._make_candidate()
        fb   = generate_rule_based_feedback(SAMPLE_RESUME_TEXT, {}, cand, 2.0, 3)
        assert fb.strengths
        assert isinstance(fb.weaknesses, list)
        assert isinstance(fb.suggestions, list)
        assert 0 <= fb.ats_score <= 100

    def test_feedback_identifies_missing_skills(self):
        cand = self._make_candidate(missing_skills=["TensorFlow", "Kubernetes"],
                                     skill_match=0.30)
        fb   = generate_rule_based_feedback(SAMPLE_RESUME_TEXT, {}, cand, 0.0, 0)
        combined = " ".join(fb.weaknesses + fb.suggestions)
        assert "TensorFlow" in combined or "missing" in combined.lower()

    def test_high_scorer_has_strengths(self):
        cand = self._make_candidate(semantic_similarity=0.80, skill_match=0.90,
                                     matching_skills=["Python","PyTorch","TensorFlow","AWS"],
                                     missing_skills=[])
        fb   = generate_rule_based_feedback(SAMPLE_RESUME_TEXT, {}, cand, 2.0, 3)
        assert len(fb.strengths) >= 1
