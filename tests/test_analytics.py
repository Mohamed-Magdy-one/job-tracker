from datetime import datetime, timedelta

from tracker.analytics import (
    get_dashboard_stats,
    get_monthly_applications,
    get_status_distribution,
    get_upcoming_interviews,
)
from tracker.interviews import add_interview


def test_empty_database_stats():
    stats = get_dashboard_stats()
    assert stats["total_applications"] == 0
    assert stats["response_rate"] == 0


def test_dashboard_stats_and_response_rate(make_app):
    make_app(status="Applied")
    make_app(status="Interview")
    make_app(status="Rejected")
    make_app(status="Withdrawn")
    stats = get_dashboard_stats()
    assert stats["total_applications"] == 4
    assert stats["interviews"] == 1
    assert stats["response_rate"] == 50.0  # Interview + Rejected out of 4


def test_status_distribution_and_monthly(make_app):
    make_app(applied_date="2026-10-05", status="Applied")
    make_app(applied_date="2026-11-05", status="Applied")
    assert get_status_distribution() == [{"status": "Applied", "count": 2}]
    assert get_monthly_applications() == [
        {"month": "2026-10", "total": 1}, {"month": "2026-11", "total": 1}
    ]


def test_upcoming_interviews_excludes_past_even_today(make_app):
    """Regression: ISO 'T' timestamps used to compare wrongly against 'now'."""
    app_id = make_app()
    now = datetime.now()
    add_interview(app_id, (now - timedelta(hours=2)).isoformat(), "Past")
    add_interview(app_id, (now + timedelta(hours=2)).isoformat(), "Future")
    upcoming = get_upcoming_interviews()
    assert [i["interview_type"] for i in upcoming] == ["Future"]
