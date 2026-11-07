from tracker.database import db_session


def add_interview(application_id, interview_date, interview_type=None, meeting_link=None, notes=None):
    """Add a new interview for a specific application."""

    with db_session() as connection:
        exists = connection.execute(
            "SELECT 1 FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        if not exists:
            raise ValueError(f"Application {application_id} does not exist.")

        cursor = connection.execute("""
            INSERT INTO interviews (
                application_id,
                interview_date,
                interview_type,
                meeting_link,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            application_id,
            interview_date,
            interview_type,
            meeting_link,
            notes
        ))

        # Move early-stage applications to 'Interview' (never downgrade an Offer/Rejected)
        connection.execute("""
            UPDATE applications
            SET status = 'Interview', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status IN ('Applied', 'Assessment')
        """, (application_id,))

        return cursor.lastrowid


def get_interviews(application_id):
    """Get all interviews for a specific application."""

    with db_session() as connection:
        rows = connection.execute("""
            SELECT *
            FROM interviews
            WHERE application_id = ?
            ORDER BY interview_date ASC
        """, (application_id,)).fetchall()

        return [dict(row) for row in rows]


def delete_interview(interview_id):
    """Delete an interview."""

    with db_session() as connection:
        cursor = connection.execute("""
            DELETE FROM interviews
            WHERE id = ?
        """, (interview_id,))

        return cursor.rowcount > 0