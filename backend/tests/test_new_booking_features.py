"""
Test Suite for New Booking Features - Iteration 16
1. Past-date validation for BOTH check-in AND check-out dates
2. Source breakdown analytics endpoint with pie charts data
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Generate unique test identifiers
TS = str(int(datetime.now().timestamp() * 1000))

@pytest.fixture(scope="module")
def session():
    """Create requests session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="module")
def test_user(session):
    """Create test user with company via MongoDB"""
    import subprocess
    user_id = f"test-admin-{TS}"
    company_id = f"comp_{TS}"
    session_token = f"test_session_{TS}"
    
    script = f'''
    use('test_database');
    db.companies.insertOne({{
      company_id: "{company_id}",
      name: "Test Company {TS}",
      subscription_status: "trial",
      created_at: new Date(),
      updated_at: new Date()
    }});
    db.users.insertOne({{
      user_id: "{user_id}",
      email: "testadmin{TS}@example.com",
      name: "Test Admin {TS}",
      picture: "",
      company_id: "{company_id}",
      role: "company_admin",
      created_at: new Date(),
      updated_at: new Date()
    }});
    db.user_sessions.insertOne({{
      user_id: "{user_id}",
      session_token: "{session_token}",
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    print("OK");
    '''
    
    result = subprocess.run(["mongosh", "--quiet", "--eval", script], capture_output=True, text=True)
    assert "OK" in result.stdout or result.returncode == 0, f"MongoDB setup failed: {result.stderr}"
    
    return {
        "user_id": user_id,
        "company_id": company_id,
        "session_token": session_token
    }

@pytest.fixture(scope="module")
def auth_headers(test_user):
    """Get auth headers with session token"""
    return {"Authorization": f"Bearer {test_user['session_token']}"}

@pytest.fixture(scope="module")
def test_property(session, auth_headers, test_user):
    """Create test property for booking tests"""
    property_data = {
        "name": f"Test Property {TS}",
        "address": "123 Test St",
        "owner_first_name": "Test",
        "owner_last_name": "Owner",
        "owner_phone": "555-0123",
        "owner_email": f"owner{TS}@test.com",
        "units": 2
    }
    resp = session.post(f"{BASE_URL}/api/properties", json=property_data, headers=auth_headers)
    assert resp.status_code == 201, f"Failed to create property: {resp.text}"
    return resp.json()


