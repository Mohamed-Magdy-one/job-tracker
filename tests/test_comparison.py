import pytest

from tracker.applications import delete_application
from tracker.comparison import build_comparison, get_highlights, get_ratings, parse_salary, save_ratings

ALL3 = {"learning": 3, "work_life": 3, "company": 3, "location": 3}
ALL5 = {"learning": 5, "work_life": 5, "company": 5, "location": 5}


def test_parse_salary():
    assert parse_salary("90,000") == 90000
    assert parse_salary("15k") == 15000
    assert parse_salary("15,000 - 20,000 EGP") == 17500
    assert parse_salary("15-20k") == 17500
    assert parse_salary("EGP 1.5k") == 1500
    assert parse_salary("negotiable") is None and parse_salary("") is None and parse_salary(None) is None


def test_ratings_upsert_validation_and_cascade(make_app):
    app_id = make_app(status="Offer")
    save_ratings(app_id, **ALL3)
    save_ratings(app_id, learning=5, work_life=4, company=4, location=3)  # update, not duplicate
    assert len(get_ratings()) == 1 and get_ratings()[app_id]["learning"] == 5
    with pytest.raises(ValueError):
        save_ratings(app_id, **{**ALL3, "learning": 6})
    with pytest.raises(ValueError):
        save_ratings(app_id, learning=3)
    with pytest.raises(ValueError):
        save_ratings(999, **ALL3)
    delete_application(app_id)
    assert get_ratings() == {}


@pytest.mark.parametrize("weight, winner", [(1.0, "A"), (0.0, "B"), (0.5, "A")])
def test_salary_weight_changes_the_winner(make_app, weight, winner):
    save_ratings(make_app(company="A", status="Offer", salary="100000"), **ALL3)
    save_ratings(make_app(company="B", status="Offer", salary="50000"), **ALL5)
    assert build_comparison(["Offer"], weight)[0]["company"] == winner


def test_pool_filter_and_missing_data(make_app):
    make_app(company="Offer Co", status="Offer", salary="80000")
    make_app(company="Interview Co", status="Interview", salary="60000")
    make_app(company="Applied Co", status="Applied", salary="999999")
    assert [i["company"] for i in build_comparison(["Offer"])] == ["Offer Co"]
    assert {i["company"] for i in build_comparison(["Offer", "Interview"])} == {"Offer Co", "Interview Co"}

    items = build_comparison(["Offer", "Interview"], 0.5)
    assert all(i["overall_score"] is None for i in items)  # nothing rated yet
    by_salary = build_comparison(["Offer", "Interview"], 1.0)  # salary-only needs no ratings
    assert by_salary[0]["company"] == "Offer Co" and by_salary[0]["overall_score"] == 100


def test_highlights(make_app):
    rich = make_app(company="Rich", status="Offer", salary="200000")
    happy = make_app(company="Happy", status="Offer", salary="100000")
    save_ratings(rich, **ALL3)
    save_ratings(happy, **ALL5)
    top = get_highlights(build_comparison(["Offer"], 0.5))
    assert top["top_salary"]["company"] == "Rich"
    assert top["best_fit"]["company"] == "Happy"
    assert top["top_overall"]["company"] == "Rich"  # at 50/50: 0.5*1 + 0.5*0.6 = 80 beats 0.5*0.5 + 0.5*1 = 75
    assert get_highlights(build_comparison(["Offer"], 0.2))["top_overall"]["company"] == "Happy"  # fit matters more
    assert get_highlights([]) == {"top_salary": None, "best_fit": None, "top_overall": None}
