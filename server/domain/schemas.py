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


class ResumeSkill(BaseModel):
    name: str
    proficiency: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)
    source_span: Optional[str] = None


class WorkExperience(BaseModel):
    company: str = ""
    title: str = ""
    start: Optional[str] = None
    end: Optional[str] = None
    description: str = ""
    source_span: Optional[str] = None


class ProjectExperience(BaseModel):
    name: str = ""
    role: str = ""
    description: str = ""
    source_span: Optional[str] = None


class EducationRecord(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    source_span: Optional[str] = None


class Achievement(BaseModel):
    text: str
    source_span: Optional[str] = None


class ResumeProfile(BaseModel):
    summary: Optional[str] = None
    skills: list[ResumeSkill] = Field(default_factory=list)
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    projects: list[ProjectExperience] = Field(default_factory=list)
    education: list[EducationRecord] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    years_of_experience: Optional[float] = None


class RiskFlag(BaseModel):
    type: str
    severity: str
    detail: str = ""


class SkillGap(BaseModel):
    name: str
    status: str


class EvidenceLink(BaseModel):
    jd: str
    resume: str
    dimension: str
    score: float
    status: str = ""


class MatchExplanation(BaseModel):
    explanation: str


class MatchResult(BaseModel):
    overall_score: float
    dimension_scores: dict[str, float]
    matched_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_responsibilities: list[str] = Field(default_factory=list)
    evidence_from_resume: list[str] = Field(default_factory=list)
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    explanation: Optional[str] = None
    explanation_status: str = "SKIPPED"
    model_version: Optional[str] = None
    scoring_version: str
    hard_constraint_passed: bool = True
    penalty_points: float = 0


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
