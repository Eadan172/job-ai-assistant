"""Hybrid match scoring.

Layer A records hard preference violations.
Layer B scores skills, duties, experience, education, location, salary, and other
preferences with local embeddings. The numeric score is fixed before any LLM runs.
"""

from __future__ import annotations

from typing import Optional

from domain.preferences import DEFAULT_WEIGHTS, scoring_weights
from domain.schemas import (
    EvidenceLink,
    ExperienceRange,
    JobJD,
    MatchResult,
    ResumeProfile,
    RiskFlag,
    SkillGap,
)
from llm.embeddings import HashEmbeddingProvider, canonical_skill, cosine, normalize_text, tokens

MATCHED = "MATCHED"
MISSING_REQUIRED = "MISSING_REQUIRED"
MISSING_PREFERRED = "MISSING_PREFERRED"
WEAK_EVIDENCE = "WEAK_EVIDENCE"
UNKNOWN = "UNKNOWN"
HIGH_PENALTY = 15.0
_MATCH_SIMILARITY = 0.82
_WEAK_SIMILARITY = 0.55

_EDU_RANK = {
    "初中": 1,
    "高中": 2,
    "中专": 2,
    "大专": 3,
    "专科": 3,
    "本科": 4,
    "学士": 4,
    "硕士": 5,
    "研究生": 5,
    "博士": 6,
}


class MatchAgent:
    def __init__(self, embedder: Optional[HashEmbeddingProvider] = None) -> None:
        self.embedder = embedder or HashEmbeddingProvider()

    def score(
        self,
        job: JobJD,
        profile: ResumeProfile,
        preferences: dict,
        *,
        scoring_version: str,
    ) -> MatchResult:
        weights = scoring_weights(preferences or {})
        resume_blobs = _resume_blobs(profile)
        gaps, skill_links = self._skills(job, resume_blobs)
        responsibilities, duty_links = self._responsibilities(job, profile)
        experience_score, experience_flags = _experience(job, profile, preferences)
        education_score, education_flags = _education(job, profile, preferences)
        location_score, location_flags = _location(job, preferences)
        salary_score, salary_flags = _salary(job, preferences)
        other_score = _other(job, preferences)
        dimensions = {
            "skills": _skill_dimension(gaps, set(job.required_skills), set(job.preferred_skills)),
            "responsibilities": _average([link.score for link in duty_links], empty=100.0),
            "experience": experience_score,
            "education": education_score,
            "location": location_score,
            "salary": salary_score,
            "other": other_score,
        }
        flags = experience_flags + education_flags + location_flags + salary_flags
        weighted = sum(dimensions[name] * weights.get(name, DEFAULT_WEIGHTS[name]) for name in DEFAULT_WEIGHTS)
        high = [flag for flag in flags if flag.severity == "high"]
        penalty = HIGH_PENALTY * len(high)
        overall = max(0.0, min(100.0, weighted - penalty))
        matched = [gap.name for gap in gaps if gap.status == MATCHED]
        missing = [gap.name for gap in gaps if gap.status == MISSING_REQUIRED]
        evidence = [link.resume for link in skill_links + duty_links if link.resume]
        return MatchResult(
            overall_score=round(overall, 1),
            dimension_scores={name: round(value, 1) for name, value in dimensions.items()},
            matched_skills=matched,
            missing_required_skills=missing,
            matched_responsibilities=responsibilities,
            evidence_from_resume=_unique(evidence),
            evidence_links=skill_links + duty_links,
            skill_gaps=gaps,
            risk_flags=flags,
            explanation=None,
            explanation_status="PENDING",
            model_version=None,
            scoring_version=scoring_version,
            hard_constraint_passed=not high,
            penalty_points=penalty,
        )

    def _skills(self, job: JobJD, blobs: list[tuple[str, str]]) -> tuple[list[SkillGap], list[EvidenceLink]]:
        gaps: list[SkillGap] = []
        links: list[EvidenceLink] = []
        pairs = [(name, MISSING_REQUIRED) for name in job.required_skills]
        pairs += [(name, MISSING_PREFERRED) for name in job.preferred_skills]
        for name, missing_status in pairs:
            similarity, quote = self._best(name, blobs)
            status = _gap_status(similarity, missing_status)
            gaps.append(SkillGap(name=name, status=status))
            if quote:
                links.append(
                    EvidenceLink(
                        jd=name,
                        resume=quote,
                        dimension="skills",
                        score=round(similarity, 4),
                        status=status,
                    )
                )
        return gaps, links

    def _responsibilities(self, job: JobJD, profile: ResumeProfile) -> tuple[list[str], list[EvidenceLink]]:
        blobs = []
        for item in profile.work_experiences:
            blobs.append((item.description or item.title, item.source_span or item.description))
        for project in profile.projects:
            blobs.append((project.description or project.name, project.source_span or project.description))
        matched: list[str] = []
        links: list[EvidenceLink] = []
        for duty in job.responsibilities:
            similarity, quote = self._best(duty, blobs)
            if similarity >= _WEAK_SIMILARITY and quote:
                matched.append(duty)
            links.append(
                EvidenceLink(
                    jd=duty,
                    resume=quote,
                    dimension="responsibilities",
                    score=round(similarity * 100, 1),
                    status=MATCHED if similarity >= _WEAK_SIMILARITY else MISSING_REQUIRED,
                )
            )
        return matched, links

    def _best(self, needle: str, blobs: list[tuple[str, str]]) -> tuple[float, str]:
        best = 0.0
        quote = ""
        left = self.embedder.embed_one(needle)
        folded = canonical_skill(needle)
        for text, source in blobs:
            target = text or ""
            if folded and folded in canonical_skill(target):
                return 1.0, source or target
            if not _shares_token(folded, target):
                continue
            similarity = cosine(left, self.embedder.embed_one(target))
            if similarity > best:
                best = similarity
                quote = source or target
        return best, quote


