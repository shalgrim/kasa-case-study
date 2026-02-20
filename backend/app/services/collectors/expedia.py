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
        logger.warning("APIFY_TOKEN not set — skipping Expedia collection for %s", hotel.name)
        return None, None

    # The actor's location parameter is a geographic location (city/region), not a hotel name.
    # Search by city+state so the actor can resolve the destination, then name-match.
    location_query = f"{hotel.city}, {hotel.state}" if hotel.city and hotel.state else hotel.name
    try:
        client = ApifyClient(APIFY_TOKEN)
        run = client.actor(ACTOR_ID).call(
            run_input={"location": [location_query], "limit": 5},
            timeout_secs=120,
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            logger.warning("Expedia: no results for %s", hotel.name)
            return None, None

        # The search returns nearby properties — find the right one by name.
        match_name = (hotel.expedia_name or hotel.name).lower()
        logger.info("Expedia: got %d results for '%s', looking for '%s': %s",
                    len(items), location_query, match_name,
                    [(i.get("name"), (i.get("reviews") or {}).get("label")) for i in items])
        # Match on first 2 words to handle name variations (e.g. "Hotel" vs "Resort")
        match_words = match_name.split()[:2]
        item = next(
            (i for i in items if all(w in i.get("name", "").lower() for w in match_words)),
            None,
        )
        if item is None:
            logger.warning("Expedia: no name match for '%s' in results, giving up", match_name)
            return None, None

        reviews = item.get("reviews") or {}
        count = reviews.get("total")
        label = (reviews.get("label") or "").lower()
        score = LABEL_TO_SCORE.get(label)
        if score is None:
            logger.warning("Expedia: unrecognized label '%s' for hotel %s", label, hotel.name)

        if score is not None:
            return float(score), int(count) if count is not None else None

    except Exception:
        logger.exception("Failed to collect Expedia reviews for hotel %s", hotel.name)

    return None, None
