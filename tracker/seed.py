"""Demo data loader: `python -m tracker.seed` (only fills an empty database)."""
from datetime import date, datetime, timedelta

from tracker.applications import add_application, get_all_applications
from tracker.comparison import save_ratings
from tracker.database import init_db
from tracker.interviews import add_interview

# company, title, days ago, status, location, work mode, salary
_DEMO = [
    ("Nile Tech", "Python Intern", 12, "Applied", "Cairo", "Remote", "90000"),
    ("Orbit Systems", "Data Science Intern", 10, "Assessment", "Giza", "Hybrid", "15000 - 20000 EGP"),
    ("Pixel Forge", "Backend Developer", 9, "Interview", "Cairo", "On-site", "120000"),
    ("Delta Labs", "ML Engineer", 21, "Offer", "Cairo", "On-site", "250000"),
    ("Sunrise Software", "QA Intern", 25, "Rejected", "Alexandria", "On-site", None),
    ("Cobalt Cloud", "DevOps Intern", 6, "Offer", "Remote", "Remote", "95000"),
    ("Lotus Analytics", "Data Analyst", 15, "Withdrawn", "Cairo", "Hybrid", "60000"),
    ("Falcon Apps", "Junior Python Developer", 3, "Applied", "Smart Village", "On-site", "75000"),
]


def seed_demo_data():
    """Insert sample applications if the database is empty. Returns how many were added."""
    init_db()
    if get_all_applications():
        return 0

    ids = []
    for company, title, days_ago, status, location, mode, salary in _DEMO:
        ids.append(add_application(
            company, title, (date.today() - timedelta(days=days_ago)).isoformat(),
            location=location, job_type="Internship" if "Intern" in title else "Full-time",
            work_mode=mode, salary=salary, status=status, job_url="https://example.com/careers"))

    def at(days, hour):
        moment = datetime.now() + timedelta(days=days)
        return moment.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")

    add_interview(ids[2], at(2, 14), "Technical", "https://meet.example.com/pixel-forge")
    add_interview(ids[1], at(5, 11), "HR")
    # personal 1-5 ratings: learning, work_life, company, location
    for index, scores in {3: (4, 2, 3, 3), 5: (4, 5, 4, 5), 2: (4, 3, 4, 3), 1: (4, 4, 3, 4)}.items():
        save_ratings(ids[index], learning=scores[0], work_life=scores[1], company=scores[2], location=scores[3])
    return len(ids)


if __name__ == "__main__":
    print(f"Added {seed_demo_data()} demo applications.")
