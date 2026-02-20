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
        logger.warning("APIFY_TOKEN not set — skipping Booking collection for %s", hotel.name)
        return None, None

    # The actor's search parameter is a geographic location (city/region), not a hotel name.
    # Search by city+state so the autocomplete can resolve the destination, then name-match.
    location_query = f"{hotel.city}, {hotel.state}" if hotel.city and hotel.state else hotel.name
    try:
        client = ApifyClient(APIFY_TOKEN)
        run = client.actor(ACTOR_ID).call(
            run_input={"search": location_query, "maxItems": 5},
            timeout_secs=120,
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return None, None

        # The search returns nearby properties — find the right one by name.
        match_name = (hotel.booking_name or hotel.name).lower()
        item = next(
            (i for i in items if match_name in i.get("name", "").lower()),
            items[0],
        )
        score = item.get("rating")
        count = item.get("reviews")

        if score is not None:
            return float(score), int(count) if count is not None else None

    except Exception:
        logger.exception("Failed to collect Booking reviews for hotel %s", hotel.name)

    return None, None
