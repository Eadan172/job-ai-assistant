"""Manual rematch and match reads. Scoring stays in MatchService."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.repositories.matches import JobMatchRepository
from db.session import session_scope
from services.event_hub import hub
from services.matching import MatchService, _public_match

router = APIRouter(prefix="/api")


class MatchRequest(BaseModel):
    resume_version_id: Optional[str] = None
    scoring_version: Optional[str] = None
    force: bool = False


@router.post("/jobs/{job_id}/match")
def post_match(job_id: str, body: MatchRequest) -> dict:
    try:
        with session_scope() as db:
            data = MatchService(db).run(
                job_id,
                resume_version_id=body.resume_version_id,
                scoring_version=body.scoring_version,
                force=body.force,
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    hub.publish(data["event"])
    return {
        "success": True,
        "data": {
            "job_id": data["job_id"],
            "match_id": data["match_id"],
            "status": data["status"],
            "score": data["score"],
        },
    }


@router.get("/jobs/{job_id}/match")
def get_match(job_id: str) -> dict:
    with session_scope() as db:
        row = JobMatchRepository(db).latest_for_job(job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="match not found")
        payload = _public_match(row)
    return {"success": True, "data": payload}


@router.get("/browse-sessions/{session_id}/jobs")
def list_session_jobs(session_id: str) -> dict:
    try:
        with session_scope() as db:
            payload = MatchService(db).list_session_jobs(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": payload}