def _gap_status(similarity: float, missing_status: str) -> str:
    if similarity >= _MATCH_SIMILARITY:
        return MATCHED
    if similarity >= _WEAK_SIMILARITY:
        return WEAK_EVIDENCE
    return missing_status


def _skill_dimension(gaps: list[SkillGap], required_names: set[str], preferred_names: set[str]) -> float:
    required_rows = [gap for gap in gaps if gap.name in required_names]
    preferred_rows = [gap for gap in gaps if gap.name in preferred_names and gap.name not in required_names]
    if not required_rows and not preferred_rows:
        return 100.0
    required_avg = _average([_status_score(gap.status) for gap in required_rows], empty=100.0)
    if not preferred_rows:
        return required_avg
    preferred_avg = _average([_status_score(gap.status) for gap in preferred_rows], empty=100.0)
    if not required_rows:
        return preferred_avg
    return required_avg * 0.85 + preferred_avg * 0.15


def _status_score(status: str) -> float:
    if status == MATCHED:
        return 100.0
    if status == WEAK_EVIDENCE:
        return 60.0
    return 0.0


def _resume_blobs(profile: ResumeProfile) -> list[tuple[str, str]]:
    blobs: list[tuple[str, str]] = []
    for skill in profile.skills:
        text = " ".join([skill.name, skill.proficiency or "", *skill.evidence, skill.source_span or ""])
        blobs.append((text, skill.source_span or (skill.evidence[0] if skill.evidence else skill.name)))
    for item in profile.work_experiences:
        blobs.append((f"{item.title} {item.description}", item.source_span or item.description))
    for project in profile.projects:
        blobs.append((f"{project.name} {project.description}", project.source_span or project.description))
    return [(text, quote) for text, quote in blobs if text.strip()]


def _experience(
    job: JobJD,
    profile: ResumeProfile,
    preferences: dict,
) -> tuple[float, list[RiskFlag]]:
    required = _years(job.experience_years)
    actual = profile.years_of_experience
    if actual is None and preferences.get("min_experience_years") is not None:
        actual = float(preferences["min_experience_years"])
    if required is None:
        return 100.0, []
    if actual is None:
        return 50.0, [RiskFlag(type="EXPERIENCE_UNKNOWN", severity="low", detail="简历没有可确认的工作年限")]
    if actual + 1e-6 >= required:
        return 100.0, []
    score = max(0.0, 100.0 * actual / required)
    return score, [
        RiskFlag(
            type="EXPERIENCE_BELOW_REQUIREMENT",
            severity="high",
            detail=f"岗位要求约 {required:g} 年，简历约 {actual:g} 年",
        )
    ]


def _education(job: JobJD, profile: ResumeProfile, preferences: dict) -> tuple[float, list[RiskFlag]]:
    required = _highest_rank(job.education)
    owned = _highest_rank([item.degree for item in profile.education])
    if owned is None and preferences.get("education"):
        owned = _highest_rank([str(preferences["education"])])
    if required is None:
        return 100.0, []
    if owned is None:
        return 40.0, [RiskFlag(type="EDUCATION_UNKNOWN", severity="low", detail="简历没有学历")]
    if owned >= required:
        return 100.0, []
    return 40.0, [RiskFlag(type="EDUCATION_BELOW_REQUIREMENT", severity="high", detail="学历低于岗位要求")]


