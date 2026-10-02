"""Job discovery events. Matching stays out of this phase."""

from fastapi import APIRouter, HTTPException

from db.session import session_scope
from domain.events import JobEventIn
from services.job_events import IncompleteJobError, JobEventService

router = APIRouter(prefix="/api")


@router.post("/jobs/events")
def post_job_event(body: JobEventIn) -> dict:
    try:
        with session_scope() as db:
            data = JobEventService(db).handle(body)
    except IncompleteJobError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "data": data}
