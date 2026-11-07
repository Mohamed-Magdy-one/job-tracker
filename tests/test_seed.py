from tracker.analytics import get_upcoming_interviews
from tracker.applications import get_all_applications
from tracker.comparison import build_comparison
from tracker.seed import seed_demo_data


def test_seed_fills_empty_db_once():
    added = seed_demo_data()
    assert added == len(get_all_applications()) > 0
    assert seed_demo_data() == 0  # never duplicates or overwrites existing data
    assert len(get_upcoming_interviews()) == 2
    assert len(build_comparison(["Offer"])) == 2  # two offers to compare out of the box
