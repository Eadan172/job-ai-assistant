"""Run matching after the job transaction has committed."""

from __future__ import annotations

import os
import threading
from typing import Optional

from agents.resume_profile import StructuredClient
from db.session import session_scope
from services.event_hub import hub
from services.matching import MatchService

_profile_client: Optional[StructuredClient] = None
_explanation_client: Optional[StructuredClient] = None
_threads: list[threading.Thread] = []
_thread_lock = threading.Lock()


def configure_clients(
    profile_client: Optional[StructuredClient] = None,
    explanation_client: Optional[StructuredClient] = None,
) -> None:
    global _profile_client, _explanation_client
    _profile_client = profile_client
    _explanation_client = explanation_client


def schedule_match(job_id: str, browse_session_id: Optional[str] = None) -> None:
    if os.environ.get("JOB_AI_MATCH_DISABLED") == "1":
        return
    hub.publish({"type": "MATCH_QUEUED", "job_id": job_id, "session_id": browse_session_id, "status": "PENDING"})

    def run() -> None:
        hub.publish(
            {"type": "MATCH_PROCESSING", "job_id": job_id, "session_id": browse_session_id, "status": "PROCESSING"}
        )
        try:
            with session_scope() as db:
                outcome = MatchService(
                    db,
                    profile_client=_profile_client,
                    explanation_client=_explanation_client,
                ).run(job_id, browse_session_id=browse_session_id)
        except Exception as exc:
            hub.publish(
                {
                    "type": "MATCH_FAILED",
                    "job_id": job_id,
                    "session_id": browse_session_id,
                    "status": "FAILED",
                    "overall_score": None,
                    "error_class": type(exc).__name__,
                }
            )
            return
        hub.publish(outcome["event"])

    if os.environ.get("JOB_AI_MATCH_INLINE") == "1":
        run()
        return
    thread = threading.Thread(target=run, name=f"match-{job_id}", daemon=True)
    with _thread_lock:
        _threads.append(thread)
    thread.start()


def drain(timeout: float = 5) -> None:
    with _thread_lock:
        pending = list(_threads)
        _threads.clear()
    for thread in pending:
        thread.join(timeout)
