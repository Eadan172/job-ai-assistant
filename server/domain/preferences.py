"""User-tunable scoring defaults.

Weights live in the user row so MatchAgent can read them later
without hard-coding a second copy.
"""

from __future__ import annotations

from typing import Any

SCORING_VERSION = "hybrid-v1"

DEFAULT_THRESHOLD = 70

DEFAULT_WEIGHTS = {
    "skills": 0.35,
    "responsibilities": 0.25,
    "experience": 0.15,
    "education": 0.10,
    "location": 0.05,
    "salary": 0.05,
    "other": 0.05,
}


def default_preferences() -> dict[str, Any]:
    return {
        "threshold": DEFAULT_THRESHOLD,
        "weights": dict(DEFAULT_WEIGHTS),
        "locations": [],
        "work_modes": [],
        "min_salary_k": None,
        "education": None,
        "min_experience_years": None,
        "custom_requirements": [],
    }
