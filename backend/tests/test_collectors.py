from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.collectors.booking import collect_booking_reviews
from app.services.collectors.expedia import collect_expedia_reviews


def _make_hotel(**kwargs):
    defaults = {"name": "Test Hotel", "city": "Portland", "state": "OR",
                "booking_name": None, "expedia_name": None}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---- Booking collector ----

class TestBookingCollector:
    def test_no_token_returns_none(self):
        with patch("app.services.collectors.booking.APIFY_TOKEN", ""):
            result = collect_booking_reviews(_make_hotel())
        assert result == (None, None)

    def test_success(self):
        hotel = _make_hotel()
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Test Hotel", "rating": 8.5, "reviews": 320}
        ]
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client):
            score, count = collect_booking_reviews(hotel)
        assert score == 8.5
        assert count == 320

    def test_name_matching_picks_correct_hotel(self):
        """Geo-based search may return nearby properties; prefer name match."""
        hotel = _make_hotel(name="Sea Crest Beach Hotel")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Backyard Chilling Cape Cod Home", "rating": 10, "reviews": 1},
            {"name": "Sea Crest Beach Hotel", "rating": 7.3, "reviews": 498},
        ]
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client):
            score, count = collect_booking_reviews(hotel)
        assert score == 7.3
        assert count == 498

    def test_empty_dataset(self):
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = []
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client):
            result = collect_booking_reviews(_make_hotel())
        assert result == (None, None)

    def test_exception_caught(self):
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", side_effect=RuntimeError("boom")):
            result = collect_booking_reviews(_make_hotel())
        assert result == (None, None)

    def test_falls_back_to_hotel_name_with_location(self):
        hotel = _make_hotel(booking_name=None, name="Fallback Hotel", city="Portland", state="OR")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Fallback Hotel", "rating": 7.0, "reviews": 100}
        ]
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client):
            collect_booking_reviews(hotel)
        call_args = mock_client.actor.return_value.call.call_args
        assert call_args.kwargs["run_input"]["search"] == "Fallback Hotel Portland OR"

    def test_booking_name_overrides_location_fallback(self):
        hotel = _make_hotel(booking_name="Exact Booking Name", name="Generic Hotel", city="Portland", state="OR")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Exact Booking Name", "rating": 8.0, "reviews": 50}
        ]
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client):
            collect_booking_reviews(hotel)
        call_args = mock_client.actor.return_value.call.call_args
        assert call_args.kwargs["run_input"]["search"] == "Exact Booking Name"


# ---- Expedia collector ----

class TestExpediaCollector:
    def test_no_token_returns_none(self):
        with patch("app.services.collectors.expedia.APIFY_TOKEN", ""):
            result = collect_expedia_reviews(_make_hotel())
        assert result == (None, None)

    def test_success(self):
        hotel = _make_hotel(name="Sea Crest Beach Resort")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Sea Crest Beach Resort", "reviews.label": "Very Good", "reviews.total": 251}
        ]
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            score, count = collect_expedia_reviews(hotel)
        assert score == 7.5
        assert count == 251

    def test_label_mapping(self):
        """Each known label maps to the expected score."""
        cases = [
            ("Exceptional", 9.5), ("Wonderful", 9.0), ("Excellent", 8.5),
            ("Very Good", 7.5), ("Good", 6.5), ("OK", 5.5),
        ]
        for label, expected_score in cases:
            hotel = _make_hotel(name="Hotel")
            mock_client = MagicMock()
            mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
            mock_client.dataset.return_value.iterate_items.return_value = [
                {"name": "Hotel", "reviews.label": label, "reviews.total": 100}
            ]
            with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
                 patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
                score, count = collect_expedia_reviews(hotel)
            assert score == expected_score, f"Label '{label}' should map to {expected_score}, got {score}"

    def test_unknown_label_returns_none(self):
        hotel = _make_hotel(name="Hotel")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Hotel", "reviews.label": "Unknown Label", "reviews.total": 50}
        ]
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            result = collect_expedia_reviews(hotel)
        assert result == (None, None)

    def test_empty_dataset(self):
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = []
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            result = collect_expedia_reviews(_make_hotel())
        assert result == (None, None)

    def test_exception_caught(self):
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", side_effect=RuntimeError("boom")):
            result = collect_expedia_reviews(_make_hotel())
        assert result == (None, None)

    def test_falls_back_to_hotel_name_with_location(self):
        hotel = _make_hotel(expedia_name=None, name="Fallback Hotel", city="Portland", state="OR")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Fallback Hotel", "reviews.label": "Excellent", "reviews.total": 200}
        ]
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            collect_expedia_reviews(hotel)
        call_args = mock_client.actor.return_value.call.call_args
        assert call_args.kwargs["run_input"]["location"] == ["Fallback Hotel Portland OR"]
        assert call_args.kwargs["run_input"]["limit"] == 5

    def test_name_matching_picks_correct_hotel(self):
        hotel = _make_hotel(name="Sea Crest Beach Resort")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"name": "Iris Hotel Cape Cod", "reviews.label": "Excellent", "reviews.total": 183},
            {"name": "Sea Crest Beach Resort", "reviews.label": "Very Good", "reviews.total": 251},
        ]
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            score, count = collect_expedia_reviews(hotel)
        assert score == 7.5
        assert count == 251
