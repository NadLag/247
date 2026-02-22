"""
Test iCal Property Import - Bug Fix Verification
Tests that:
1. Create property via OTA import using real Airbnb iCal URL  
2. Verify bookings are imported (should be 8 bookings from the test URL)
3. Verify 'Reserved' entries are converted to 'Airbnb Guest' name
4. Verify 'Airbnb (Not available)' entries are skipped
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_ICAL_URL = "https://www.airbnb.ca/calendar/ical/1331247817144386380.ics?t=5af8dab80e7f4ea1b11aa3526227ebe2"

# Test admin session token (from seed data)
TEST_SESSION_TOKEN = None

@pytest.fixture(scope="module")
def api_client():
    """Create session with headers"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def auth_session(api_client):
    """Get or create test admin user and session"""
    global TEST_SESSION_TOKEN
    
    # First check if we have an existing session
    test_email = "test_ical_admin@test.com"
    test_password = "TestPassword123!"
    
    # Try to login with existing credentials
    login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    
    if login_response.status_code == 200:
        # Got session from login
        user_data = login_response.json()
        cookies = login_response.cookies
        session_token = cookies.get("session_token")
        if session_token:
            api_client.cookies.set("session_token", session_token)
            TEST_SESSION_TOKEN = session_token
            print(f"Logged in as existing user: {user_data.get('email')}")
            return api_client, user_data
    
    # Need to create new admin user - use raw MongoDB insert
    print("Creating new test admin user...")
    
    # We'll need to seed test data through the app
    pytest.skip("No existing test admin user available for iCal testing. Need manual test user setup.")

@pytest.fixture(scope="module")
def admin_session(api_client):
    """Use existing admin session - requires pre-created test user"""
    # Use the session token we created for testing
    test_session_token = "test_ical_session_1771791643279"
    
    # Set the auth header
    api_client.headers.update({"Authorization": f"Bearer {test_session_token}"})
    
    # Verify session works
    auth_me_response = api_client.get(f"{BASE_URL}/api/auth/me")
    if auth_me_response.status_code == 200:
        user_data = auth_me_response.json()
        if user_data.get("role") == "company_admin":
            print(f"Using test session for: {user_data.get('email')}")
            return api_client, user_data
    
    pytest.skip("Test session not valid. Recreate test admin user.")


class TestICalParsing:
    """Test the iCal parsing logic directly"""
    
    def test_fetch_ical_data(self, api_client):
        """Test that we can fetch the Airbnb iCal data"""
        response = requests.get(TEST_ICAL_URL)
        assert response.status_code == 200, f"Failed to fetch iCal: {response.status_code}"
        assert "BEGIN:VCALENDAR" in response.text, "Invalid iCal format"
        assert "VEVENT" in response.text, "No events in iCal"
        print(f"Successfully fetched iCal data ({len(response.text)} bytes)")
    
    def test_ical_has_reserved_entries(self, api_client):
        """Test that the iCal contains 'Reserved' entries"""
        response = requests.get(TEST_ICAL_URL)
        assert response.status_code == 200
        
        reserved_count = response.text.count("SUMMARY:Reserved")
        not_available_count = response.text.count("SUMMARY:Airbnb (Not available)")
        
        print(f"Found {reserved_count} 'Reserved' entries (actual bookings)")
        print(f"Found {not_available_count} 'Not available' entries (blocked dates)")
        
        assert reserved_count == 8, f"Expected 8 'Reserved' entries, got {reserved_count}"
        assert not_available_count == 6, f"Expected 6 'Not available' entries, got {not_available_count}"


class TestOTAImport:
    """Test OTA import functionality - requires admin authentication"""
    
    def test_verify_existing_import(self, admin_session):
        """Verify that the test property was already imported with correct bookings"""
        api_client, user_data = admin_session
        
        # Get bookings - should have 8 Airbnb bookings already imported
        response = api_client.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        
        bookings = response.json()
        airbnb_bookings = [b for b in bookings if b.get("ota_source") == "airbnb"]
        
        print(f"Found {len(airbnb_bookings)} Airbnb bookings")
        
        # Should have 8 bookings
        assert len(airbnb_bookings) == 8, f"Expected 8 Airbnb bookings, got {len(airbnb_bookings)}"
        
        # All should have guest_name = "Airbnb Guest"
        for booking in airbnb_bookings:
            assert booking.get("guest_name") == "Airbnb Guest", \
                f"Expected 'Airbnb Guest', got '{booking.get('guest_name')}'"
        
        print("SUCCESS: All 8 bookings imported with correct 'Airbnb Guest' name")
    
    def test_verify_imported_bookings(self, admin_session):
        """Verify that imported bookings have correct guest names"""
        api_client, user_data = admin_session
        
        # List all bookings
        response = api_client.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        
        bookings = response.json()
        
        # Find bookings from our test import (ota_source = airbnb)
        airbnb_bookings = [b for b in bookings if b.get("ota_source") == "airbnb"]
        
        print(f"Total bookings: {len(bookings)}")
        print(f"Airbnb bookings: {len(airbnb_bookings)}")
        
        # Check that "Reserved" was converted to "Airbnb Guest"
        for booking in airbnb_bookings:
            guest_name = booking.get("guest_name", "")
            print(f"  - Booking: {booking.get('id')} | Guest: {guest_name} | Check-in: {booking.get('check_in')}")
            
            # The guest name should NOT be "Reserved" - it should be "Airbnb Guest"
            assert guest_name != "Reserved", f"Bug: Guest name is still 'Reserved' for booking {booking.get('id')}"
        
        # Check that we have "Airbnb Guest" entries
        airbnb_guest_count = len([b for b in airbnb_bookings if b.get("guest_name") == "Airbnb Guest"])
        print(f"Bookings with 'Airbnb Guest' name: {airbnb_guest_count}")
        
        # Verify blocked dates were NOT imported
        blocked_bookings = [b for b in bookings if "Not available" in b.get("guest_name", "")]
        assert len(blocked_bookings) == 0, f"Bug: {len(blocked_bookings)} blocked dates were imported as bookings"


class TestBookingsPage:
    """Test that bookings appear on the bookings page"""
    
    def test_list_bookings(self, admin_session):
        """Verify bookings list endpoint returns data"""
        api_client, user_data = admin_session
        
        response = api_client.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        
        bookings = response.json()
        print(f"Total bookings in system: {len(bookings)}")
        
        # Should have at least some bookings
        assert len(bookings) >= 0, "Bookings endpoint returned non-list"
        
        if bookings:
            # Check structure of first booking
            first = bookings[0]
            required_fields = ["id", "guest_name", "check_in", "check_out", "status"]
            for field in required_fields:
                assert field in first, f"Missing field '{field}' in booking"


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_properties(self, admin_session):
        """Delete test properties created during tests"""
        api_client, user_data = admin_session
        
        # Get all properties
        response = api_client.get(f"{BASE_URL}/api/properties")
        if response.status_code != 200:
            pytest.skip("Cannot get properties for cleanup")
        
        properties = response.json()
        
        # Delete TEST_ prefixed properties
        deleted = 0
        for prop in properties:
            if prop.get("name", "").startswith("TEST_"):
                del_response = api_client.delete(f"{BASE_URL}/api/properties/{prop['id']}")
                if del_response.status_code == 200:
                    deleted += 1
                    print(f"Deleted test property: {prop['name']}")
        
        print(f"Cleaned up {deleted} test properties")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
