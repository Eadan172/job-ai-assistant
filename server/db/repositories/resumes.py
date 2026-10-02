"""Resume versions.

Tailored rows are new versions. The original text and hash stay as stored.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import ResumeVersion, TailoredResume


class ResumeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, resume_id: str) -> Optional[ResumeVersion]:
        return self.db.get(ResumeVersion, resume_id)

    def create_original(self, *, user_id: str, filename: str, content_text: str) -> ResumeVersion:
        text = _require_text(content_text)
        row = ResumeVersion(
            user_id=user_id,
            kind="original",
            filename=filename,
            content_text=text,
            content_hash=_hash_text(text),
            version=1,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def create_tailored(
        self,
        *,
        parent_id: str,
        job_id: str,
        content_text: str,
        browse_session_id: Optional[str] = None,
    ) -> ResumeVersion:
        parent = self.get(parent_id)
        if parent is None:
            raise LookupError(f"resume {parent_id} not found")
        text = _require_text(content_text)
        parent_text = parent.content_text
        parent_hash = parent.content_hash
        sibling_max = (
            self.db.query(func.max(ResumeVersion.version))
            .filter(ResumeVersion.parent_resume_id == parent.id)
            .scalar()
        )
        next_version = max(parent.version, sibling_max or 0) + 1
        child = ResumeVersion(
            user_id=parent.user_id,
            parent_resume_id=parent.id,
            job_id=job_id,
            kind="tailored",
            filename=parent.filename,
            content_text=text,
            content_hash=_hash_text(text),
            version=next_version,
            validator_status="DRAFT",
        )
        self.db.add(child)
        self.db.flush()
        self.db.add(
            TailoredResume(
                resume_version_id=child.id,
                job_id=job_id,
                parent_resume_id=parent.id,
                browse_session_id=browse_session_id,
                content_hash=child.content_hash,
                validator_status="DRAFT",
                keyword_coverage=[],
            )
        )
        self.db.flush()
        if parent.content_text != parent_text or parent.content_hash != parent_hash:
            raise RuntimeError("tailoring must not rewrite the parent resume")
        return child


def _require_text(content_text: str) -> str:
    if not content_text or not content_text.strip():
        raise ValueError("resume content is empty")
    return content_text


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
