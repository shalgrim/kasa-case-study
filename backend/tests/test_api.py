import os
import pytest
from tests.conftest import CSV_PATH


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_register_and_login(client):
    resp = client.post("/api/auth/register", json={"email": "user@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    resp = client.post("/api/auth/login", json={"email": "user@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    resp = client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    assert resp.status_code == 400


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "user2@test.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "user2@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_unauthorized_access(client):
    resp = client.get("/api/hotels")
    assert resp.status_code == 401


def test_authenticated_get(client, auth_token):
    resp = client.get("/api/hotels", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200


def test_csv_import(client, auth_token):
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV file not found")

    with open(CSV_PATH, "rb") as f:
        resp = client.post(
            "/api/hotels/import-csv",
            files={"file": ("reviews.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] > 90

    resp = client.get("/api/hotels", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    hotels = resp.json()
    assert len(hotels) > 90

    hotel_with_scores = next((h for h in hotels if h["latest_snapshot"] is not None), None)
    assert hotel_with_scores is not None
    assert hotel_with_scores["latest_snapshot"]["source"] == "csv_import"


def test_csv_import_scoring(client, auth_token):
    """Verify normalization and weighted average for a known hotel."""
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV file not found")

    with open(CSV_PATH, "rb") as f:
        client.post(
            "/api/hotels/import-csv",
            files={"file": ("reviews.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    resp = client.get("/api/hotels", headers={"Authorization": f"Bearer {auth_token}"})
    hotels = resp.json()

    # Sea Crest Beach Hotel — CSV row 3:
    # Google: 4.00 (1596), Booking: 7.30 (498), Expedia: 7.80 (1001), TripAdvisor: 3.55 (1607)
    sea_crest = next((h for h in hotels if "Sea Crest" in h["name"]), None)
    assert sea_crest is not None
    snap = sea_crest["latest_snapshot"]

    assert snap["google_score"] == 4.0
    assert snap["booking_score"] == 7.3
    assert snap["expedia_score"] == 7.8
    assert snap["tripadvisor_score"] == 3.55

    assert snap["google_count"] == 1596
    assert snap["booking_count"] == 498
    assert snap["expedia_count"] == 1001
    assert snap["tripadvisor_count"] == 1607

    # Normalized: Google 8.0, Booking 7.3, Expedia 7.8, TripAdvisor 7.1
    assert snap["google_normalized"] == 8.0
    assert snap["booking_normalized"] == 7.3
    assert snap["expedia_normalized"] == 7.8
    assert snap["tripadvisor_normalized"] == 7.1

    # Weighted average ≈ 7.58
    assert snap["weighted_average"] is not None
    assert 7.5 <= snap["weighted_average"] <= 7.7


def test_hotel_detail(client, auth_token):
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV file not found")

    with open(CSV_PATH, "rb") as f:
        client.post(
            "/api/hotels/import-csv",
            files={"file": ("reviews.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    resp = client.get("/api/hotels", headers={"Authorization": f"Bearer {auth_token}"})
    hotel_id = resp.json()[0]["id"]

    resp = client.get(f"/api/hotels/{hotel_id}", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == hotel_id


def test_hotel_history(client, auth_token):
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV file not found")

    with open(CSV_PATH, "rb") as f:
        client.post(
            "/api/hotels/import-csv",
            files={"file": ("reviews.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    resp = client.get("/api/hotels", headers={"Authorization": f"Bearer {auth_token}"})
    hotel_id = resp.json()[0]["id"]

    resp = client.get(f"/api/hotels/{hotel_id}/history", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
