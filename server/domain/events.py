"""Inbound job events from the extension."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RawJob(BaseModel):
    title: str = ""
    company: str = ""
    salary: str = ""
    location: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years: str = ""
    education: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    full_text: str = ""


class JobEventIn(BaseModel):
    event_id: str
    session_id: Optional[str] = None
    event_type: str
    source: str
    url: str
    captured_at: datetime
    raw_job: Optional[RawJob] = None
