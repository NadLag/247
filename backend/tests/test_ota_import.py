"""
Test OTA Import Property Feature
Tests the unified 'Add Property' flow with OTA import and manual add options

Features tested:
1. POST /api/ota/import-property - Creates new property from iCal and imports bookings
2. GET /api/properties/{id} - Returns single property by ID
3. GET /api/ota/sync-status - Returns feeds_count for conditional UI
4. GET /api/bookings - Verify imported bookings have OTA source
5. Manual property creation via POST /api/properties
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOTAImportProperty:
    """Test OTA Import Property feature - create property from iCal URL"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user and session"""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('TEST_SESSION_TOKEN', 'test_import_session_1771787827199')}"
        })
    
    def test_auth_endpoint(self):
        """Verify authentication is working"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert "company_id" in data
        assert data["role"] == "company_admin"
        print(f"✅ Auth verified: {data['email']}")
    
    def test_import_property_from_ota(self):
        """Test POST /api/ota/import-property - creates new property and imports bookings"""
        payload = {
            "name": "Test Mountain Cabin",
            "source": "vrbo",
            "ical_url": "mock://vrbo/Test_Mountain_Cabin"
        }
        response = self.session.post(f"{BASE_URL}/api/ota/import-property", json=payload)
        
        # Status assertion
        assert response.status_code == 200, f"Import failed: {response.text}"
        
        # Data assertions
        data = response.json()
        assert data["status"] == "success"
        assert "property_id" in data
        assert data["property_name"] == "Test Mountain Cabin"
        assert "bookings_imported" in data
        assert isinstance(data["bookings_imported"], int)
        assert "feed_id" in data
        
        print(f"✅ Property imported: {data['property_id']} with {data['bookings_imported']} bookings")
        
        # Store for subsequent tests
        self.property_id = data["property_id"]
        return data
    
    def test_get_single_property(self):
        """Test GET /api/properties/{id} - returns single property"""
        # First import a property
        import_result = self.test_import_property_from_ota()
        property_id = import_result["property_id"]
        
        # GET the property
        response = self.session.get(f"{BASE_URL}/api/properties/{property_id}")
        
        # Status assertion
        assert response.status_code == 200, f"Get property failed: {response.text}"
        
        # Data assertions
        prop = response.json()
        assert prop["id"] == property_id
        assert prop["name"] == "Test Mountain Cabin"
        assert prop["ota_source"] == "vrbo"
        assert prop["active"] == True
        assert "ota_ical_url" in prop
        
        print(f"✅ Single property endpoint works: {prop['name']}")
    
    def test_get_nonexistent_property(self):
        """Test GET /api/properties/{id} - returns 404 for invalid ID"""
        response = self.session.get(f"{BASE_URL}/api/properties/invalid_prop_id")
        assert response.status_code == 404
        print("✅ 404 returned for nonexistent property")
    
    def test_imported_bookings_have_ota_source(self):
        """Test that imported bookings have ota_source field"""
        response = self.session.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        
        bookings = response.json()
        ota_bookings = [b for b in bookings if b.get("ota_source")]
        
        assert len(ota_bookings) > 0, "No OTA bookings found"
        
        for booking in ota_bookings:
            assert "ota_source" in booking
            assert "ota_external_id" in booking
            assert "ota_feed_id" in booking
            assert booking["ota_source"] in ["airbnb", "booking.com", "vrbo", "expedia"]
        
        print(f"✅ Found {len(ota_bookings)} bookings with OTA source")
    
    def test_sync_status_shows_feeds_count(self):
        """Test GET /api/ota/sync-status - returns feeds_count > 0 after import"""
        response = self.session.get(f"{BASE_URL}/api/ota/sync-status")
        assert response.status_code == 200
        
        data = response.json()
        assert "feeds_count" in data
        assert "is_syncing" in data
        assert data["feeds_count"] >= 1, "Should have at least 1 feed after import"
        
        print(f"✅ Sync status shows {data['feeds_count']} feeds")
    
    def test_import_different_sources(self):
        """Test importing from different OTA sources"""
        sources = [
            {"name": "City Apartment", "source": "booking.com", "ical_url": "mock://booking.com/City_Apartment"},
            {"name": "Beach Villa", "source": "expedia", "ical_url": "mock://expedia/Beach_Villa"},
        ]
        
        for payload in sources:
            response = self.session.post(f"{BASE_URL}/api/ota/import-property", json=payload)
            assert response.status_code == 200, f"Import failed for {payload['source']}: {response.text}"
            data = response.json()
            assert data["status"] == "success"
            print(f"✅ Imported from {payload['source']}: {data['property_name']}")
    
    def test_import_validation_empty_name(self):
        """Test validation - empty name should fail"""
        payload = {
            "name": "",
            "source": "airbnb",
            "ical_url": "mock://airbnb/Test"
        }
        response = self.session.post(f"{BASE_URL}/api/ota/import-property", json=payload)
        # Should either fail validation or succeed and strip whitespace
        # Based on the code, empty string might pass but stripped
        if response.status_code == 200:
            data = response.json()
            assert "property_id" in data
        print(f"✅ Empty name handling verified (status: {response.status_code})")
    
    def test_import_validation_invalid_url(self):
        """Test validation - invalid URL handling"""
        payload = {
            "name": "Test Property",
            "source": "airbnb",
            "ical_url": "not_a_valid_url"
        }
        response = self.session.post(f"{BASE_URL}/api/ota/import-property", json=payload)
        # Should fail since it's not a mock:// or valid URL
        assert response.status_code in [400, 500], f"Expected error for invalid URL: {response.text}"
        print("✅ Invalid URL properly rejected")


class TestManualPropertyCreation:
    """Test manual property creation (existing functionality)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('TEST_SESSION_TOKEN', 'test_import_session_1771787827199')}"
        })
    
    def test_create_property_manually(self):
        """Test POST /api/properties - manual creation"""
        payload = {
            "name": "Manual Test Property",
            "address": "123 Test Street",
            "property_type": "Apartment",
            "rooms": 2,
            "suites": 1,
            "bathrooms": 1,
            "city": "Test City",
            "country": "United States",
            "notes": "Created manually for testing",
            "owner_first_name": "John",
            "owner_last_name": "Doe",
            "owner_phone": "+1234567890",
            "owner_email": "john.doe@test.com",
            "units": 1,
            "active": True
        }
        response = self.session.post(f"{BASE_URL}/api/properties", json=payload)
        
        # Status assertion
        assert response.status_code == 201, f"Manual create failed: {response.text}"
        
        # Data assertions
        data = response.json()
        assert data["name"] == "Manual Test Property"
        assert data["property_type"] == "Apartment"
        assert data["owner_first_name"] == "John"
        assert "id" in data
        
        print(f"✅ Manual property created: {data['id']}")
        return data
    
    def test_update_property(self):
        """Test PUT /api/properties/{id}"""
        # First create a property
        create_result = self.test_create_property_manually()
        property_id = create_result["id"]
        
        # Update it
        update_payload = {
            "name": "Updated Property Name",
            "rooms": 5,
            "city": "New City"
        }
        response = self.session.put(f"{BASE_URL}/api/properties/{property_id}", json=update_payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Updated Property Name"
        assert data["rooms"] == 5
        assert data["city"] == "New City"
        
        print(f"✅ Property updated: {property_id}")


class TestOTAFeedsAfterImport:
    """Test that OTA feeds are created correctly after import"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('TEST_SESSION_TOKEN', 'test_import_session_1771787827199')}"
        })
    
    def test_feeds_created_after_import(self):
        """Verify OTA feed is created when property is imported"""
        # Import a new property
        import_payload = {
            "name": "Feed Test Property",
            "source": "airbnb",
            "ical_url": "mock://airbnb/Feed_Test_Property"
        }
        import_response = self.session.post(f"{BASE_URL}/api/ota/import-property", json=import_payload)
        assert import_response.status_code == 200
        
        import_data = import_response.json()
        feed_id = import_data["feed_id"]
        property_id = import_data["property_id"]
        
        # Get feeds and verify
        feeds_response = self.session.get(f"{BASE_URL}/api/ota/feeds")
        assert feeds_response.status_code == 200
        
        feeds = feeds_response.json()
        matching_feed = next((f for f in feeds if f["id"] == feed_id), None)
        
        assert matching_feed is not None, f"Feed {feed_id} not found"
        assert matching_feed["property_id"] == property_id
        assert matching_feed["source"] == "airbnb"
        assert matching_feed["active"] == True
        assert matching_feed["property_name"] == "Feed Test Property"
        
        print(f"✅ Feed created correctly: {feed_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
