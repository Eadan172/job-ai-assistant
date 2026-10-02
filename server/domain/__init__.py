"""Domain contracts shared by repositories and later agents."""

from domain.naming import format_evaluation_title, format_jd_number, format_session_label
from domain.preferences import SCORING_VERSION, default_preferences

__all__ = [
    "SCORING_VERSION",
    "default_preferences",
    "format_evaluation_title",
    "format_jd_number",
    "format_session_label",
]
