from tracker.database import db_session

def get_dashboard_stats():
    with db_session() as connection:
        stats = connection.execute("""
            SELECT
                COUNT(*) AS total_applications,
                SUM(CASE WHEN status = 'Applied' THEN 1 ELSE 0 END) AS applied,
                SUM(CASE WHEN status = 'Assessment' THEN 1 ELSE 0 END) AS assessments,
                SUM(CASE WHEN status = 'Interview' THEN 1 ELSE 0 END) AS interviews,
                SUM(CASE WHEN status = 'Offer' THEN 1 ELSE 0 END) AS offers,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN status = 'Withdrawn' THEN 1 ELSE 0 END) AS withdrawn
            FROM applications
        """).fetchone()

        result = dict(stats)
        total = result["total_applications"] or 0
        responded = (
            (result["assessments"] or 0) + (result["interviews"] or 0) +
            (result["offers"] or 0) + (result["rejected"] or 0)
        )
        result["response_rate"] = round((responded / total) * 100, 1) if total > 0 else 0
        return result

def get_status_distribution():
    with db_session() as connection:
        rows = connection.execute("""
            SELECT status, COUNT(*) AS count
            FROM applications
            GROUP BY status
            ORDER BY count DESC
        """).fetchall()
        return [dict(row) for row in rows]

def get_monthly_applications():
    with db_session() as connection:
        rows = connection.execute("""
            SELECT strftime('%Y-%m', applied_date) AS month, COUNT(*) AS total
            FROM applications
            GROUP BY month
            ORDER BY month
        """).fetchall()
        return [dict(row) for row in rows]

def get_recent_applications(limit=5):
    with db_session() as connection:
        rows = connection.execute("""
            SELECT id, company, job_title, status, applied_date
            FROM applications
            ORDER BY applied_date DESC, id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]

def get_upcoming_interviews(limit=5):
    with db_session() as connection:
        rows = connection.execute("""
            SELECT 
                i.id,
                i.interview_date,
                a.company,
                a.job_title,
                i.interview_type,
                i.meeting_link
            FROM interviews i
            JOIN applications a ON i.application_id = a.id
            WHERE datetime(i.interview_date) >= datetime('now', 'localtime')
            ORDER BY datetime(i.interview_date) ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]