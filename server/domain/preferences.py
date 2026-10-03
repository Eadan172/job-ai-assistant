"""User-tunable scoring defaults.

Weights live in the user row so MatchAgent can read them later
without hard-coding a second copy.
"""

from __future__ import annotations

import hashlib
import json
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


def scoring_weights(preferences: dict[str, Any]) -> dict[str, float]:
    raw = preferences.get("weights") or {}
    weights = {name: float(raw.get(name, default)) for name, default in DEFAULT_WEIGHTS.items()}
    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        return dict(DEFAULT_WEIGHTS)
    return weights


def preferences_hash(preferences: dict[str, Any]) -> str:
    payload = {
        "weights": scoring_weights(preferences),
        "locations": list(preferences.get("locations") or []),
        "work_modes": list(preferences.get("work_modes") or []),
        "min_salary_k": preferences.get("min_salary_k"),
        "education": preferences.get("education"),
        "min_experience_years": preferences.get("min_experience_years"),
        "custom_requirements": list(preferences.get("custom_requirements") or []),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
