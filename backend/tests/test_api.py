import os
from unittest.mock import patch

import pytest
from app.models import User
from tests.conftest import CSV_PATH, TestSession, count_queries


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

    resp = client.get("/api/hotels", params={"page_size": 500}, headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    hotels = resp.json()["items"]
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

    resp = client.get("/api/hotels", params={"page_size": 500}, headers={"Authorization": f"Bearer {auth_token}"})
    hotels = resp.json()["items"]

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

    resp = client.get("/api/hotels", params={"page_size": 500}, headers={"Authorization": f"Bearer {auth_token}"})
    hotel_id = resp.json()["items"][0]["id"]

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

    resp = client.get("/api/hotels", params={"page_size": 500}, headers={"Authorization": f"Bearer {auth_token}"})
    hotel_id = resp.json()["items"][0]["id"]

    resp = client.get(f"/api/hotels/{hotel_id}/history", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---- Group CRUD tests ----

def _import_csv(client, auth_token):
    """Helper: import CSV and return list of hotel IDs."""
    if not os.path.exists(CSV_PATH):
        pytest.skip("CSV file not found")
    with open(CSV_PATH, "rb") as f:
        client.post(
            "/api/hotels/import-csv",
            files={"file": ("reviews.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    resp = client.get("/api/hotels", params={"page_size": 500}, headers={"Authorization": f"Bearer {auth_token}"})
    return [h["id"] for h in resp.json()["items"]]


def test_create_group(client, auth_token):
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.post("/api/groups", json={"name": "Test Group", "hotel_ids": hotel_ids[:3]}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Group"
    assert data["hotel_count"] == 3
    assert "id" in data


def test_list_groups(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Empty initially
    resp = client.get("/api/groups", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Create one, then list
    hotel_ids = _import_csv(client, auth_token)
    client.post("/api/groups", json={"name": "G1", "hotel_ids": hotel_ids[:2]}, headers=headers)
    client.post("/api/groups", json={"name": "G2", "hotel_ids": []}, headers=headers)

    resp = client.get("/api/groups", headers=headers)
    assert resp.status_code == 200
    groups = resp.json()
    assert len(groups) == 2
    names = {g["name"] for g in groups}
    assert names == {"G1", "G2"}


def test_get_group_detail(client, auth_token):
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.post("/api/groups", json={"name": "Detail Group", "hotel_ids": hotel_ids[:2]}, headers=headers)
    group_id = resp.json()["id"]

    resp = client.get(f"/api/groups/{group_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Group"
    assert len(data["hotels"]) == 2
    # Each hotel should have score fields
    h = data["hotels"][0]
    assert "name" in h
    assert "weighted_average" in h


def test_update_group(client, auth_token):
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.post("/api/groups", json={"name": "Old Name", "hotel_ids": hotel_ids[:2]}, headers=headers)
    group_id = resp.json()["id"]

    # Rename
    resp = client.put(f"/api/groups/{group_id}", json={"name": "New Name"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["hotel_count"] == 2

    # Change membership
    resp = client.put(f"/api/groups/{group_id}", json={"hotel_ids": hotel_ids[:5]}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["hotel_count"] == 5


def test_delete_group(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.post("/api/groups", json={"name": "To Delete", "hotel_ids": []}, headers=headers)
    group_id = resp.json()["id"]

    resp = client.delete(f"/api/groups/{group_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Verify gone
    resp = client.get(f"/api/groups/{group_id}", headers=headers)
    assert resp.status_code == 404


def test_export_hotels_csv(client, auth_token):
    _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.get("/api/export/hotels", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Name" in resp.text  # header row


def test_export_group_csv(client, auth_token):
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.post("/api/groups", json={"name": "Export Group", "hotel_ids": hotel_ids[:3]}, headers=headers)
    group_id = resp.json()["id"]

    resp = client.get(f"/api/export/groups/{group_id}", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


def test_group_user_isolation(client):
    """User A's groups are invisible to User B."""
    # Register two users
    resp_a = client.post("/api/auth/register", json={"email": "a@test.com", "password": "pass123"})
    token_a = resp_a.json()["access_token"]
    resp_b = client.post("/api/auth/register", json={"email": "b@test.com", "password": "pass123"})
    token_b = resp_b.json()["access_token"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a group
    resp = client.post("/api/groups", json={"name": "A's Group", "hotel_ids": []}, headers=headers_a)
    group_id = resp.json()["id"]

    # User B can't see it
    resp = client.get("/api/groups", headers=headers_b)
    assert resp.json() == []

    # User B can't access it directly
    resp = client.get(f"/api/groups/{group_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B can't delete it
    resp = client.delete(f"/api/groups/{group_id}", headers=headers_b)
    assert resp.status_code == 404


# ---- Phase 5: Collection (mocked), Admin, Delete ----

CLEAN_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "hotel_rows_to_import.csv")


def test_collect_hotel_mocked(client, auth_token):
    """Collect live reviews with mocked external APIs."""
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}
    hotel_id = hotel_ids[0]

    with patch("app.routers.reviews.collect_google_reviews", return_value=(4.5, 200)), \
         patch("app.routers.reviews.collect_tripadvisor_reviews", return_value=(4.0, 150)):
        resp = client.post(f"/api/reviews/hotels/{hotel_id}/collect", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is not None
    assert data["weighted_average"] is not None

    # Verify snapshot was created with correct normalized scores
    resp = client.get(f"/api/hotels/{hotel_id}/history", headers=headers)
    history = resp.json()
    live_snap = next(s for s in history if s["source"] == "live")
    assert live_snap["google_normalized"] == 9.0  # 4.5 * 2
    assert live_snap["tripadvisor_normalized"] == 8.0  # 4.0 * 2
    assert live_snap["google_count"] == 200
    assert live_snap["tripadvisor_count"] == 150


def test_collect_group_mocked(client, auth_token):
    """Collect live reviews for a group with mocked APIs."""
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.post("/api/groups", json={"name": "Collect Group", "hotel_ids": hotel_ids[:2]}, headers=headers)
    group_id = resp.json()["id"]

    with patch("app.routers.reviews.collect_google_reviews", return_value=(4.2, 100)), \
         patch("app.routers.reviews.collect_tripadvisor_reviews", return_value=(3.8, 80)):
        resp = client.post(f"/api/reviews/groups/{group_id}/collect", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["collected"] == 2


def _promote_to_admin(email: str):
    """Set is_admin=True for the user with the given email."""
    db = TestSession()
    user = db.query(User).filter(User.email == email).first()
    user.is_admin = True
    db.commit()
    db.close()


def test_admin_reset(client, auth_token):
    """Admin reset wipes data and re-imports from clean CSV."""
    if not os.path.exists(CLEAN_CSV_PATH):
        pytest.skip("Clean CSV file not found")

    _promote_to_admin("test@example.com")

    # Import original CSV first
    _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    resp = client.get("/api/hotels", params={"page_size": 500}, headers=headers)
    old_count = resp.json()["total"]
    assert old_count > 0

    # Reset
    resp = client.post("/api/admin/reset", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_hotels"] == old_count
    assert data["imported"] > 0

    # Verify new hotels exist
    resp = client.get("/api/hotels", params={"page_size": 500}, headers=headers)
    new_count = resp.json()["total"]
    assert new_count == data["imported"]


def test_delete_hotel(client, auth_token):
    """Delete a hotel and verify it's gone but others remain."""
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}
    target_id = hotel_ids[0]

    resp = client.delete(f"/api/hotels/{target_id}?confirm=true", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Verify gone
    resp = client.get(f"/api/hotels/{target_id}", headers=headers)
    assert resp.status_code == 404

    # Others still exist
    resp = client.get("/api/hotels", params={"page_size": 500}, headers=headers)
    remaining_ids = [h["id"] for h in resp.json()["items"]]
    assert target_id not in remaining_ids
    assert len(remaining_ids) == len(hotel_ids) - 1


def test_delete_hotel_cleans_up_group_membership(client, auth_token):
    """Deleting a hotel removes it from groups but group still exists."""
    hotel_ids = _import_csv(client, auth_token)
    headers = {"Authorization": f"Bearer {auth_token}"}

    # Create group with 3 hotels
    resp = client.post("/api/groups", json={"name": "Cleanup Group", "hotel_ids": hotel_ids[:3]}, headers=headers)
    group_id = resp.json()["id"]

    # Delete one hotel
    client.delete(f"/api/hotels/{hotel_ids[0]}?confirm=true", headers=headers)

    # Group still exists but has fewer members
    resp = client.get(f"/api/groups/{group_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["hotels"]) == 2


def test_delete_hotel_not_found(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.delete("/api/hotels/99999?confirm=true", headers=headers)
    assert resp.status_code == 404


def test_delete_hotel_requires_confirmation(client, auth_token):
    """DELETE without ?confirm=true should be rejected."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    client.post("/api/hotels", json={"name": "Don't Delete Me"}, headers=headers)
    resp = client.get("/api/hotels", headers=headers)
    hotel_id = resp.json()["items"][0]["id"]

    # Without confirm param → 400
    resp = client.delete(f"/api/hotels/{hotel_id}", headers=headers)
    assert resp.status_code == 400

    # With confirm=true → 200
    resp = client.delete(f"/api/hotels/{hotel_id}?confirm=true", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ---- Phase 6: Create Hotel (manual) ----

def test_create_hotel(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post(
        "/api/hotels",
        json={"name": "Test Hotel", "city": "Portland", "state": "OR", "website": "https://example.com"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Hotel"
    assert data["city"] == "Portland"
    assert data["state"] == "OR"
    assert data["website"] == "https://example.com"
    assert data["latest_snapshot"] is None

    # Verify it appears in the list
    resp = client.get("/api/hotels", headers=headers)
    names = [h["name"] for h in resp.json()["items"]]
    assert "Test Hotel" in names


def test_create_hotel_name_required(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/api/hotels", json={"city": "Portland"}, headers=headers)
    assert resp.status_code == 422


# ---- Phase 7: Hardening tests ----

def test_search_escapes_like_wildcards(client, auth_token):
    """Searching for '%' should not match all hotels."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    client.post("/api/hotels", json={"name": "100% Inn"}, headers=headers)
    client.post("/api/hotels", json={"name": "Normal Hotel"}, headers=headers)

    resp = client.get("/api/hotels", params={"search": "%"}, headers=headers)
    assert resp.status_code == 200
    names = [h["name"] for h in resp.json()["items"]]
    assert "100% Inn" in names
    assert "Normal Hotel" not in names


def test_sort_by_invalid_field_falls_back(client, auth_token):
    """Invalid sort_by values should not error; fall back to name sort."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    client.post("/api/hotels", json={"name": "Bravo Hotel"}, headers=headers)
    client.post("/api/hotels", json={"name": "Alpha Hotel"}, headers=headers)

    resp = client.get("/api/hotels", params={"sort_by": "snapshots"}, headers=headers)
    assert resp.status_code == 200
    names = [h["name"] for h in resp.json()["items"]]
    # Should fall back to name asc
    assert names == ["Alpha Hotel", "Bravo Hotel"]


def test_pagination(client, auth_token):
    """Paginated response returns correct page metadata and slices."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    for i in range(5):
        client.post("/api/hotels", json={"name": f"Hotel {i}"}, headers=headers)

    # Page 1 with page_size=2
    resp = client.get("/api/hotels", params={"page": 1, "page_size": 2}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2

    # Page 3 with page_size=2 should have 1 item
    resp = client.get("/api/hotels", params={"page": 3, "page_size": 2}, headers=headers)
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 5

    # Page beyond range returns empty items
    resp = client.get("/api/hotels", params={"page": 10, "page_size": 2}, headers=headers)
    data = resp.json()
    assert len(data["items"]) == 0
    assert data["total"] == 5


def test_hotel_list_query_count(client, auth_token):
    """Listing hotels should not issue N+1 queries for snapshots."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    for i in range(10):
        client.post("/api/hotels", json={"name": f"Hotel {i}"}, headers=headers)

    with count_queries() as queries:
        resp = client.get("/api/hotels", params={"page_size": 10}, headers=headers)

    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 10
    # With joinedload: auth query + count query + hotel+snapshots JOIN = ~3 queries
    # Without joinedload it would be 1 (auth) + 1 (count) + 1 (hotels) + 10 (snapshots) = 13
    assert len(queries) <= 5, f"Expected ≤5 queries, got {len(queries)}"


def test_admin_reset_requires_admin(client, auth_token):
    """Non-admin user should get 403 on reset endpoint."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.post("/api/admin/reset", headers=headers)
    assert resp.status_code == 403
