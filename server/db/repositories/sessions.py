"""Browse sessions and the single local user."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.errors import InvalidTransition
from db.models import BrowseSession, User, utcnow
from domain.naming import format_session_label
from domain.preferences import DEFAULT_THRESHOLD, default_preferences

LOCAL_USER_ID = "local-user"

_TRANSITIONS = {
    "IDLE": {"ACTIVE", "FAILED"},
    "ACTIVE": {"FINALIZING", "FAILED"},
    "FINALIZING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": {"ACTIVE"},
}


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_local_user(self) -> User:
        user = self.db.get(User, LOCAL_USER_ID)
        if user is not None:
            return user
        user = User(
            id=LOCAL_USER_ID,
            display_name="本地用户",
            preferences=default_preferences(),
        )
        self.db.add(user)
        self.db.flush()
        return user

    def set_active_resume(self, user_id: str, resume_version_id: str) -> User:
        user = self.get_or_create_local_user() if user_id == LOCAL_USER_ID else self.db.get(User, user_id)
        if user is None:
            raise LookupError(f"user {user_id} not found")
        user.active_resume_version_id = resume_version_id
        user.updated_at = utcnow()
        self.db.flush()
        return user

    def update_preferences(self, user_id: str, preferences: dict) -> User:
        user = self.get_or_create_local_user() if user_id == LOCAL_USER_ID else self.db.get(User, user_id)
        if user is None:
            raise LookupError(f"user {user_id} not found")
        current = dict(user.preferences or {})
        current.update(preferences)
        user.preferences = current
        user.updated_at = utcnow()
        self.db.flush()
        return user


class BrowseSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, session_id: str) -> BrowseSession | None:
        return self.db.get(BrowseSession, session_id)

    def create(
        self,
        *,
        user_id: str,
        resume_version_id: str | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        when: datetime | None = None,
        origin: str | None = None,
    ) -> BrowseSession:
        moment = when or datetime.now(timezone.utc)
        row = BrowseSession(
            user_id=user_id,
            resume_version_id=resume_version_id,
            status="IDLE",
            label=self._next_label(moment),
            threshold=threshold,
            origin=origin,
            created_at=moment,
            updated_at=moment,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def transition(
        self,
        session_id: str,
        target: str,
        *,
        error_class: str | None = None,
    ) -> BrowseSession:
        row = self.get(session_id)
        if row is None:
            raise LookupError(f"browse session {session_id} not found")
        allowed = _TRANSITIONS.get(row.status, set())
        if target not in allowed:
            raise InvalidTransition(f"{row.status} cannot move to {target}")
        row.status = target
        row.updated_at = utcnow()
        if target == "ACTIVE" and row.started_at is None:
            row.started_at = row.updated_at
        if target == "COMPLETED":
            row.finalized_at = row.updated_at
        if target == "FAILED":
            row.error_class = error_class or "FAILED"
        self.db.flush()
        return row

    def set_resume(self, session_id: str, resume_version_id: str | None) -> BrowseSession:
        row = self.get(session_id)
        if row is None:
            raise LookupError(f"browse session {session_id} not found")
        row.resume_version_id = resume_version_id
        row.updated_at = utcnow()
        self.db.flush()
        return row

    def latest_active(self) -> BrowseSession | None:
        return (
            self.db.query(BrowseSession)
            .filter(BrowseSession.status == "ACTIVE")
            .order_by(BrowseSession.updated_at.desc())
            .first()
        )

    def _next_label(self, when: datetime) -> str:
        prefix = when.strftime("%Y%m%d")
        rows = self.db.query(BrowseSession.label).filter(BrowseSession.label.like(f"{prefix}-%")).all()
        highest = 0
        for (label,) in rows:
            suffix = str(label).rsplit("-", 1)[-1]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        return format_session_label(when, highest + 1)
