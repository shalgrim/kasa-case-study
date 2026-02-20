import logging
import os

from apify_client import ApifyClient

from ...models import Hotel

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
ACTOR_ID = "voyager/booking-scraper"


def collect_booking_reviews(hotel: Hotel) -> tuple[float | None, int | None]:
    """Collect Booking.com reviews via Apify scraper. Returns (score, count)."""
    if not APIFY_TOKEN:
        return None, None

    search_query = hotel.booking_name or hotel.name
    try:
        client = ApifyClient(APIFY_TOKEN)
        run = client.actor(ACTOR_ID).call(
            run_input={"search": search_query, "maxItems": 1},
            timeout_secs=120,
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return None, None

        item = items[0]
        score = item.get("rating") or item.get("score")
        count = item.get("reviewCount") or item.get("numberOfReviews")

        if score is not None:
            return float(score), int(count) if count is not None else None

    except Exception:
        logger.exception("Failed to collect Booking reviews for hotel %s", hotel.name)

    return None, None