class TestCheckoutPastDateValidation:
    """Test past-date validation for check-out date (new feature)"""
    
    def test_01_checkin_past_date_rejected(self, session, auth_headers, test_property):
        """POST /api/bookings should reject bookings with check-in date in the past"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        
        booking_data = {
            "property_id": test_property["id"],
            "guest_name": f"Test Guest Past CI {TS}",
            "check_in": yesterday,
            "check_out": future,
            "total_amount": 500,
            "guests_count": 2
        }
        resp = session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=auth_headers)
        
        assert resp.status_code == 400, f"Expected 400 for past check-in, got {resp.status_code}: {resp.text}"
        error = resp.json()
        assert "check-in" in error.get("detail", "").lower() or "past" in error.get("detail", "").lower(), \
            f"Error message should mention check-in/past: {error}"
        print(f"PASS: Past check-in date rejected with 400: {error.get('detail')}")

    def test_02_checkout_past_date_rejected(self, session, auth_headers, test_property):
        """POST /api/bookings should reject bookings with check-out date in the past"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        
        booking_data = {
            "property_id": test_property["id"],
            "guest_name": f"Test Guest Past CO {TS}",
            "check_in": two_days_ago,
            "check_out": yesterday,
            "total_amount": 300,
            "guests_count": 1
        }
        resp = session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=auth_headers)
        
        # Should be rejected - either for check-in or check-out being in past
        assert resp.status_code == 400, f"Expected 400 for past check-out, got {resp.status_code}: {resp.text}"
        error = resp.json()
        assert "past" in error.get("detail", "").lower(), \
            f"Error message should mention past date: {error}"
        print(f"PASS: Past checkout date rejected with 400: {error.get('detail')}")
    
    def test_03_only_checkout_past_rejected(self, session, auth_headers, test_property):
        """POST /api/bookings should reject even when only check-out is in the past (check-in is today)"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        booking_data = {
            "property_id": test_property["id"],
            "guest_name": f"Test Guest Only CO Past {TS}",
            "check_in": today,
            "check_out": yesterday,
            "total_amount": 200,
            "guests_count": 1
        }
        resp = session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=auth_headers)
        
        # Should be rejected - check-out before check-in or check-out in past
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        print(f"PASS: Check-out before check-in rejected with 400")

    def test_04_today_checkin_checkout_accepted(self, session, auth_headers, test_property):
        """POST /api/bookings should accept bookings with today and future dates"""
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        booking_data = {
            "property_id": test_property["id"],
            "guest_name": f"Test Guest Valid {TS}",
            "check_in": today,
            "check_out": future,
            "total_amount": 600,
            "guests_count": 2
        }
        resp = session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=auth_headers)
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        booking = resp.json()
        assert booking.get("check_in") == today
        assert booking.get("check_out") == future
        print(f"PASS: Today check-in and future check-out accepted (booking: {booking['id']})")
        return booking

    def test_05_future_dates_accepted(self, session, auth_headers, test_property):
        """POST /api/bookings should accept bookings with future check-in AND check-out dates"""
        future_ci = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        future_co = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        
        booking_data = {
            "property_id": test_property["id"],
            "guest_name": f"Test Guest Future {TS}",
            "check_in": future_ci,
            "check_out": future_co,
            "total_amount": 800,
            "guests_count": 3
        }
        resp = session.post(f"{BASE_URL}/api/bookings", json=booking_data, headers=auth_headers)
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        booking = resp.json()
        assert booking.get("check_in") == future_ci
        assert booking.get("check_out") == future_co
        print(f"PASS: Future check-in and check-out accepted (booking: {booking['id']})")


class TestSourceBreakdownEndpoint:
    """Test new /api/analytics/source-breakdown endpoint"""

    def test_06_source_breakdown_returns_data(self, session, auth_headers):
        """GET /api/analytics/source-breakdown should return source breakdown data"""
        resp = session.get(f"{BASE_URL}/api/analytics/source-breakdown", headers=auth_headers)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "sources" in data, "Response should contain 'sources' field"
        assert "total_bookings" in data, "Response should contain 'total_bookings' field"
        assert "total_revenue" in data, "Response should contain 'total_revenue' field"
        
        print(f"PASS: Source breakdown endpoint returns data structure")
        print(f"  - Total bookings: {data['total_bookings']}")
        print(f"  - Total revenue: ${data['total_revenue']}")
        print(f"  - Sources count: {len(data['sources'])}")

    def test_07_source_breakdown_structure(self, session, auth_headers):
        """GET /api/analytics/source-breakdown sources should have correct fields"""
        resp = session.get(f"{BASE_URL}/api/analytics/source-breakdown", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        # If sources exist, validate structure
        if data.get("sources"):
            source = data["sources"][0]
            required_fields = ["label", "key", "bookings", "revenue", "booking_pct", "revenue_pct"]
            for field in required_fields:
                assert field in source, f"Source missing required field: {field}"
            
            assert isinstance(source["bookings"], int), "bookings should be int"
            assert isinstance(source["revenue"], (int, float)), "revenue should be numeric"
            assert isinstance(source["booking_pct"], (int, float)), "booking_pct should be numeric"
            assert isinstance(source["revenue_pct"], (int, float)), "revenue_pct should be numeric"
            
            print(f"PASS: Source breakdown has correct field structure")
            for s in data["sources"][:3]:
                print(f"  - {s['label']}: {s['bookings']} bookings, ${s['revenue']} revenue, {s['booking_pct']}%")
        else:
            print("PASS: Source breakdown returns empty sources (no bookings for period)")

    def test_08_source_breakdown_with_year_filter(self, session, auth_headers):
        """GET /api/analytics/source-breakdown should accept year query param"""
        current_year = datetime.now().year
        resp = session.get(f"{BASE_URL}/api/analytics/source-breakdown?year={current_year}", headers=auth_headers)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "sources" in data
        print(f"PASS: Source breakdown accepts year filter (year={current_year})")

    def test_09_source_breakdown_with_month_filter(self, session, auth_headers):
        """GET /api/analytics/source-breakdown should accept month query param"""
        current_month = datetime.now().month
        resp = session.get(f"{BASE_URL}/api/analytics/source-breakdown?month={current_month}", headers=auth_headers)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "sources" in data
        print(f"PASS: Source breakdown accepts month filter (month={current_month})")

    def test_10_source_breakdown_with_property_filter(self, session, auth_headers, test_property):
        """GET /api/analytics/source-breakdown should accept property_id query param"""
        prop_id = test_property["id"]
        resp = session.get(f"{BASE_URL}/api/analytics/source-breakdown?property_id={prop_id}", headers=auth_headers)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "sources" in data
        print(f"PASS: Source breakdown accepts property_id filter ({prop_id})")

    def test_11_source_breakdown_with_all_filters(self, session, auth_headers, test_property):
        """GET /api/analytics/source-breakdown should accept all filters combined"""
        current_year = datetime.now().year
        current_month = datetime.now().month
        prop_id = test_property["id"]
        
        url = f"{BASE_URL}/api/analytics/source-breakdown?year={current_year}&month={current_month}&property_id={prop_id}"
        resp = session.get(url, headers=auth_headers)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "sources" in data
        assert "total_bookings" in data
        assert "total_revenue" in data
        print(f"PASS: Source breakdown accepts combined filters")
        print(f"  - URL: {url}")
        print(f"  - Results: {data['total_bookings']} bookings, ${data['total_revenue']} revenue")


class TestCleanup:
    """Cleanup test data"""
    
    def test_99_cleanup(self, test_user):
        """Clean up test data from MongoDB"""
        import subprocess
        company_id = test_user["company_id"]
        
        script = f'''
        use('test_database');
        db.bookings.deleteMany({{ company_id: "{company_id}" }});
        db.properties.deleteMany({{ company_id: "{company_id}" }});
        db.companies.deleteOne({{ company_id: "{company_id}" }});
        db.users.deleteMany({{ company_id: "{company_id}" }});
        db.user_sessions.deleteOne({{ session_token: "{test_user['session_token']}" }});
        print("Cleaned up");
        '''
        
        result = subprocess.run(["mongosh", "--quiet", "--eval", script], capture_output=True, text=True)
        print(f"PASS: Cleanup completed for company {company_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
