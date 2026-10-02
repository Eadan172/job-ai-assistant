"""Stable display names.

Session labels and evaluation titles are different on purpose.
A browse session is `20261002-001`. An evaluation is `26-10-02-JD-no.01`.
"""

from __future__ import annotations

import re
from datetime import datetime

_JD_NUMBER = re.compile(r"^JD-no\.\d{2,}$")


def format_jd_number(index: int) -> str:
    if index < 1:
        raise ValueError("JD index starts at 1")
    return f"JD-no.{index:02d}"


def format_session_label(when: datetime, sequence: int) -> str:
    if sequence < 1:
        raise ValueError("sequence starts at 1")
    return f"{when.strftime('%Y%m%d')}-{sequence:03d}"


def format_evaluation_title(when: datetime, jd_number: str) -> str:
    if not _JD_NUMBER.match(jd_number):
        raise ValueError("jd_number must look like JD-no.01")
    return f"{when.strftime('%y-%m-%d')}-{jd_number}"
