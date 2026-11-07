"""Compare offers / interview-stage jobs: salary parsing, fit ratings and a combined score."""
import re

from tracker.database import db_session

# rating key -> label shown in the UI (each rated 1-5)
CRITERIA = {
    "learning": "Learning & growth",
    "work_life": "Work-life balance",
    "company": "Company & team",
    "location": "Location & commute",
}

_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kK])?")


def parse_salary(text):
    """Turn free-text salary into one number, or None if it has no number.

    '90,000' -> 90000, '15k' -> 15000, '15,000 - 20,000 EGP' -> 17500 (middle of the range).
    All compared salaries are assumed to share one currency and pay period.
    """
    if not text:
        return None
    values = [[float(n.replace(",", "")), bool(k)] for n, k in _NUMBER.findall(str(text))[:2]]
    if not values:
        return None
    if len(values) == 2 and values[1][1] and not values[0][1]:  # '15-20k' means 15k-20k
        values[0][1] = True
    numbers = [v * 1000 if k else v for v, k in values]
    return sum(numbers) / len(numbers)


def save_ratings(application_id, **scores):
    """Create or update the 1-5 ratings of an application (all criteria are required)."""
    if set(scores) != set(CRITERIA):
        raise ValueError(f"Ratings needed for: {', '.join(CRITERIA)}.")
    for name, value in scores.items():
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{name} must be a whole number from 1 to 5.")

    with db_session() as connection:
        if not connection.execute("SELECT 1 FROM applications WHERE id = ?", (application_id,)).fetchone():
            raise ValueError(f"Application {application_id} does not exist.")
        connection.execute("""
            INSERT INTO ratings (application_id, learning, work_life, company, location)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(application_id) DO UPDATE SET
                learning = excluded.learning, work_life = excluded.work_life,
                company = excluded.company, location = excluded.location,
                updated_at = CURRENT_TIMESTAMP
        """, (application_id, *(scores[name] for name in CRITERIA)))


def get_ratings():
    """Return {application_id: {criterion: score}} for every rated application."""
    with db_session() as connection:
        rows = connection.execute("SELECT * FROM ratings").fetchall()
    return {row["application_id"]: {name: row[name] for name in CRITERIA} for row in rows}


def _overall(salary_value, max_salary, fit, salary_weight):
    """0-100 score mixing salary (relative to the best one) and fit.

    Only the parts that matter (weight above 0) are required, otherwise the score is None.
    """
    if salary_weight > 0 and (salary_value is None or not max_salary):
        return None
    if salary_weight < 1 and fit is None:
        return None
    salary_part = salary_value / max_salary if salary_weight > 0 else 0
    fit_part = fit / 5 if salary_weight < 1 else 0
    return round(100 * (salary_weight * salary_part + (1 - salary_weight) * fit_part), 1)


def build_comparison(statuses, salary_weight=0.5):
    """Applications in the given statuses, with numeric salary, fit and overall score, best first."""
    placeholders = ",".join("?" * len(statuses))
    with db_session() as connection:
        rows = connection.execute(
            f"SELECT * FROM applications WHERE status IN ({placeholders})", list(statuses)
        ).fetchall()
    ratings = get_ratings()

    items = []
    for row in rows:
        item = dict(row)
        item["salary_value"] = parse_salary(item["salary"])
        item["ratings"] = ratings.get(item["id"])
        item["fit_score"] = round(sum(item["ratings"].values()) / len(CRITERIA), 2) if item["ratings"] else None
        items.append(item)

    salaries = [i["salary_value"] for i in items if i["salary_value"] is not None]
    max_salary = max(salaries) if salaries else None
    for item in items:
        item["overall_score"] = _overall(item["salary_value"], max_salary, item["fit_score"], salary_weight)

    items.sort(key=lambda i: (
        i["overall_score"] is None, -(i["overall_score"] or 0), -(i["salary_value"] or 0), i["company"].lower()
    ))
    return items


def get_highlights(items):
    """The item with the highest salary, the best fit and the best overall score (None if no data)."""
    def best(key):
        scored = [i for i in items if i[key] is not None]
        return max(scored, key=lambda i: i[key]) if scored else None

    return {"top_salary": best("salary_value"), "best_fit": best("fit_score"), "top_overall": best("overall_score")}
