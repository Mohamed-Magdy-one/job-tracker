import pytest

from tracker.applications import (
    add_application,
    delete_application,
    get_all_applications,
    get_application,
    update_application,
)


def test_add_and_get(make_app):
    app_id = make_app(location="Remote", notes="hi")
    app = get_application(app_id)
    assert app["company"] == "Google"
    assert app["status"] == "Applied"
    assert app["location"] == "Remote"


def test_required_fields_are_validated():
    with pytest.raises(ValueError):
        add_application("  ", "Intern", "2026-11-01")


def test_invalid_status_rejected(make_app):
    with pytest.raises(ValueError):
        make_app(status="Hired")


def test_update_status_and_strip(make_app):
    app_id = make_app()
    assert update_application(app_id, status="Offer", company="  Meta ")
    app = get_application(app_id)
    assert app["status"] == "Offer" and app["company"] == "Meta"


def test_update_rejects_unknown_field_and_empty_company(make_app):
    app_id = make_app()
    with pytest.raises(ValueError):
        update_application(app_id, id=99)
    with pytest.raises(ValueError):
        update_application(app_id, company="  ")


def test_update_missing_returns_false():
    assert update_application(999, status="Offer") is False


def test_get_all_newest_first(make_app):
    make_app(company="Old", applied_date="2026-01-01")
    make_app(company="New", applied_date="2026-12-01")
    assert [a["company"] for a in get_all_applications()] == ["New", "Old"]


def test_delete(make_app):
    app_id = make_app()
    assert delete_application(app_id) is True
    assert get_application(app_id) is None


def test_filter_applications(make_app):
    from tracker.applications import filter_applications

    make_app(company="Google", job_title="Python Intern", location="Cairo", status="Applied")
    make_app(company="Meta", job_title="Data Intern", notes="referral", status="Offer")
    apps = get_all_applications()
    assert len(filter_applications(apps)) == 2
    assert [a["company"] for a in filter_applications(apps, "CAIRO")] == ["Google"]
    assert [a["company"] for a in filter_applications(apps, "referral")] == ["Meta"]
    assert [a["company"] for a in filter_applications(apps, statuses=["Offer"])] == ["Meta"]
    assert filter_applications(apps, "nothing") == []


def test_salary_is_formatted_with_thousands_separators(make_app):
    from tracker.applications import normalize_salary

    assert normalize_salary("90000") == "90,000"
    assert normalize_salary(" 1500000 ") == "1,500,000"
    assert normalize_salary("15,000 - 20,000 EGP") == "15,000 - 20,000 EGP"
    assert normalize_salary("") == "" and normalize_salary(None) is None

    app_id = make_app(salary="90000")
    assert get_application(app_id)["salary"] == "90,000"
    update_application(app_id, salary="120000")
    assert get_application(app_id)["salary"] == "120,000"
