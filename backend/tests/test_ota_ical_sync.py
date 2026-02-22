"""
OTA iCal Sync Feature Tests
Tests: OTA feeds CRUD, Sync trigger, Sync status, Sync logs, Duplicate detection
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data created via setup
TEST_SESSION = None
TEST_COMPANY_ID = None
TEST_PROPERTY_IDS = []
CREATED_FEEDS = []


class TestOTAFeedsCRUD:
    """OTA Feeds CRUD endpoint tests"""

    @pytest.fixture(autouse=True)
    def setup(self, session_with_properties):
        """Use shared session and properties"""
        global TEST_SESSION, TEST_COMPANY_ID, TEST_PROPERTY_IDS
        TEST_SESSION = session_with_properties["session_token"]
        TEST_COMPANY_ID = session_with_properties["company_id"]
        TEST_PROPERTY_IDS = session_with_properties["property_ids"]

    def test_list_ota_feeds_empty(self):
        """GET /api/ota/feeds - should return empty list initially"""
        response = requests.get(
            f"{BASE_URL}/api/ota/feeds",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ List OTA feeds returned {len(data)} feeds")

    def test_create_ota_feed_airbnb(self):
        """POST /api/ota/feeds - create Airbnb feed with mock URL"""
        payload = {
            "property_id": TEST_PROPERTY_IDS[0],
            "source": "airbnb",
            "ical_url": "mock://airbnb/TestProperty1"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["source"] == "airbnb"
        assert data["property_id"] == TEST_PROPERTY_IDS[0]
        assert data["active"] == True
        assert "property_name" in data
        CREATED_FEEDS.append(data["id"])
        print(f"✅ Created Airbnb feed: {data['id']}")

    def test_create_ota_feed_booking_com(self):
        """POST /api/ota/feeds - create Booking.com feed"""
        if len(TEST_PROPERTY_IDS) < 2:
            pytest.skip("Need at least 2 properties")
        
        payload = {
            "property_id": TEST_PROPERTY_IDS[1],
            "source": "booking.com",
            "ical_url": "mock://booking.com/TestProperty2",
            "name": "Custom Feed Name"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "booking.com"
        assert data["name"] == "Custom Feed Name"
        CREATED_FEEDS.append(data["id"])
        print(f"✅ Created Booking.com feed: {data['id']}")

    def test_create_duplicate_feed_fails(self):
        """POST /api/ota/feeds - duplicate source+property should fail"""
        payload = {
            "property_id": TEST_PROPERTY_IDS[0],
            "source": "airbnb",  # Same as first feed
            "ical_url": "mock://airbnb/Duplicate"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 400
        assert "already exists" in response.json().get("detail", "").lower()
        print("✅ Duplicate feed correctly rejected")

    def test_create_feed_invalid_property(self):
        """POST /api/ota/feeds - invalid property should 404"""
        payload = {
            "property_id": "nonexistent_property",
            "source": "vrbo",
            "ical_url": "mock://vrbo/Test"
        }
        response = requests.post(
            f"{BASE_URL}/api/ota/feeds",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 404
        print("✅ Invalid property correctly rejected")

    def test_list_ota_feeds_with_data(self):
        """GET /api/ota/feeds - should return created feeds with property names"""
        response = requests.get(
            f"{BASE_URL}/api/ota/feeds",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        # Verify enrichment with property names
        for feed in data:
            assert "property_name" in feed
            assert feed["property_name"] != "Unknown Property"
        print(f"✅ Listed {len(data)} feeds with property names")

    def test_update_ota_feed(self):
        """PUT /api/ota/feeds/{id} - update feed name and active status"""
        if not CREATED_FEEDS:
            pytest.skip("No feeds created")
        
        feed_id = CREATED_FEEDS[0]
        payload = {
            "name": "Updated Feed Name",
            "active": False
        }
        response = requests.put(
            f"{BASE_URL}/api/ota/feeds/{feed_id}",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Feed Name"
        assert data["active"] == False
        print(f"✅ Updated feed: {feed_id}")
        
        # Re-enable for sync tests
        requests.put(
            f"{BASE_URL}/api/ota/feeds/{feed_id}",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json={"active": True}
        )

    def test_update_nonexistent_feed(self):
        """PUT /api/ota/feeds/{id} - nonexistent feed should 404"""
        response = requests.put(
            f"{BASE_URL}/api/ota/feeds/nonexistent",
            headers={"Authorization": f"Bearer {TEST_SESSION}", "Content-Type": "application/json"},
            json={"name": "Test"}
        )
        assert response.status_code == 404
        print("✅ Nonexistent feed update correctly rejected")


class TestOTASync:
    """OTA Sync trigger and status tests"""

    def test_get_sync_status_initial(self):
        """GET /api/ota/sync-status - check initial status"""
        response = requests.get(
            f"{BASE_URL}/api/ota/sync-status",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_syncing" in data
        assert "feeds_count" in data
        assert "latest_sync" in data
        print(f"✅ Sync status: syncing={data['is_syncing']}, feeds={data['feeds_count']}")

    def test_trigger_ota_sync(self):
        """POST /api/ota/sync - trigger background sync"""
        response = requests.post(
            f"{BASE_URL}/api/ota/sync",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
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
        # Wait for background task
        time.sleep(5)
        
        response = requests.get(
            f"{BASE_URL}/api/ota/sync-status",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("latest_sync"):
            latest = data["latest_sync"]
            assert latest["status"] in ["completed", "completed_with_errors", "processing"]
            assert "stats" in latest or latest["status"] == "processing"
            if "stats" in latest:
                print(f"✅ Sync completed: created={latest['stats']['created']}, updated={latest['stats']['updated']}")
        else:
            print("⚠️ No sync logs available")

    def test_sync_creates_bookings(self):
        """GET /api/bookings - verify OTA bookings created with ota_source"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
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


