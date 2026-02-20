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
            {"rating": 8.5, "reviewCount": 320}
        ]
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client):
            score, count = collect_booking_reviews(hotel)
        assert score == 8.5
        assert count == 320

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

    def test_falls_back_to_hotel_name(self):
        hotel = _make_hotel(booking_name=None, name="Fallback Hotel")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"rating": 7.0, "reviewCount": 100}
        ]
        with patch("app.services.collectors.booking.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.booking.ApifyClient", return_value=mock_client) as mock_cls:
            collect_booking_reviews(hotel)
        call_args = mock_client.actor.return_value.call.call_args
        assert call_args.kwargs["run_input"]["search"] == "Fallback Hotel"


# ---- Expedia collector ----

class TestExpediaCollector:
    def test_no_token_returns_none(self):
        with patch("app.services.collectors.expedia.APIFY_TOKEN", ""):
            result = collect_expedia_reviews(_make_hotel())
        assert result == (None, None)

    def test_success(self):
        hotel = _make_hotel()
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"rating": 9.2, "reviewCount": 450}
        ]
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            score, count = collect_expedia_reviews(hotel)
        assert score == 9.2
        assert count == 450

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

    def test_falls_back_to_hotel_name(self):
        hotel = _make_hotel(expedia_name=None, name="Fallback Hotel")
        mock_client = MagicMock()
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds1"}
        mock_client.dataset.return_value.iterate_items.return_value = [
            {"rating": 8.0, "reviewCount": 200}
        ]
        with patch("app.services.collectors.expedia.APIFY_TOKEN", "tok"), \
             patch("app.services.collectors.expedia.ApifyClient", return_value=mock_client):
            collect_expedia_reviews(hotel)
        call_args = mock_client.actor.return_value.call.call_args
        assert call_args.kwargs["run_input"]["search"] == "Fallback Hotel"
