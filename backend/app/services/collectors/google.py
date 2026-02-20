import logging
import os

import httpx

from ...models import Hotel

logger = logging.getLogger(__name__)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


def collect_google_reviews(hotel: Hotel) -> tuple[float | None, int | None]:
    """Collect Google reviews via SerpAPI. Returns (score, count)."""
    if not SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not set — skipping Google collection for %s", hotel.name)
        return None, None

    query = f"{hotel.name} {hotel.city} {hotel.state} hotel"
    try:
        resp = httpx.get(
            "https://serpapi.com/search.json",
            params={
                "q": query,
                "engine": "google",
                "api_key": SERPAPI_KEY,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Try knowledge graph first
        kg = data.get("knowledge_graph", {})
        if kg:
            rating = kg.get("rating")
            reviews = kg.get("reviews")
            if rating is not None:
                count = int(reviews) if reviews else None
                return float(rating), count

        # Try local results
        local = data.get("local_results", [])
        if local:
            first = local[0]
            rating = first.get("rating")
            reviews = first.get("reviews")
            if rating is not None:
                return float(rating), int(reviews) if reviews else None

    except Exception:
        logger.exception("Failed to collect Google reviews for hotel %s", hotel.name)

    return None, None
