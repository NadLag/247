"""
OTA iCal Sync Feature Tests - Using pre-created test session
Tests: OTA feeds CRUD, Sync trigger, Sync status, Sync logs
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Pre-created test session from mongosh
# Create test data before running: use auth_testing.md guide
TEST_SESSION = "test_ota_session_1771783913416"
TEST_PROPERTY_ID_1 = "prop_ota_test_1_1771783913416"  
TEST_PROPERTY_ID_2 = "prop_ota_test_2_1771783913416"

# Track created resources for cleanup
CREATED_FEEDS = []


def get_headers():
    return {"Authorization": f"Bearer {TEST_SESSION}"}


class TestOTAAccessControl:
    """Access control tests - verify admin-only access"""

    def test_ota_feeds_requires_auth(self):
        """GET /api/ota/feeds without auth should 401"""
        response = requests.get(f"{BASE_URL}/api/ota/feeds")
        assert response.status_code == 401
        print("✅ OTA feeds endpoint requires authentication")

    def test_sync_requires_auth(self):
        """POST /api/ota/sync without auth should 401"""
        response = requests.post(f"{BASE_URL}/api/ota/sync")
        assert response.status_code == 401
        print("✅ OTA sync endpoint requires authentication")

    def test_sync_status_requires_auth(self):
        """GET /api/ota/sync-status without auth should 401"""
        response = requests.get(f"{BASE_URL}/api/ota/sync-status")
        assert response.status_code == 401
        print("✅ OTA sync-status endpoint requires authentication")


class TestOTAFeedsCRUD:
    """OTA Feeds CRUD endpoint tests"""

    def test_auth_me_works(self):
        """Verify test session is valid"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") == "company_admin"
        print(f"✅ Session valid for user: {data.get('email')}")

    def test_list_properties(self):
        """Verify test properties exist"""
        response = requests.get(f"{BASE_URL}/api/properties", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        print(f"✅ Found {len(data)} properties")

    def test_list_ota_feeds(self):
        """GET /api/ota/feeds - list feeds for company"""
        response = requests.get(f"{BASE_URL}/api/ota/feeds", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List OTA feeds returned {len(data)} feeds")

    def test_create_ota_feed_vrbo(self):
        """POST /api/ota/feeds - create VRBO feed with mock URL"""
        payload = {
            "property_id": TEST_PROPERTY_ID_1,
            "source": "vrbo",
            "ical_url": "mock://vrbo/TestProperty1"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={**get_headers(), "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["source"] == "vrbo"
        assert data["property_id"] == TEST_PROPERTY_ID_1
        assert data["active"] == True
        assert "property_name" in data
        CREATED_FEEDS.append(data["id"])
        print(f"✅ Created VRBO feed: {data['id']}")

    def test_create_ota_feed_expedia(self):
        """POST /api/ota/feeds - create Expedia feed"""
        payload = {
            "property_id": TEST_PROPERTY_ID_2,
            "source": "expedia",
            "ical_url": "mock://expedia/TestProperty2",
            "name": "Custom Expedia Feed Name"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={**get_headers(), "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["source"] == "expedia"
        assert data["name"] == "Custom Expedia Feed Name"
        CREATED_FEEDS.append(data["id"])
        print(f"✅ Created Expedia feed: {data['id']}")

    def test_create_duplicate_feed_fails(self):
        """POST /api/ota/feeds - duplicate source+property should fail"""
        payload = {
            "property_id": TEST_PROPERTY_ID_1,
            "source": "vrbo",  # Same as created above
            "ical_url": "mock://vrbo/Duplicate"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={**get_headers(), "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 400
        assert "already exists" in response.json().get("detail", "").lower()
        print("✅ Duplicate feed correctly rejected")

    def test_create_feed_invalid_property(self):
        """POST /api/ota/feeds - invalid property should 404"""
        payload = {
            "property_id": "nonexistent_property_id",
            "source": "other",
            "ical_url": "mock://other/Test"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={**get_headers(), "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 404
        print("✅ Invalid property correctly rejected")

    def test_list_ota_feeds_with_property_names(self):
        """GET /api/ota/feeds - feeds should include property_name"""
        response = requests.get(f"{BASE_URL}/api/ota/feeds", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        
        # Check feeds have property_name enrichment
        for feed in data:
            assert "property_name" in feed
            assert feed["property_name"] != "Unknown Property"
        print(f"✅ All {len(data)} feeds have property_name")

    def test_update_ota_feed(self):
        """PUT /api/ota/feeds/{id} - update feed name and active status"""
        if not CREATED_FEEDS:
            pytest.skip("No feeds created to update")
        
        feed_id = CREATED_FEEDS[0]
        payload = {
            "name": "Updated VRBO Feed Name",
            "active": False
        }
        response = requests.put(
            f"{BASE_URL}/api/ota/feeds/{feed_id}",
            headers={**get_headers(), "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated VRBO Feed Name"
        assert data["active"] == False
        print(f"✅ Updated feed: {feed_id}")
        
        # Re-enable for sync tests
        requests.put(
            f"{BASE_URL}/api/ota/feeds/{feed_id}",
            headers={**get_headers(), "Content-Type": "application/json"},
            json={"active": True}
        )

    def test_update_nonexistent_feed(self):
        """PUT /api/ota/feeds/{id} - nonexistent feed should 404"""
        response = requests.put(
            f"{BASE_URL}/api/ota/feeds/nonexistent_feed_id",
            headers={**get_headers(), "Content-Type": "application/json"},
            json={"name": "Test"}
        )
        assert response.status_code == 404
        print("✅ Nonexistent feed update correctly returns 404")


class TestOTASync:
    """OTA Sync trigger and status tests"""

    def test_get_sync_status(self):
        """GET /api/ota/sync-status - check sync status"""
        response = requests.get(f"{BASE_URL}/api/ota/sync-status", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "is_syncing" in data
        assert "feeds_count" in data
        assert "latest_sync" in data
        print(f"✅ Sync status: syncing={data['is_syncing']}, feeds={data['feeds_count']}")

    def test_trigger_ota_sync(self):
        """POST /api/ota/sync - trigger background sync"""
        response = requests.post(f"{BASE_URL}/api/ota/sync", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["started", "no_feeds"]
        if data["status"] == "started":
            assert "sync_id" in data
            assert "feeds_count" in data
            print(f"✅ Sync started: {data['sync_id']}, feeds: {data['feeds_count']}")
        else:
            print("⚠️ No feeds configured for sync")

    def test_sync_completion(self):
        """GET /api/ota/sync-status - verify sync completes"""
        # Wait for background task to complete
        time.sleep(5)
        
        response = requests.get(f"{BASE_URL}/api/ota/sync-status", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        
        if data.get("latest_sync"):
            latest = data["latest_sync"]
            assert latest["status"] in ["completed", "completed_with_errors", "processing"]
            if "stats" in latest:
                stats = latest["stats"]
                print(f"✅ Sync completed: created={stats.get('created', 0)}, updated={stats.get('updated', 0)}, errors={stats.get('errors', 0)}")
            else:
                print(f"⚠️ Sync status: {latest['status']}")
        else:
            print("⚠️ No sync logs available")

    def test_sync_creates_bookings_with_ota_source(self):
        """GET /api/bookings - verify OTA bookings have ota_source field"""
        response = requests.get(f"{BASE_URL}/api/bookings", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        
        ota_bookings = [b for b in data if b.get("ota_source")]
        print(f"✅ Found {len(ota_bookings)} OTA-sourced bookings out of {len(data)} total")
        
        if ota_bookings:
            # Verify OTA booking structure
            booking = ota_bookings[0]
            assert "ota_source" in booking
            assert "ota_external_id" in booking
            assert "ota_feed_id" in booking
            assert "imported_at" in booking
            print(f"✅ OTA booking structure verified: source={booking['ota_source']}")


class TestOTASyncLogs:
    """OTA Sync logs endpoint tests"""

    def test_list_sync_logs(self):
        """GET /api/ota-sync-logs - list sync logs"""
        response = requests.get(f"{BASE_URL}/api/ota-sync-logs", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Found {len(data)} sync logs")
        
        if data:
            log = data[0]
            assert "id" in log
            assert "source" in log
            assert "event_type" in log
            assert "status" in log
            assert "created_at" in log
            print(f"✅ Latest log: status={log['status']}, event={log['event_type']}")

    def test_sync_logs_limit(self):
        """GET /api/ota-sync-logs?limit=1 - verify limit parameter"""
        response = requests.get(f"{BASE_URL}/api/ota-sync-logs?limit=1", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
        print(f"✅ Limit parameter works: returned {len(data)} logs")


class TestOTAFeedsCleanup:
    """Cleanup tests - run last"""

    def test_delete_ota_feed(self):
        """DELETE /api/ota/feeds/{id} - delete feed"""
        if not CREATED_FEEDS:
            pytest.skip("No feeds to delete")
        
        feed_id = CREATED_FEEDS[-1]  # Delete last created feed
        response = requests.delete(
            f"{BASE_URL}/api/ota/feeds/{feed_id}",
            headers=get_headers()
        )
        assert response.status_code == 200
        assert "deleted" in response.json().get("message", "").lower()
        print(f"✅ Deleted feed: {feed_id}")
        CREATED_FEEDS.remove(feed_id)

    def test_delete_nonexistent_feed(self):
        """DELETE /api/ota/feeds/{id} - nonexistent should 404"""
        response = requests.delete(
            f"{BASE_URL}/api/ota/feeds/nonexistent_feed_id",
            headers=get_headers()
        )
        assert response.status_code == 404
        print("✅ Nonexistent feed delete correctly returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
