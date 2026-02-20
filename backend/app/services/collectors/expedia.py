import logging
import os

from apify_client import ApifyClient

from ...models import Hotel

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
ACTOR_ID = "jupri/expedia-hotels"

# The Expedia actor returns text labels instead of numeric scores.
# Map to midpoint of each label's typical range on a 1-10 scale.
LABEL_TO_SCORE = {
    "exceptional": 9.5,
    "wonderful": 9.0,
    "excellent": 8.5,
    "very good": 7.5,
    "good": 6.5,
    "ok": 5.5,
}


def collect_expedia_reviews(hotel: Hotel) -> tuple[float | None, int | None]:
    """Collect Expedia reviews via Apify scraper. Returns (score, count)."""
    if not APIFY_TOKEN:
        return None, None

    search_query = hotel.expedia_name or f"{hotel.name} {hotel.city} {hotel.state}"
    try:
        client = ApifyClient(APIFY_TOKEN)
        run = client.actor(ACTOR_ID).call(
            run_input={"location": [search_query], "limit": 5},
            timeout_secs=120,
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return None, None

        # Try to find a name match first; fall back to first result.
        match_name = (hotel.expedia_name or hotel.name).lower()
        item = next(
            (i for i in items if match_name in i.get("name", "").lower()),
            items[0],
        )

        count = item.get("reviews.total")
        label = (item.get("reviews.label") or "").lower()
        score = LABEL_TO_SCORE.get(label)

        if score is not None:
            return float(score), int(count) if count is not None else None

    except Exception:
        logger.exception("Failed to collect Expedia reviews for hotel %s", hotel.name)

    return None, None
