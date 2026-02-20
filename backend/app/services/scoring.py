from ..models import ReviewSnapshot


def normalize_score(score: float | None, source: str) -> float | None:
    """Normalize score to 0-10 scale.
    Google/TripAdvisor: 1-5 scale -> multiply by 2
    Booking/Expedia: 1-10 scale -> use as-is
    """
    if score is None:
        return None
    if source in ("google", "tripadvisor"):
        return round(score * 2, 2)
    return round(score, 2)


def compute_scores(snapshot: ReviewSnapshot) -> None:
    """Compute normalized scores and weighted average for a snapshot."""
    snapshot.google_normalized = normalize_score(snapshot.google_score, "google")
    snapshot.booking_normalized = normalize_score(snapshot.booking_score, "booking")
    snapshot.expedia_normalized = normalize_score(snapshot.expedia_score, "expedia")
    snapshot.tripadvisor_normalized = normalize_score(
        snapshot.tripadvisor_score, "tripadvisor"
    )

    channels = [
        (snapshot.google_normalized, snapshot.google_count),
        (snapshot.booking_normalized, snapshot.booking_count),
        (snapshot.expedia_normalized, snapshot.expedia_count),
        (snapshot.tripadvisor_normalized, snapshot.tripadvisor_count),
    ]

    # For channels with a score but no review count, impute the count as the
    # average of the counts from channels that do have both.
    known_counts = [c for _, c in channels if c is not None and c > 0]
    avg_count = round(sum(known_counts) / len(known_counts)) if known_counts else 1

    weighted_sum = 0.0
    total_count = 0
    for norm_score, count in channels:
        if norm_score is not None:
            effective_count = count if count is not None and count > 0 else avg_count
            weighted_sum += norm_score * effective_count
            total_count += effective_count

    snapshot.weighted_average = (
        round(weighted_sum / total_count, 2) if total_count > 0 else None
    )
