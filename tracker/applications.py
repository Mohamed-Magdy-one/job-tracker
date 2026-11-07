
from tracker.database import db_session

# Allowed application statuses
VALID_STATUSES = [
    "Applied",
    "Assessment",
    "Interview",
    "Offer",
    "Rejected",
    "Withdrawn"
]

JOB_TYPES = ["Internship", "Full-time", "Part-time", "Freelance", "Contract"]
WORK_MODES = ["On-site", "Remote", "Hybrid"]


def normalize_salary(value):
    """Format plain numbers with thousands separators: '90000' -> '90,000'.

    Free text such as '15,000 - 20,000 EGP' is kept as typed (just trimmed)."""
    if not value or not str(value).strip():
        return value
    text = str(value).strip()
    digits = text.replace(",", "").replace(" ", "")
    return f"{int(digits):,}" if digits.isdigit() else text


def add_application(
    company,
    job_title,
    applied_date,
    location=None,
    job_type=None,
    work_mode=None,
    salary=None,
    job_url=None,
    status="Applied",
    notes=None
):
    """Add a new job application."""

    if not company.strip() or not job_title.strip():
        raise ValueError("Company and job title are required.")

    if status not in VALID_STATUSES:
        raise ValueError("Invalid application status.")

    salary = normalize_salary(salary)

    with db_session() as connection:
        cursor = connection.execute("""
            INSERT INTO applications (
                company,
                job_title,
                location,
                job_type,
                work_mode,
                salary,
                job_url,
                status,
                applied_date,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company.strip(),
            job_title.strip(),
            location,
            job_type,
            work_mode,
            salary,
            job_url,
            status,
            applied_date,
            notes
        ))

        return cursor.lastrowid


def get_all_applications():
    """Return all applications, newest first."""

    with db_session() as connection:
        rows = connection.execute("""
            SELECT *
            FROM applications
            ORDER BY applied_date DESC, id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def get_application(application_id):
    """Get one application by its ID."""

    with db_session() as connection:
        row = connection.execute("""
            SELECT *
            FROM applications
            WHERE id = ?
        """, (application_id,)).fetchone()

        return dict(row) if row else None


def update_application(application_id, **updates):
    """Update selected fields of an application."""

    allowed_fields = {
        "company",
        "job_title",
        "location",
        "job_type",
        "work_mode",
        "salary",
        "job_url",
        "status",
        "applied_date",
        "notes"
    }

    if not updates:
        raise ValueError("No updates provided.")

    for field in updates:
        if field not in allowed_fields:
            raise ValueError(f"Field cannot be updated: {field}")

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError("Invalid application status.")

    for field in ("company", "job_title"):
        if field in updates:
            value = updates[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} cannot be empty.")
            updates[field] = value.strip()

    if "salary" in updates:
        updates["salary"] = normalize_salary(updates["salary"])

    set_clause = ", ".join(
        f"{field} = ?" for field in updates
    )

    values = list(updates.values())
    values.append(application_id)

    with db_session() as connection:
        cursor = connection.execute(
            f"""
            UPDATE applications
            SET {set_clause},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values
        )

        return cursor.rowcount > 0


def delete_application(application_id):
    """Delete an application and its related interviews."""

    with db_session() as connection:
        cursor = connection.execute("""
            DELETE FROM applications
            WHERE id = ?
        """, (application_id,))

        return cursor.rowcount > 0


def filter_applications(applications, query="", statuses=None):
    """Filter application dicts by free-text query and an optional status list."""
    q = (query or "").strip().lower()
    fields = ("company", "job_title", "location", "notes")
    result = []
    for app in applications:
        if statuses is not None and app["status"] not in statuses:
            continue
        text = " ".join(str(app.get(f) or "") for f in fields).lower()
        if q in text:
            result.append(app)
    return result
