"""End-to-end UI test: drives the real Streamlit app (board, search, edit, delete)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from tracker.applications import add_application, get_application
from tracker.comparison import save_ratings
from tracker.interviews import add_interview, get_interviews

APP = Path(__file__).resolve().parent.parent / "app.py"


def test_full_ui_flow():
    a1 = add_application(
        "Google", "Python Intern", "2026-11-01", location="Cairo", job_type="Internship", work_mode="Remote"
    )
    a2 = add_application("Meta", "Data Intern", "2026-11-02")
    add_interview(a2, "2026-12-01T10:00:00", "HR")

    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception, at.exception

    at.sidebar.radio[0].set_value("📋 My Jobs Board").run()
    assert not at.exception, at.exception
    # move Google card from Applied -> Offer via its selector
    sb = [s for s in at.selectbox if s.key == f"mv_{a1}"][0]
    sb.set_value("Offer").run()
    assert not at.exception, at.exception
    assert get_application(a1)["status"] == "Offer", get_application(a1)["status"]
    at.text_input[0].set_value("meta").run()
    assert not at.exception and len([s for s in at.selectbox if s.key and s.key.startswith("mv_")]) == 1

    at.sidebar.radio[0].set_value("⚙️ Add & Manage").run()
    assert not at.exception, at.exception

    # --- edit form: change location + salary + status of Google (id a1) ---
    at.sidebar.radio[0].set_value("⚙️ Add & Manage").run()
    manage_sel = [s for s in at.selectbox if s.label == "Select an application:"][0]
    manage_sel.set_value("Meta - Data Intern").run()
    # Meta (a2) edit form: set salary, save
    sal = [t for t in at.text_input if t.label == "Salary" and t.value == ""]
    sal[-1].set_value("15000 EGP")
    [b for b in at.button if b.label == "Save changes"][0].click().run()
    assert not at.exception, at.exception
    assert get_application(a2)["salary"] == "15000 EGP", get_application(a2)

    # --- delete interview of Meta ---
    assert len(get_interviews(a2)) == 1
    [b for b in at.button if b.key and b.key.startswith("del_iv_")][0].click().run()
    assert not at.exception and len(get_interviews(a2)) == 0

    # --- delete application needs confirmation ---
    btn = [b for b in at.button if b.label == "Delete application"][0]
    assert btn.disabled
    [c for c in at.checkbox if c.key == f"confirm_del_{a2}"][0].check().run()
    [b for b in at.button if b.label == "Delete application"][0].click().run()
    assert get_application(a2) is None


def test_compare_page_renders():
    first = add_application("Delta Labs", "ML Engineer", "2026-11-01", status="Offer", salary="250000")
    save_ratings(first, learning=5, work_life=3, company=4, location=4)
    add_application("Cobalt Cloud", "DevOps Intern", "2026-11-02", status="Offer", salary="95000")

    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.sidebar.radio[0].set_value("⚖️ Compare").run()
    assert not at.exception, at.exception
    assert any("Compare" in m.value for m in at.markdown)

    pool = [r for r in at.radio if r.label == "Compare"][0]
    pool.set_value("Interview stage").run()  # an empty group shows a hint instead of crashing
    assert not at.exception, at.exception
