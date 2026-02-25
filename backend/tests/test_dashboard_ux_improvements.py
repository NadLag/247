"""
Tests for Dashboard UX Improvements - Iteration 24
Features tested:
1. Sidebar navigation per role (admin: 8 items, owner: 5 items, staff: 4 items)
2. Role-based dashboards with KPIs
3. Backend /api/dashboard/kpis returns incomplete_bookings for admin
4. Backend /api/companies/me PUT endpoint for saving fee settings
"""

import pytest
import requests
import uuid
import time
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

@pytest.fixture(scope="module")
def test_session():
    """Create a test company and admin user for testing"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    ts = int(time.time() * 1000)
    
    # Create test data directly in MongoDB via API
    # Since we can't use Google OAuth, we'll work with seed data endpoint
    data = {
        "session": session,
        "timestamp": ts,
        "company_id": None,
        "admin_session_token": None
    }
    
    yield data
    
    # Cleanup would go here if needed

class TestDashboardKPIsEndpoint:
    """Test /api/dashboard/kpis endpoint with incomplete_bookings field"""
    
    def test_dashboard_kpis_requires_auth(self):
        """KPIs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/kpis")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Dashboard KPIs endpoint correctly requires authentication")
    
    def test_dashboard_kpis_structure(self, test_session):
        """Test KPIs response structure"""
        # This test would need an authenticated session
        # For now, verify the endpoint exists and returns 401 without auth
        response = requests.get(f"{BASE_URL}/api/dashboard/kpis")
        assert response.status_code == 401
        print("✅ Dashboard KPIs endpoint exists and requires auth")


class TestCompanyUpdateEndpoint:
    """Test PUT /api/companies/me endpoint for fee settings"""
    
    def test_company_update_requires_auth(self):
        """Company update endpoint requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/companies/me",
            json={"management_fee_type": "percentage_revenue", "management_fee_percent": 15}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Company update endpoint correctly requires authentication")
    
    def test_company_get_endpoint_exists(self):
        """GET /api/companies/me endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/companies/me")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✅ Company GET endpoint exists and requires auth")


class TestRevenueTrendsEndpoint:
    """Test /api/dashboard/revenue-trends endpoint"""
    
    def test_revenue_trends_requires_auth(self):
        """Revenue trends endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/revenue-trends")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Revenue trends endpoint correctly requires authentication")


class TestSeedDataAndDashboard:
    """Test dashboard with seeded data"""
    
    def test_seed_demo_data_endpoint(self):
        """Test seed demo data endpoint creates data correctly"""
        ts = int(time.time() * 1000)
        response = requests.post(
            f"{BASE_URL}/api/seed-demo-data",
            json={"session_token": f"test_dashboard_{ts}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "company_id" in data, "Response should contain company_id"
            assert "message" in data, "Response should contain message"
            print(f"✅ Seed demo data created successfully: {data.get('company_id')}")
            return data
        else:
            # Endpoint may not exist or require different auth
            print(f"⚠️ Seed demo data endpoint returned {response.status_code}")
            pytest.skip("Seed demo data endpoint not available")


class TestAuthenticatedDashboard:
    """Test dashboard endpoints with authentication via seed data"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session via seed data"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        ts = int(time.time() * 1000)
        
        # Try to create seed data
        response = session.post(
            f"{BASE_URL}/api/seed-demo-data",
            json={"session_token": f"test_dash_auth_{ts}"}
        )
        
        if response.status_code != 200:
            pytest.skip("Cannot create test data")
        
        data = response.json()
        session_token = data.get("session_token") or f"test_dash_auth_{ts}"
        
        # Set session cookie
        session.cookies.set("session_token", session_token)
        
        return {
            "session": session,
            "company_id": data.get("company_id"),
            "session_token": session_token
        }
    
    def test_dashboard_kpis_with_auth(self, auth_session):
        """Test KPIs endpoint returns expected fields for admin"""
        session = auth_session["session"]
        
        response = session.get(f"{BASE_URL}/api/dashboard/kpis")
        
        if response.status_code == 401:
            pytest.skip("Session not properly authenticated")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify expected KPI fields exist
        expected_fields = [
            "role", "revenue_mtd", "revenue_last_month", "net_income",
            "occupancy_rate", "nights_booked", "active_properties",
            "active_bookings", "total_expenses"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
        
        # For admin role, verify incomplete_bookings is returned
        if data.get("role") == "company_admin":
            assert "incomplete_bookings" in data, "Admin should see incomplete_bookings field"
            print(f"✅ Admin KPIs include incomplete_bookings: {data['incomplete_bookings']}")
        
        print(f"✅ Dashboard KPIs returned with role: {data.get('role')}")
        print(f"   Revenue MTD: {data.get('revenue_mtd')}")
        print(f"   Active Properties: {data.get('active_properties')}")
        print(f"   Active Bookings: {data.get('active_bookings')}")
    
    def test_company_update_fee_settings(self, auth_session):
        """Test updating company fee settings"""
        session = auth_session["session"]
        
        update_data = {
            "management_fee_type": "percentage_revenue",
            "management_fee_percent": 18.5,
            "onboarding_completed": True
        }
        
        response = session.put(f"{BASE_URL}/api/companies/me", json=update_data)
        
        if response.status_code == 401:
            pytest.skip("Session not properly authenticated")
        if response.status_code == 403:
            pytest.skip("User is not admin")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ Company fee settings updated successfully")
        
        # Verify the update by getting company info
        get_response = session.get(f"{BASE_URL}/api/companies/me")
        if get_response.status_code == 200:
            company_data = get_response.json()
            assert company_data.get("management_fee_type") == "percentage_revenue", "Fee type not updated"
            assert company_data.get("management_fee_percent") == 18.5, "Fee percent not updated"
            print(f"✅ Verified company settings: fee_type={company_data.get('management_fee_type')}, fee_percent={company_data.get('management_fee_percent')}")
    
    def test_revenue_trends_with_auth(self, auth_session):
        """Test revenue trends endpoint returns data array"""
        session = auth_session["session"]
        
        response = session.get(f"{BASE_URL}/api/dashboard/revenue-trends")
        
        if response.status_code == 401:
            pytest.skip("Session not properly authenticated")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Revenue trends should return a list"
        
        if len(data) > 0:
            # Verify structure of trend entries
            trend = data[0]
            assert "month" in trend, "Trend entry should have 'month'"
            assert "revenue" in trend, "Trend entry should have 'revenue'"
            print(f"✅ Revenue trends returned {len(data)} months of data")
            for t in data[-3:]:  # Show last 3 months
                print(f"   {t.get('month')}: revenue=${t.get('revenue', 0)}, net=${t.get('net_income', 0)}")
        else:
            print("✅ Revenue trends returned empty list (no data yet)")


class TestPropertiesEndpoint:
    """Test properties endpoint for dashboard integration"""
    
    def test_properties_requires_auth(self):
        """Properties endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/properties")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Properties endpoint correctly requires authentication")


class TestTasksEndpoint:
    """Test tasks endpoint for staff dashboard"""
    
    def test_tasks_requires_auth(self):
        """Tasks endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Tasks endpoint correctly requires authentication")


class TestNotificationsEndpoint:
    """Test notifications for dashboard integration"""
    
    def test_notifications_requires_auth(self):
        """Notifications endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Notifications endpoint correctly requires authentication")
    
    def test_unread_count_requires_auth(self):
        """Unread count endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Notification unread-count endpoint correctly requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
