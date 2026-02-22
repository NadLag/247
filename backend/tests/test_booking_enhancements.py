"""
Test suite for Booking Enhancements:
1. Auto-checkout status - expired bookings auto-update to checked_out
2. Past-date validation - block manual bookings with check-in in the past  
3. iCal source tracking - tag booking source (Airbnb, etc)
4. Source filter dropdown on Bookings page
5. Source display in booking list/table
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')
PROPERTY_ID = os.environ.get('TEST_PROPERTY_ID', '')

@pytest.fixture(scope="module")
def api_client():
    """Setup requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session

@pytest.fixture(scope="module")
def cleanup_ids():
    """Track created booking IDs for cleanup"""
    ids = []
    yield ids
    # Cleanup happens in test_99_cleanup

class TestBookingEnhancements:
    """Test booking enhancement features"""
    
    def test_01_auth_verification(self, api_client):
        """Verify authentication is working"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Auth failed: {response.text}"
        user = response.json()
        assert "user_id" in user
        assert user.get("role") == "company_admin"
        print(f"✓ Authenticated as: {user.get('name')} ({user.get('email')})")
    
    def test_02_past_date_booking_rejected(self, api_client, cleanup_ids):
        """POST /api/bookings should reject bookings with past check-in date"""
        # Create booking with check_in yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        payload = {
            "property_id": PROPERTY_ID,
            "guest_name": "TEST_Past Date Guest",
            "check_in": yesterday,
            "check_out": checkout,
            "total_amount": 100,
            "guests_count": 1,
            "status": "confirmed"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bookings", json=payload)
        assert response.status_code == 400, f"Expected 400 for past date, got {response.status_code}: {response.text}"
        
        error = response.json()
        assert "detail" in error
        assert "past" in error["detail"].lower() or "future" in error["detail"].lower()
        print(f"✓ Past date booking correctly rejected: {error['detail']}")
    
    def test_03_today_booking_accepted(self, api_client, cleanup_ids):
        """POST /api/bookings should accept bookings with today's check-in"""
        today = datetime.now().strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        payload = {
            "property_id": PROPERTY_ID,
            "guest_name": "TEST_Today Guest",
            "check_in": today,
            "check_out": checkout,
            "total_amount": 200,
            "guests_count": 2,
            "status": "confirmed"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bookings", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        booking = response.json()
        cleanup_ids.append(booking["id"])
        assert booking["check_in"] == today
        assert booking.get("ota_source") == "manual", f"Expected ota_source='manual', got {booking.get('ota_source')}"
        print(f"✓ Today's booking accepted with id: {booking['id']}, ota_source: {booking.get('ota_source')}")
    
    def test_04_future_booking_accepted(self, api_client, cleanup_ids):
        """POST /api/bookings should accept bookings with future check-in"""
        future_checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        future_checkout = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        
        payload = {
            "property_id": PROPERTY_ID,
            "guest_name": "TEST_Future Guest",
            "check_in": future_checkin,
            "check_out": future_checkout,
            "total_amount": 500,
            "guests_count": 3,
            "status": "confirmed"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bookings", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        booking = response.json()
        cleanup_ids.append(booking["id"])
        assert booking["check_in"] == future_checkin
        assert booking.get("ota_source") == "manual"
        print(f"✓ Future booking accepted with id: {booking['id']}")
    
    def test_05_manual_booking_has_ota_source(self, api_client, cleanup_ids):
        """Manual bookings should have ota_source='manual'"""
        future = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=23)).strftime("%Y-%m-%d")
        
        payload = {
            "property_id": PROPERTY_ID,
            "guest_name": "TEST_Source Check Guest",
            "check_in": future,
            "check_out": checkout,
            "total_amount": 300,
            "guests_count": 1,
            "status": "confirmed"
        }
        
        response = api_client.post(f"{BASE_URL}/api/bookings", json=payload)
        assert response.status_code == 201
        
        booking = response.json()
        cleanup_ids.append(booking["id"])
        
        assert "ota_source" in booking, "ota_source field missing"
        assert booking["ota_source"] == "manual", f"Expected 'manual', got '{booking['ota_source']}'"
        print(f"✓ Manual booking has ota_source='manual': {booking['id']}")
    
    def test_06_get_bookings_sources_endpoint(self, api_client):
        """GET /api/bookings/sources should return available sources"""
        response = api_client.get(f"{BASE_URL}/api/bookings/sources")
        assert response.status_code == 200, f"Sources endpoint failed: {response.text}"
        
        sources = response.json()
        assert isinstance(sources, list)
        
        # Check structure of each source
        for source in sources:
            assert "value" in source, f"Source missing 'value': {source}"
            assert "label" in source, f"Source missing 'label': {source}"
        
        print(f"✓ Sources endpoint returned {len(sources)} sources: {[s['value'] for s in sources]}")
    
    def test_07_filter_bookings_by_source_direct(self, api_client):
        """GET /api/bookings?source=direct should filter to direct/manual bookings"""
        response = api_client.get(f"{BASE_URL}/api/bookings?source=direct")
        assert response.status_code == 200, f"Filtered bookings failed: {response.text}"
        
        bookings = response.json()
        assert isinstance(bookings, list)
        
        # All returned bookings should be direct/manual
        for b in bookings:
            ota_source = b.get("ota_source")
            # Direct bookings have ota_source=None, 'manual', or missing
            assert ota_source in [None, "manual"] or not ota_source, \
                f"Non-direct booking returned: {b.get('id')} has ota_source={ota_source}"
        
        print(f"✓ Source filter 'direct' returned {len(bookings)} bookings")
    
    def test_08_auto_checkout_in_list_bookings(self, api_client, cleanup_ids):
        """GET /api/bookings should auto-update expired bookings to checked_out"""
        # First, create a booking that will be in the past for testing
        # We'll need to directly insert via MongoDB or use a different approach
        # For now, verify the logic exists by checking existing data
        
        response = api_client.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        
        bookings = response.json()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check that expired bookings have been auto-updated
        expired_confirmed = [b for b in bookings 
                          if b.get("check_out", "") < today 
                          and b.get("status") == "confirmed"
                          and b.get("booking_type") != "blocked"]
        
        expired_checked_in = [b for b in bookings
                            if b.get("check_out", "") < today
                            and b.get("status") == "checked_in"
                            and b.get("booking_type") != "blocked"]
        
        # After calling list_bookings, there should be no expired confirmed/checked_in
        print(f"✓ Auto-checkout check: {len(expired_confirmed)} expired confirmed, {len(expired_checked_in)} expired checked_in")
        # Note: These should be 0 if auto-checkout is working
        assert len(expired_confirmed) == 0, f"Found {len(expired_confirmed)} expired 'confirmed' bookings that should be checked_out"
        assert len(expired_checked_in) == 0, f"Found {len(expired_checked_in)} expired 'checked_in' bookings that should be checked_out"
    
    def test_09_booking_list_contains_ota_source(self, api_client):
        """Verify bookings list returns ota_source field"""
        response = api_client.get(f"{BASE_URL}/api/bookings")
        assert response.status_code == 200
        
        bookings = response.json()
        
        # Check that at least one booking has ota_source field
        has_source = [b for b in bookings if "ota_source" in b]
        print(f"✓ {len(has_source)}/{len(bookings)} bookings have ota_source field")
        
        # All our test bookings should have it
        test_bookings = [b for b in bookings if b.get("guest_name", "").startswith("TEST_")]
        for tb in test_bookings:
            assert "ota_source" in tb, f"Test booking {tb.get('id')} missing ota_source"
            assert tb["ota_source"] == "manual"
    
    def test_10_checkout_before_checkin_rejected(self, api_client):
        """POST /api/bookings should reject checkout before check-in"""
        checkin = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")  # Before check-in!
        
        payload = {
            "property_id": PROPERTY_ID,
            "guest_name": "TEST_Invalid Dates Guest",
            "check_in": checkin,
            "check_out": checkout,
            "total_amount": 100,
            "guests_count": 1
        }
        
        response = api_client.post(f"{BASE_URL}/api/bookings", json=payload)
        assert response.status_code == 400, f"Expected 400 for invalid dates, got {response.status_code}"
        print(f"✓ Checkout before check-in correctly rejected")
    
    def test_99_cleanup(self, api_client, cleanup_ids):
        """Cleanup test data"""
        deleted = 0
        for booking_id in cleanup_ids:
            try:
                # Note: Need admin to delete
                response = api_client.delete(f"{BASE_URL}/api/bookings/{booking_id}")
                if response.status_code in [200, 204]:
                    deleted += 1
            except Exception as e:
                print(f"Cleanup error for {booking_id}: {e}")
        
        print(f"✓ Cleanup: Deleted {deleted}/{len(cleanup_ids)} test bookings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
