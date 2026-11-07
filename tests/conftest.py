import pytest

from tracker import database


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets a fresh, isolated database (the real one is never touched)."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()


@pytest.fixture
def make_app():
    from tracker.applications import add_application

    def _make(company="Google", job_title="Python Intern", applied_date="2026-11-01", **kw):
        return add_application(company, job_title, applied_date, **kw)

    return _make
