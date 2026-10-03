"""Job discovery events. Matching runs only after the job commit."""

from fastapi import APIRouter, HTTPException

from db.session import session_scope
from domain.events import JobEventIn
from services.event_hub import hub
from services.job_events import IncompleteJobError, JobEventService
from services.match_queue import schedule_match

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
    job_id = data.get("job_id")
    if job_id and data.get("event_type") == "job.discovered":
        hub.publish(
            {
                "type": "JOB_SAVED",
                "job_id": job_id,
                "session_id": data.get("session_id"),
                "status": "SAVED",
            }
        )
        schedule_match(str(job_id), data.get("session_id"))
    return {"success": True, "data": data}
