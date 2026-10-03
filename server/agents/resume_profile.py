"""Turn resume plain text into a ResumeProfile.

PDF, DOCX, and TXT parsing stays in server/utils/resume_parser.py.
This agent only structures text that parser already extracted.
"""

from __future__ import annotations

from typing import Protocol, Type, TypeVar

from pydantic import BaseModel

from domain.schemas import ResumeProfile

T = TypeVar("T", bound=BaseModel)

PROFILE_SYSTEM = (
    "Extract a resume profile from the user text. "
    "Return one JSON object matching the schema. "
    "Copy only facts that appear in the text. "
    "Do not invent employers, dates, skills, or years. "
    "evidence and source_span must be short quotes from the resume. "
    "Use an empty list or null when the resume does not say it."
)


class StructuredClient(Protocol):
    def complete(self, schema: Type[T], *, system: str, user: str) -> T:
        """Return a validated model."""


class ResumeProfileAgent:
    def __init__(self, client: StructuredClient) -> None:
        self.client = client

    def extract(self, text: str) -> ResumeProfile:
        clipped = text[:8000]
        result = self.client.complete(ResumeProfile, system=PROFILE_SYSTEM, user=clipped)
        if not isinstance(result, ResumeProfile):
            return ResumeProfile.model_validate(result)
        return result
