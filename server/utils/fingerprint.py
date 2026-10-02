"""Deterministic job identity.

A detail URL is trusted only when the path looks like a job page for a
known board. Search and list URLs fall back to company, title, salary,
and location so two different postings are not merged.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

_WHITESPACE = re.compile(r"\s+")
_DIGITS = re.compile(r"\d{3,}")


def normalize_text(value: str) -> str:
    return _WHITESPACE.sub(" ", (value or "").strip().lower())


def canonical_detail_url(source: str, url: str) -> Optional[str]:
    raw = (url or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    host = (parts.netloc or "").lower()
    if not host:
        return None
    path = parts.path or ""
    lowered = path.lower()
    site = f"{host} {(source or '').lower()}"
    if not _is_detail_path(site, lowered):
        return None
    scheme = "https" if parts.scheme.lower() in ("", "http", "https") else parts.scheme.lower()
    clean_path = path.rstrip("/") or "/"
    return urlunsplit((scheme, host, clean_path, "", ""))


def build_job_fingerprint(
    *,
    source: str,
    url: str,
    company: str,
    title: str,
    salary: str = "",
    location: str = "",
) -> tuple[str, Optional[str]]:
    canonical = canonical_detail_url(source, url)
    source_key = normalize_text(source)
    company_key = normalize_text(company)
    title_key = normalize_text(title)
    if canonical:
        material = [source_key, canonical, company_key, title_key]
    else:
        material = [
            source_key,
            company_key,
            title_key,
            normalize_text(salary),
            normalize_text(location),
        ]
    digest = hashlib.sha256("\n".join(material).encode("utf-8")).hexdigest()
    return digest, canonical


def _is_detail_path(site: str, path: str) -> bool:
    if any(token in site for token in ("zhipin", "boss")):
        return "job_detail" in path and path.rstrip("/").split("/")[-1] not in ("", "job_detail")
    if "lagou" in site or "拉勾" in site:
        return "/jobs/" in path and bool(_DIGITS.search(path))
    if "51job" in site or "前程" in site:
        blocked_51 = ("search", "joblist", "job-list")
        return bool(_DIGITS.search(path)) and not any(token in path for token in blocked_51)
    if "zhaopin" in site or "智联" in site:
        blocked_zhaopin = ("search", "joblist")
        detailed = "jobdetail" in path or "/job/" in path
        has_id = bool(_DIGITS.search(path))
        return detailed and has_id and not any(token in path for token in blocked_zhaopin)
    return False
