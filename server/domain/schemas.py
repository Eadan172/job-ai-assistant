"""Pydantic contracts for structured agent output.

These models are the schema later agents must fill.
Phase 1 only checks that they round-trip; no model is called here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Salary(BaseModel):
    raw: str = ""
    min_k: Optional[float] = None
    max_k: Optional[float] = None
    months: Optional[int] = None


class Location(BaseModel):
    raw: str = ""
    city: Optional[str] = None
    work_mode: Optional[str] = None


class ExperienceRange(BaseModel):
    raw: str = ""
    min_years: Optional[float] = None
    max_years: Optional[float] = None


class JobJD(BaseModel):
    id: str
    source: str
    url: str
    canonical_url: Optional[str] = None
    title: str
    company: str
    salary: Salary = Field(default_factory=Salary)
    location: Location = Field(default_factory=Location)
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years: Optional[ExperienceRange] = None
    education: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    full_text: str = ""
    source_spans: dict[str, list[str]] = Field(default_factory=dict)
    captured_at: datetime
    normalized_at: datetime


class ResumeSkillFact(BaseModel):
    name: str
    evidence: str


class ResumeProfile(BaseModel):
    skills: list[ResumeSkillFact] = Field(default_factory=list)
    experiences: list[dict[str, str]] = Field(default_factory=list)
    projects: list[dict[str, str]] = Field(default_factory=list)
    education: list[dict[str, str]] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    overall_score: float
    dimension_scores: dict[str, float]
    matched_skills: list[str]
    missing_required_skills: list[str]
    evidence_from_resume: list[str]
    risk_flags: list[str]
    explanation: str
    model_version: str
    scoring_version: str
    hard_constraint_passed: bool = True


class ResumeDraft(BaseModel):
    markdown: str
    keyword_coverage: list[dict[str, str]] = Field(default_factory=list)
    used_fact_ids: list[str] = Field(default_factory=list)


class ResumeCritique(BaseModel):
    status: str
    issues: list[str] = Field(default_factory=list)


class CommunicationEvaluation(BaseModel):
    session_title: str
    overall: float
    dimensions: dict[str, float]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missed_questions: list[str] = Field(default_factory=list)
    improvement_actions: list[str] = Field(default_factory=list)
    transcript_summary: str = ""
    evidence_messages: list[str] = Field(default_factory=list)
    model_version: str = ""
    created_at: datetime