def _location(job: JobJD, preferences: dict) -> tuple[float, list[RiskFlag]]:
    wanted = [str(item) for item in preferences.get("locations") or [] if str(item).strip()]
    modes = [str(item) for item in preferences.get("work_modes") or [] if str(item).strip()]
    raw = job.location.city or job.location.raw or ""
    location_score = 100.0
    flags: list[RiskFlag] = []
    if wanted and not any(_place_match(item, raw) for item in wanted):
        location_score = 0.0
        flags.append(
            RiskFlag(
                type="LOCATION_MISMATCH",
                severity="high",
                detail=f"期望 {', '.join(wanted)}，岗位为 {raw or '未知'}",
            )
        )
    mode_score = 100.0
    job_mode = job.location.work_mode or ""
    if modes:
        if not job_mode:
            mode_score = 70.0
            flags.append(RiskFlag(type="WORK_MODE_UNKNOWN", severity="low", detail="岗位没有写工作模式"))
        elif not any(mode in job_mode or job_mode in mode for mode in modes):
            mode_score = 0.0
            flags.append(RiskFlag(type="WORK_MODE_MISMATCH", severity="high", detail=f"期望 {', '.join(modes)}"))
    if wanted and modes:
        return (location_score + mode_score) / 2, flags
    if modes and not wanted:
        return mode_score, flags
    return location_score, flags


def _salary(job: JobJD, preferences: dict) -> tuple[float, list[RiskFlag]]:
    floor = preferences.get("min_salary_k")
    if floor is None:
        return 100.0, []
    _low, high = parse_salary_k(job.salary.raw)
    if high is None:
        return 50.0, [RiskFlag(type="SALARY_UNKNOWN", severity="medium", detail="岗位薪资无法解析")]
    if high < float(floor):
        return 0.0, [
            RiskFlag(
                type="SALARY_BELOW_EXPECTATION",
                severity="high",
                detail=f"期望不低于 {floor:g}K，岗位上限约 {high:g}K",
            )
        ]
    return 100.0, []


def _other(job: JobJD, preferences: dict) -> float:
    requirements = [str(item) for item in preferences.get("custom_requirements") or [] if str(item).strip()]
    if not requirements:
        return 100.0
    haystack = normalize_text(job.full_text)
    hits = sum(1 for item in requirements if normalize_text(item) in haystack)
    return 100.0 * hits / len(requirements)


def _years(value: Optional[ExperienceRange]) -> Optional[float]:
    if value is None:
        return None
    if value.min_years is not None:
        return float(value.min_years)
    return parse_years(value.raw)


def parse_years(text: str) -> Optional[float]:
    if not text or "不限" in text:
        return None
    numbers = _numbers(text)
    if not numbers:
        return None
    return numbers[0]


def parse_salary_k(text: str) -> tuple[Optional[float], Optional[float]]:
    numbers = _numbers(text)
    if "薪" in text and len(numbers) >= 3 and numbers[-1] <= 24:
        numbers = numbers[:-1]
    if not numbers:
        return None, None
    if "万" in text:
        numbers = [number * 10 if number < 10 else number for number in numbers]
    low = min(numbers[0], numbers[1] if len(numbers) > 1 else numbers[0])
    high = max(numbers[0], numbers[1] if len(numbers) > 1 else numbers[0])
    return low, high


def _numbers(text: str) -> list[float]:
    found: list[float] = []
    current = ""
    for char in text or "":
        if char.isdigit() or (char == "." and current):
            current += char
            continue
        if current:
            found.append(float(current))
            current = ""
    if current:
        found.append(float(current))
    return found


def _highest_rank(values: list[str]) -> Optional[int]:
    ranks = []
    for value in values:
        for label, rank in _EDU_RANK.items():
            if label in (value or ""):
                ranks.append(rank)
    if not ranks:
        return None
    return max(ranks)


def _place_match(wanted: str, actual: str) -> bool:
    left = wanted.replace("市", "").strip()
    right = actual.replace("市", "").strip()
    return bool(left and right and (left in right or right in left))


def _shares_token(folded_skill: str, text: str) -> bool:
    if folded_skill and folded_skill in canonical_skill(text):
        return True
    skill_tokens = set(tokens(folded_skill))
    text_tokens = set(tokens(text))
    return bool(skill_tokens and skill_tokens & text_tokens)


def _average(values: list[float], *, empty: float) -> float:
    if not values:
        return empty
    return sum(values) / len(values)


def _unique(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
