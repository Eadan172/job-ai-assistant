from datetime import datetime, timezone

import pytest

from domain.naming import format_evaluation_title, format_jd_number, format_session_label
from domain.preferences import default_preferences
from domain.schemas import JobJD
from utils.fingerprint import build_job_fingerprint, canonical_detail_url


def test_weights_sum_to_one():
    prefs = default_preferences()
    other = default_preferences()
    prefs["threshold"] = 60
    prefs["weights"]["skills"] = 0
    assert other["threshold"] == 70
    assert other["weights"]["skills"] == 0.35
    assert abs(sum(default_preferences()["weights"].values()) - 1) < 1e-9


def test_names_follow_the_two_display_rules():
    moment = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    assert format_session_label(moment, 1) == "20261002-001"
    assert format_jd_number(1) == "JD-no.01"
    assert format_evaluation_title(moment, "JD-no.03") == "26-10-02-JD-no.03"
    with pytest.raises(ValueError):
        format_evaluation_title(moment, "03")


def test_detail_url_ignores_tracking_query():
    left, canonical_left = build_job_fingerprint(
        source="Boss直聘",
        url="https://www.zhipin.com/job_detail/abc123.html?ka=search",
        company="示例公司",
        title="Python 工程师",
    )
    right, canonical_right = build_job_fingerprint(
        source="boss直聘",
        url="http://www.zhipin.com/job_detail/abc123.html",
        company=" 示例公司 ",
        title="Python   工程师",
    )
    assert left == right
    assert canonical_left == canonical_right
    assert canonical_left == "https://www.zhipin.com/job_detail/abc123.html"


def test_list_page_uses_salary_and_location():
    assert canonical_detail_url("Boss直聘", "https://www.zhipin.com/web/geek/job?query=python") is None
    low, _ = build_job_fingerprint(
        source="Boss直聘",
        url="https://www.zhipin.com/web/geek/job?query=python",
        company="示例公司",
        title="Python 工程师",
        salary="20-30K",
        location="上海",
    )
    high, _ = build_job_fingerprint(
        source="Boss直聘",
        url="https://www.zhipin.com/web/geek/job?query=python",
        company="示例公司",
        title="Python 工程师",
        salary="30-40K",
        location="上海",
    )
    assert low != high


def test_known_board_detail_paths():
    assert canonical_detail_url("拉勾网", "https://www.lagou.com/wn/jobs/1234567.html")
    assert canonical_detail_url("前程无忧", "https://jobs.51job.com/shanghai/12345678.html")
    assert canonical_detail_url("智联招聘", "https://www.zhaopin.com/jobdetail/CC123456.htm")
    assert canonical_detail_url("Boss直聘", "https://www.zhipin.com/job_detail") is None


def test_job_jd_keeps_source_spans():
    moment = datetime(2026, 10, 2, tzinfo=timezone.utc)
    jd = JobJD(
        id="job-1",
        source="Boss直聘",
        url="https://www.zhipin.com/job_detail/abc.html",
        title="Python 工程师",
        company="示例公司",
        source_spans={"required_skills": ["熟悉 Python"]},
        captured_at=moment,
        normalized_at=moment,
    )
    restored = JobJD.model_validate(jd.model_dump())
    assert restored.source_spans["required_skills"] == ["熟悉 Python"]
