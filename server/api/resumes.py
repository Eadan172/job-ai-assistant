"""Store the active resume and local matching preferences.

The existing /parse-resume route still only returns text.
"""

import hashlib
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.repositories.resumes import ResumeRepository
from db.repositories.sessions import LOCAL_USER_ID, UserRepository
from db.session import session_scope

router = APIRouter(prefix="/api")


class ResumeIn(BaseModel):
    filename: str = "resume.txt"
    content_text: str


class PreferencesIn(BaseModel):
    locations: Optional[list[str]] = None
    work_modes: Optional[list[str]] = None
    min_salary_k: Optional[float] = None
    education: Optional[str] = None
    min_experience_years: Optional[float] = None
    custom_requirements: Optional[list[str]] = None
    weights: Optional[dict[str, float]] = None
    threshold: Optional[float] = None


class LlmSettingsIn(BaseModel):
    model_type: str = "deepseek"
    api_key: str = Field(default="")


@router.post("/resumes")
def post_resume(body: ResumeIn) -> dict:
    text = body.content_text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="resume content is empty")
    with session_scope() as db:
        users = UserRepository(db)
        resumes = ResumeRepository(db)
        user = users.get_or_create_local_user()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        existing = resumes.find_original_by_hash(user_id=user.id, content_hash=digest)
        row = existing or resumes.create_original(user_id=user.id, filename=body.filename, content_text=text)
        users.set_active_resume(LOCAL_USER_ID, row.id)
        payload = {"id": row.id, "content_hash": row.content_hash, "reused": existing is not None}
    return {"success": True, "data": payload}


@router.get("/preferences")
def get_preferences() -> dict:
    with session_scope() as db:
        user = UserRepository(db).get_or_create_local_user()
        return {"success": True, "data": _public_preferences(user.preferences or {}, user.active_resume_version_id)}


@router.put("/preferences")
def put_preferences(body: PreferencesIn) -> dict:
    changes = body.model_dump(exclude_unset=True)
    with session_scope() as db:
        user = UserRepository(db).update_preferences(LOCAL_USER_ID, changes)
        payload = _public_preferences(user.preferences or {}, user.active_resume_version_id)
    return {"success": True, "data": payload}


@router.put("/settings/llm")
def put_llm_settings(body: LlmSettingsIn) -> dict:
    with session_scope() as db:
        UserRepository(db).update_preferences(
            LOCAL_USER_ID,
            {"llm": {"model_type": body.model_type, "api_key": body.api_key}},
        )
    return {"success": True, "data": {"model_type": body.model_type, "llm_configured": bool(body.api_key)}}


def _public_preferences(preferences: dict[str, Any], active_resume_version_id: Optional[str]) -> dict[str, Any]:
    public = {key: value for key, value in preferences.items() if key != "llm"}
    llm = preferences.get("llm") or {}
    public["llm_configured"] = bool(llm.get("api_key"))
    public["model_type"] = llm.get("model_type") or "deepseek"
    public["active_resume_version_id"] = active_resume_version_id
    return public
