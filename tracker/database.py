
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DB_PATH = Path(os.getenv("JOB_TRACKER_DB", DATA_DIR / "job_tracker.db"))


def get_connection():
    """Create and return a database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


@contextmanager
def db_session():
    """Open a connection, commit on success, roll back on error, always close."""
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create database tables if they don't exist."""

    with db_session() as connection:

        # Applications table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                job_title TEXT NOT NULL,
                location TEXT,
                job_type TEXT,
                work_mode TEXT,
                salary TEXT,
                job_url TEXT,
                status TEXT NOT NULL DEFAULT 'Applied'
                    CHECK(status IN (
                        'Applied',
                        'Assessment',
                        'Interview',
                        'Offer',
                        'Rejected',
                        'Withdrawn'
                    )),
                applied_date TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Interviews table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                interview_date TEXT NOT NULL,
                interview_type TEXT,
                meeting_link TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (application_id)
                    REFERENCES applications(id)
                    ON DELETE CASCADE
            )
        """)

        # Personal 1-5 ratings used to compare offers
        connection.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                application_id INTEGER PRIMARY KEY,
                learning INTEGER NOT NULL CHECK(learning BETWEEN 1 AND 5),
                work_life INTEGER NOT NULL CHECK(work_life BETWEEN 1 AND 5),
                company INTEGER NOT NULL CHECK(company BETWEEN 1 AND 5),
                location INTEGER NOT NULL CHECK(location BETWEEN 1 AND 5),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (application_id)
                    REFERENCES applications(id)
                    ON DELETE CASCADE
            )
        """)

        # Indexes for faster searches
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_applications_status
            ON applications(status)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_applications_date
            ON applications(applied_date)
        """)



def test_connection():
    """Check if database tables were created."""

    with db_session() as connection:
        applications = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    print("Database tables:")
    for table in applications:
        print(f"- {table['name']}")


if __name__ == "__main__":
    init_db()
    test_connection()
