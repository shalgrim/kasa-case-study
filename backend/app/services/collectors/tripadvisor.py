import os

import httpx

from ...models import Hotel

TRIPADVISOR_KEY = os.getenv("TRIPADVISOR_KEY", "")
BASE_URL = "https://api.content.tripadvisor.com/api/v1"


def collect_tripadvisor_reviews(hotel: Hotel) -> tuple[float | None, int | None]:
    """Collect TripAdvisor reviews via Content API. Returns (score, count)."""
    if not TRIPADVISOR_KEY:
        return None, None

    search_query = hotel.tripadvisor_name or hotel.name
    try:
        # Step 1: Search for the hotel
        resp = httpx.get(
            f"{BASE_URL}/location/search",
            params={
                "key": TRIPADVISOR_KEY,
                "searchQuery": search_query,
                "category": "hotels",
                "language": "en",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        locations = data.get("data", [])
        if not locations:
            return None, None

        location_id = locations[0]["location_id"]

        # Step 2: Get location details
        resp = httpx.get(
            f"{BASE_URL}/location/{location_id}/details",
            params={"key": TRIPADVISOR_KEY, "language": "en"},
            timeout=15,
        )
        resp.raise_for_status()
        details = resp.json()

        rating = details.get("rating")
        num_reviews = details.get("num_reviews")

        if rating is not None:
            count = int(num_reviews.replace(",", "")) if num_reviews else None
            return float(rating), count

    except Exception:
        pass

    return None, None