class TestOTASyncLogs:
    """OTA Sync logs endpoint tests"""

    def test_list_sync_logs(self):
        """GET /api/ota-sync-logs - list sync logs"""
        response = requests.get(
            f"{BASE_URL}/api/ota-sync-logs",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
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

    def test_sync_logs_limit(self):
        """GET /api/ota-sync-logs?limit=1 - verify limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/ota-sync-logs?limit=1",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
        print(f"✅ Limit parameter works: returned {len(data)} logs")


class TestOTAFeedsCleanup:
    """Cleanup tests - run last"""

    def test_delete_ota_feed(self):
        """DELETE /api/ota/feeds/{id} - delete feed"""
        if len(CREATED_FEEDS) < 2:
            pytest.skip("Need feeds to delete")
        
        feed_id = CREATED_FEEDS[-1]  # Delete last created feed
        response = requests.delete(
            f"{BASE_URL}/api/ota/feeds/{feed_id}",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 200
        assert "deleted" in response.json().get("message", "").lower()
        print(f"✅ Deleted feed: {feed_id}")
        CREATED_FEEDS.remove(feed_id)

    def test_delete_nonexistent_feed(self):
        """DELETE /api/ota/feeds/{id} - nonexistent should 404"""
        response = requests.delete(
            f"{BASE_URL}/api/ota/feeds/nonexistent",
            headers={"Authorization": f"Bearer {TEST_SESSION}"}
        )
        assert response.status_code == 404
        print("✅ Nonexistent feed delete correctly returns 404")


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


@pytest.fixture(scope="session")
def session_with_properties():
    """Create test admin user with company and properties"""
    import subprocess
    import json
    
    ts = str(int(time.time() * 1000))
    
    # Create test data in MongoDB
    mongo_script = f'''
    use('test_database');
    var userId = 'test-ota-pytest-{ts}';
    var companyId = 'comp_ota_pytest_{ts}';
    var sessionToken = 'ota_pytest_session_{ts}';
    var propId1 = 'prop_ota_pytest_1_{ts}';
    var propId2 = 'prop_ota_pytest_2_{ts}';
    
    db.companies.insertOne({{
        company_id: companyId,
        name: 'OTA Pytest Company',
        subscription_status: 'trial',
        created_at: new Date(),
        updated_at: new Date()
    }});
    
    db.users.insertOne({{
        user_id: userId,
        email: 'ota.pytest.{ts}@example.com',
        name: 'OTA Pytest Admin',
        company_id: companyId,
        role: 'company_admin',
        created_at: new Date(),
        updated_at: new Date()
    }});
    
    db.user_sessions.insertOne({{
        user_id: userId,
        session_token: sessionToken,
        expires_at: new Date(Date.now() + 24*60*60*1000),
        created_at: new Date()
    }});
    
    db.properties.insertMany([
        {{id: propId1, company_id: companyId, name: 'Pytest Beach House', address: '123 Test Dr', owner_first_name: 'Test', owner_last_name: 'Owner', owner_phone: '+1234567890', owner_email: 'test@example.com', units: 1, active: true, created_at: new Date(), updated_at: new Date()}},
        {{id: propId2, company_id: companyId, name: 'Pytest Mountain Cabin', address: '456 Test Rd', owner_first_name: 'Test', owner_last_name: 'Owner2', owner_phone: '+1234567891', owner_email: 'test2@example.com', units: 2, active: true, created_at: new Date(), updated_at: new Date()}}
    ]);
    
    printjson({{
        session_token: sessionToken,
        company_id: companyId,
        property_ids: [propId1, propId2]
    }});
    '''
    
    result = subprocess.run(
        ["mongosh", "--quiet", "--eval", mongo_script],
        capture_output=True,
        text=True
    )
    
    # Parse output
    output = result.stdout.strip()
    lines = output.split('\n')
    for line in lines:
        if line.startswith('{'):
            data = json.loads(line)
            return data
    
    # Fallback - use predefined test session
    return {
        "session_token": f"ota_pytest_session_{ts}",
        "company_id": f"comp_ota_pytest_{ts}",
        "property_ids": [f"prop_ota_pytest_1_{ts}", f"prop_ota_pytest_2_{ts}"]
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
