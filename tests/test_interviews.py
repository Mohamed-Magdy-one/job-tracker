import pytest

from tracker.applications import delete_application, get_application
from tracker.interviews import add_interview, delete_interview, get_interviews


def test_add_interview_promotes_status(make_app):
    app_id = make_app()
    add_interview(app_id, "2026-11-10T10:00:00", "HR")
    assert get_application(app_id)["status"] == "Interview"
    assert len(get_interviews(app_id)) == 1


def test_interview_never_downgrades_offer(make_app):
    app_id = make_app(status="Offer")
    add_interview(app_id, "2026-11-10T10:00:00")
    assert get_application(app_id)["status"] == "Offer"


def test_interview_for_missing_application():
    with pytest.raises(ValueError):
        add_interview(999, "2026-11-10T10:00:00")


def test_delete_interview_and_cascade(make_app):
    app_id = make_app()
    interview_id = add_interview(app_id, "2026-11-10T10:00:00")
    assert delete_interview(interview_id) is True
    add_interview(app_id, "2026-11-11T10:00:00")
    delete_application(app_id)
    assert get_interviews(app_id) == []
