"""Persistence errors that callers can handle without parsing SQL text."""


class InvalidTransition(ValueError):
    """Raised when a browse session status change is not allowed."""
