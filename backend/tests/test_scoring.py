from app.models import ReviewSnapshot
from app.services.scoring import compute_scores


def _make_snapshot(**kwargs):
    """Create a ReviewSnapshot with only the fields we care about."""
    snap = ReviewSnapshot(hotel_id=1, source="test")
    for k, v in kwargs.items():
        setattr(snap, k, v)
    return snap


def test_all_channels_with_counts():
    snap = _make_snapshot(
        google_score=4.0, google_count=100,
        booking_score=8.0, booking_count=200,
        expedia_score=9.0, expedia_count=300,
        tripadvisor_score=4.0, tripadvisor_count=400,
    )
    compute_scores(snap)
    assert snap.google_normalized == 8.0
    assert snap.booking_normalized == 8.0
    assert snap.expedia_normalized == 9.0
    assert snap.tripadvisor_normalized == 8.0
    # (8*100 + 8*200 + 9*300 + 8*400) / 1000 = 8.3
    assert snap.weighted_average == 8.3


def test_score_without_count_imputes_average():
    """A channel with a score but no count should use the avg count of other channels."""
    snap = _make_snapshot(
        google_score=4.0, google_count=None,
        tripadvisor_score=1.0, tripadvisor_count=2,
    )
    compute_scores(snap)
    # Google normalized=8.0, no count -> imputed as avg of known counts = 2
    # TripAdvisor normalized=2.0, count=2
    # (8.0*2 + 2.0*2) / 4 = 5.0
    assert snap.weighted_average == 5.0


def test_score_with_zero_count_imputes_average():
    """A channel with count=0 should be treated like missing count."""
    snap = _make_snapshot(
        google_score=4.0, google_count=0,
        booking_score=7.0, booking_count=100,
    )
    compute_scores(snap)
    # Google normalized=8.0, count=0 -> imputed as 100
    # Booking normalized=7.0, count=100
    # (8.0*100 + 7.0*100) / 200 = 7.5
    assert snap.weighted_average == 7.5


def test_all_channels_missing_counts():
    """If no channel has a count, impute count=1 for all."""
    snap = _make_snapshot(
        google_score=4.0, google_count=None,
        tripadvisor_score=3.0, tripadvisor_count=None,
    )
    compute_scores(snap)
    # Google norm=8.0 count=1, TA norm=6.0 count=1
    # (8+6)/2 = 7.0
    assert snap.weighted_average == 7.0


def test_no_scores_gives_none():
    snap = _make_snapshot()
    compute_scores(snap)
    assert snap.weighted_average is None


def test_channels_with_none_score_excluded():
    """Channels with no score should not affect the average."""
    snap = _make_snapshot(
        google_score=4.0, google_count=100,
        booking_score=None, booking_count=None,
        expedia_score=None, expedia_count=None,
    )
    compute_scores(snap)
    # Only Google: 8.0
    assert snap.weighted_average == 8.0
