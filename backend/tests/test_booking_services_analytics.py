"""
Test suite for new features:
- Bookings by status (tabs: checked_in_today, upcoming, confirmed, checked_out, cancelled)
- Services CRUD (internal staff and external provider assignments)
- Analytics API (with property, year, month filters)
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = None
COMPANY_ID = None
TEST_PROPERTY_ID = None


@pytest.fixture(scope="module")
def api_session():
    """Create requests session with authorization"""
    global SESSION_TOKEN, COMPANY_ID, TEST_PROPERTY_ID
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Get existing session from environment or use test credentials
    SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_new_features_session_1771705659471')
    session.headers.update({"Authorization": f"Bearer {SESSION_TOKEN}"})
    
    # Verify session and get company_id
    resp = session.get(f"{BASE_URL}/api/auth/me")
    if resp.status_code == 200:
        user_data = resp.json()
        COMPANY_ID = user_data.get("company_id")
        
        # Get first property ID
        props_resp = session.get(f"{BASE_URL}/api/properties")
        if props_resp.status_code == 200 and props_resp.json():
            TEST_PROPERTY_ID = props_resp.json()[0]["id"]
    
    return session


class TestBookingsByStatus:
    """Test bookings by status API for tab navigation"""
    
    def test_get_bookings_by_status_returns_all_categories(self, api_session):
        """GET /api/bookings/by-status should return all 5 status categories"""
        response = api_session.get(f"{BASE_URL}/api/bookings/by-status")
        assert response.status_code == 200
        
        data = response.json()
        # Verify all required categories exist
        expected_categories = ["checked_in_today", "upcoming", "confirmed", "checked_out", "cancelled"]
        for category in expected_categories:
            assert category in data, f"Missing category: {category}"
            assert isinstance(data[category], list), f"Category {category} should be a list"
    
    def test_bookings_have_required_fields(self, api_session):
        """Verify bookings in by-status response have all required fields"""
        response = api_session.get(f"{BASE_URL}/api/bookings/by-status")
        assert response.status_code == 200
        
        data = response.json()
        # Find first non-empty category
        for category, bookings in data.items():
            if bookings:
                booking = bookings[0]
                required_fields = ["id", "company_id", "property_id", "guest_name", "check_in", "check_out", "total_amount", "status"]
                for field in required_fields:
                    assert field in booking, f"Booking missing field: {field}"
                break
    
    def test_bookings_sorted_correctly(self, api_session):
        """Verify bookings are sorted by check_in date"""
        response = api_session.get(f"{BASE_URL}/api/bookings/by-status")
        assert response.status_code == 200
        
        data = response.json()
        # Check upcoming bookings are sorted ascending by check_in
        upcoming = data.get("upcoming", [])
        if len(upcoming) > 1:
            dates = [b["check_in"] for b in upcoming]
            assert dates == sorted(dates), "Upcoming bookings should be sorted by check_in ascending"


class TestServicesCRUD:
    """Test Services CRUD endpoints"""
    
    def test_create_service_internal_provider(self, api_session):
        """POST /api/services with internal staff provider"""
        service_data = {
            "name": "TEST_Internal Service",
            "description": "Test internal service description",
            "category": "spa",
            "price": 100.00,
            "price_type": "per_person",
            "provider_type": "internal",
            "active": True
        }
        response = api_session.post(f"{BASE_URL}/api/services", json=service_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == service_data["name"]
        assert data["category"] == "spa"
        assert data["provider_type"] == "internal"
        assert data["price"] == 100.00
        assert "id" in data
        
        # Store for cleanup
        pytest.created_service_internal_id = data["id"]
    
    def test_create_service_external_provider(self, api_session):
        """POST /api/services with external third-party provider"""
        service_data = {
            "name": "TEST_External Service",
            "description": "Test external service description",
            "category": "excursions",
            "price": 150.00,
            "price_type": "per_person",
            "provider_type": "external",
            "external_provider_name": "External Tours Co",
            "external_provider_phone": "+1999888777",
            "external_provider_email": "test@externaltours.com",
            "active": True
        }
        response = api_session.post(f"{BASE_URL}/api/services", json=service_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["provider_type"] == "external"
        assert data["external_provider_name"] == "External Tours Co"
        assert data["external_provider_phone"] == "+1999888777"
        assert data["external_provider_email"] == "test@externaltours.com"
        
        pytest.created_service_external_id = data["id"]
    
    def test_list_services(self, api_session):
        """GET /api/services returns all services"""
        response = api_session.get(f"{BASE_URL}/api/services?active_only=false")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the services we created
        assert len(data) >= 1
    
    def test_filter_services_by_category(self, api_session):
        """GET /api/services with category filter"""
        response = api_session.get(f"{BASE_URL}/api/services?category=excursions&active_only=false")
        assert response.status_code == 200
        
        data = response.json()
        for service in data:
            assert service["category"] == "excursions"
    
    def test_update_service(self, api_session):
        """PUT /api/services/{id} updates service"""
        if not hasattr(pytest, 'created_service_internal_id'):
            pytest.skip("No service created to update")
        
        update_data = {
            "price": 120.00,
            "description": "Updated description"
        }
        response = api_session.put(
            f"{BASE_URL}/api/services/{pytest.created_service_internal_id}",
            json=update_data
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["price"] == 120.00
        assert data["description"] == "Updated description"
        
        # Verify with GET
        get_resp = api_session.get(f"{BASE_URL}/api/services?active_only=false")
        assert get_resp.status_code == 200
        services = get_resp.json()
        updated_service = next((s for s in services if s["id"] == pytest.created_service_internal_id), None)
        assert updated_service is not None
        assert updated_service["price"] == 120.00
    
    def test_delete_service(self, api_session):
        """DELETE /api/services/{id} deletes service"""
        if not hasattr(pytest, 'created_service_external_id'):
            pytest.skip("No service created to delete")
        
        response = api_session.delete(f"{BASE_URL}/api/services/{pytest.created_service_external_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Service deleted"
        
        # Verify deleted
        get_resp = api_session.get(f"{BASE_URL}/api/services?active_only=false")
        services = get_resp.json()
        assert not any(s["id"] == pytest.created_service_external_id for s in services)


class TestAnalyticsAPI:
    """Test Analytics API endpoint"""
    
    def test_analytics_returns_current_previous_trends(self, api_session):
        """GET /api/analytics returns current, previous, changes, and trends"""
        response = api_session.get(f"{BASE_URL}/api/analytics")
        assert response.status_code == 200
        
        data = response.json()
        assert "current" in data
        assert "previous" in data
        assert "changes" in data
        assert "trends" in data
        assert "period" in data
    
    def test_analytics_current_has_required_kpis(self, api_session):
        """Verify current metrics contain all 8 KPIs"""
        response = api_session.get(f"{BASE_URL}/api/analytics")
        assert response.status_code == 200
        
        current = response.json()["current"]
        required_kpis = [
            "revenue", "net_income", "occupancy_rate", "nights_booked",
            "adr", "revpan", "active_properties", "total_bookings"
        ]
        for kpi in required_kpis:
            assert kpi in current, f"Missing KPI: {kpi}"
    
    def test_analytics_property_filter(self, api_session):
        """GET /api/analytics with property_id filter"""
        if not TEST_PROPERTY_ID:
            pytest.skip("No property available for filtering")
        
        response = api_session.get(f"{BASE_URL}/api/analytics?property_id={TEST_PROPERTY_ID}")
        assert response.status_code == 200
        
        data = response.json()
        # When filtered by one property, should show only that property
        assert data["current"]["active_properties"] <= 1
    
    def test_analytics_year_filter(self, api_session):
        """GET /api/analytics with year filter"""
        response = api_session.get(f"{BASE_URL}/api/analytics?year=2026")
        assert response.status_code == 200
        
        data = response.json()
        assert "current" in data
    
    def test_analytics_month_filter(self, api_session):
        """GET /api/analytics with month filter"""
        response = api_session.get(f"{BASE_URL}/api/analytics?year=2026&month=1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period"]["current_month"] == "January 2026"
    
    def test_analytics_trends_has_12_months(self, api_session):
        """Verify trends array contains 12 months of data"""
        response = api_session.get(f"{BASE_URL}/api/analytics")
        assert response.status_code == 200
        
        trends = response.json()["trends"]
        assert len(trends) == 12, "Trends should have 12 months"
        
        # Each trend should have required fields
        for trend in trends:
            assert "month" in trend
            assert "revenue" in trend
            assert "occupancy_rate" in trend
            assert "adr" in trend
    
    def test_analytics_changes_calculated(self, api_session):
        """Verify percentage changes are calculated"""
        response = api_session.get(f"{BASE_URL}/api/analytics")
        assert response.status_code == 200
        
        changes = response.json()["changes"]
        expected_changes = ["revenue_change", "expenses_change", "occupancy_change", "adr_change", "bookings_change"]
        for change in expected_changes:
            assert change in changes, f"Missing change: {change}"


class TestServicesCategories:
    """Test service categories functionality"""
    
    def test_all_service_categories(self, api_session):
        """Verify all category values are accepted"""
        categories = ["airport_transfer", "meals", "excursions", "spa", "transport", "other"]
        
        for category in categories:
            service_data = {
                "name": f"TEST_Category_{category}",
                "description": f"Test {category} service",
                "category": category,
                "price": 50.00,
                "price_type": "fixed",
                "provider_type": "internal",
                "active": True
            }
            response = api_session.post(f"{BASE_URL}/api/services", json=service_data)
            assert response.status_code == 201, f"Failed to create service with category: {category}"
            
            # Clean up
            service_id = response.json()["id"]
            api_session.delete(f"{BASE_URL}/api/services/{service_id}")


class TestCleanup:
    """Clean up test data"""
    
    def test_cleanup_internal_service(self, api_session):
        """Delete internal service created in tests"""
        if hasattr(pytest, 'created_service_internal_id'):
            response = api_session.delete(f"{BASE_URL}/api/services/{pytest.created_service_internal_id}")
            # May already be deleted or not exist, either is fine
            assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
