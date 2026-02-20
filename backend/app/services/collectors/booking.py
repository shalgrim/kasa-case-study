import logging
import os

from apify_client import ApifyClient

from ...models import Hotel

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
ACTOR_ID = "voyager/booking-scraper"

# Booking's autocomplete requires full state names, not abbreviations.
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def collect_booking_reviews(hotel: Hotel) -> tuple[float | None, int | None]:
    """Collect Booking.com reviews via Apify scraper. Returns (score, count)."""
    if not APIFY_TOKEN:
        logger.warning("APIFY_TOKEN not set — skipping Booking collection for %s", hotel.name)
        return None, None

    # Booking autocomplete requires full state names (not abbreviations) and no comma.
    if hotel.city and hotel.state:
        state_full = STATE_NAMES.get(hotel.state.upper(), hotel.state)
        location_query = f"{hotel.city} {state_full}"
    else:
        location_query = hotel.name
    try:
        client = ApifyClient(APIFY_TOKEN)
        run = client.actor(ACTOR_ID).call(
            run_input={
                "search": location_query,
                "maxItems": 5,
                "accommodationType": 204,  # hotels only (excludes vacation rentals)
            },
            timeout_secs=120,
        )

        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            logger.warning("Booking: no results for %s", hotel.name)
            return None, None

        # The search returns nearby properties — find the right one by name.
        match_name = (hotel.booking_name or hotel.name).lower()
        logger.info("Booking: got %d results for '%s', looking for '%s': %s",
                    len(items), location_query, match_name,
                    [i.get("name") for i in items])
        # Match on first 2 words to handle name variations (e.g. "Hotel" vs "Inn")
        match_words = match_name.split()[:2]
        item = next(
            (i for i in items if all(w in i.get("name", "").lower() for w in match_words)),
            None,
        )
        if item is None:
            logger.warning("Booking: no name match for '%s' in results, giving up", match_name)
            return None, None
        score = item.get("rating")
        count = item.get("reviews")

        if score is not None:
            return float(score), int(count) if count is not None else None

    except Exception:
        logger.exception("Failed to collect Booking reviews for hotel %s", hotel.name)

    return None, None
