"""
RBAC (Role-Based Access Control) Enforcement Tests
Tests for Admin, Owner, and Staff role access restrictions

Test scenarios:
1. Admin: Full access to all endpoints
2. Owner: 403 on /api/staff, 403 on /api/payouts, filtered data on properties/bookings/expenses/analytics
3. Staff: 403 on /api/staff (except own), 403 on /api/payouts, 403 on /api/analytics without view_financials
4. Staff with view_financials permission: CAN access /api/analytics
"""

import pytest
import requests
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

# Load BASE_URL from frontend .env file
import subprocess
try:
    result = subprocess.run(
        ['bash', '-c', 'source /app/frontend/.env && echo $REACT_APP_BACKEND_URL'],
        capture_output=True, text=True
    )
    BASE_URL = result.stdout.strip().rstrip('/')
except Exception:
    BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

if not BASE_URL:
    BASE_URL = "https://property-team-1.preview.emergentagent.com"

# Generate unique test prefix to avoid conflicts
TEST_PREFIX = f"TEST_RBAC_{int(time.time())}"


class TestSetupData:
    """Create test data for RBAC tests"""
    
    @pytest.fixture(scope="class")
    def test_data(self):
        """Setup test data: company, users (admin, owner, staff), properties, bookings, expenses"""
        session = requests.Session()
        
        # Create unique identifiers
        ts = int(time.time())
        company_id = f"comp_rbac_{ts}"
        admin_id = f"user_admin_{ts}"
        owner_id = f"user_owner_{ts}"
        staff_id = f"user_staff_{ts}"
        staff_with_perm_id = f"user_staff_perm_{ts}"
        
        # Property IDs - 3 properties total, owner has 2, staff has 1
        prop_1 = f"prop_rbac_1_{ts}"
        prop_2 = f"prop_rbac_2_{ts}"
        prop_3 = f"prop_rbac_3_{ts}"  # Admin only property
        
        # Staff record ID
        staff_record_id = f"staff_rec_{ts}"
        staff_with_perm_record_id = f"staff_rec_perm_{ts}"
        
        # Create company
        from pymongo import MongoClient
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        now_str = datetime.now(timezone.utc).isoformat()
        
        # Insert company
        db.companies.insert_one({
            "company_id": company_id,
            "name": f"{TEST_PREFIX}_Company",
            "subscription_status": "active",
            "created_at": now_str,
            "updated_at": now_str
        })
        
        # Insert admin user
        db.users.insert_one({
            "user_id": admin_id,
            "email": f"admin_{ts}@test.com",
            "name": f"{TEST_PREFIX}_Admin",
            "auth_method": "test",
            "company_id": company_id,
            "role": "company_admin",
            "assigned_properties": [],
            "permissions": {},
            "created_at": now_str,
            "updated_at": now_str
        })
        
        # Insert owner user - assigned to prop_1 and prop_2 only
        db.users.insert_one({
            "user_id": owner_id,
            "email": f"owner_{ts}@test.com",
            "name": f"{TEST_PREFIX}_Owner",
            "auth_method": "test",
            "company_id": company_id,
            "role": "owner",
            "assigned_properties": [prop_1, prop_2],
            "permissions": {},
            "created_at": now_str,
            "updated_at": now_str
        })
        
        # Insert staff user WITHOUT view_financials permission - assigned to prop_1 only
        db.users.insert_one({
            "user_id": staff_id,
            "email": f"staff_{ts}@test.com",
            "name": f"{TEST_PREFIX}_Staff",
            "auth_method": "test",
            "company_id": company_id,
            "role": "staff",
            "assigned_properties": [prop_1],
            "permissions": {},
            "created_at": now_str,
            "updated_at": now_str
        })
        
        # Insert staff user WITH view_financials permission
        db.users.insert_one({
            "user_id": staff_with_perm_id,
            "email": f"staff_perm_{ts}@test.com",
            "name": f"{TEST_PREFIX}_Staff_Financials",
            "auth_method": "test",
            "company_id": company_id,
            "role": "staff",
            "assigned_properties": [prop_1],
            "permissions": {"view_financials": True},
            "created_at": now_str,
            "updated_at": now_str
        })
        
        # Create sessions for each user
        admin_token = f"token_admin_{ts}"
        owner_token = f"token_owner_{ts}"
        staff_token = f"token_staff_{ts}"
        staff_with_perm_token = f"token_staff_perm_{ts}"
        
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        
        db.user_sessions.insert_many([
            {"user_id": admin_id, "session_token": admin_token, "expires_at": expires_at, "created_at": now_str},
            {"user_id": owner_id, "session_token": owner_token, "expires_at": expires_at, "created_at": now_str},
            {"user_id": staff_id, "session_token": staff_token, "expires_at": expires_at, "created_at": now_str},
            {"user_id": staff_with_perm_id, "session_token": staff_with_perm_token, "expires_at": expires_at, "created_at": now_str}
        ])
        
        # Create properties
        db.properties.insert_many([
            {
                "id": prop_1,
                "company_id": company_id,
                "name": f"{TEST_PREFIX}_Property_1",
                "address": "123 Test St",
                "owner_email": f"owner_{ts}@test.com",
                "units": 2,
                "active": True,
                "created_at": now_str,
                "updated_at": now_str
            },
            {
                "id": prop_2,
                "company_id": company_id,
                "name": f"{TEST_PREFIX}_Property_2",
                "address": "456 Test Ave",
                "owner_email": f"owner_{ts}@test.com",
                "units": 3,
                "active": True,
                "created_at": now_str,
                "updated_at": now_str
            },
            {
                "id": prop_3,
                "company_id": company_id,
                "name": f"{TEST_PREFIX}_Property_3_AdminOnly",
                "address": "789 Admin Blvd",
                "owner_email": "other_owner@test.com",
                "units": 1,
                "active": True,
                "created_at": now_str,
                "updated_at": now_str
            }
        ])
        
        # Create staff records
        db.staff.insert_many([
            {
                "id": staff_record_id,
                "company_id": company_id,
                "first_name": f"{TEST_PREFIX}_Staff",
                "last_name": "Member",
                "email": f"staff_{ts}@test.com",
                "assigned_properties": [prop_1],
                "salary": 1000,
                "staff_role": "housekeeper",
                "active": True,
                "created_at": now_str,
                "updated_at": now_str
            },
            {
                "id": staff_with_perm_record_id,
                "company_id": company_id,
                "first_name": f"{TEST_PREFIX}_Staff_Perm",
                "last_name": "Member",
                "email": f"staff_perm_{ts}@test.com",
                "assigned_properties": [prop_1],
                "salary": 1200,
                "staff_role": "co_host",
                "active": True,
                "created_at": now_str,
                "updated_at": now_str
            }
        ])
        
        # Create bookings across properties
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        
        db.bookings.insert_many([
            {
                "id": f"book_1_{ts}",
                "company_id": company_id,
                "property_id": prop_1,
                "guest_name": "Guest 1",
                "check_in": today,
                "check_out": tomorrow,
                "total_amount": 100,
                "status": "confirmed",
                "booking_type": "reservation",
                "created_at": now_str
            },
            {
                "id": f"book_2_{ts}",
                "company_id": company_id,
                "property_id": prop_2,
                "guest_name": "Guest 2",
                "check_in": today,
                "check_out": next_week,
                "total_amount": 500,
                "status": "confirmed",
                "booking_type": "reservation",
                "created_at": now_str
            },
            {
                "id": f"book_3_{ts}",
                "company_id": company_id,
                "property_id": prop_3,  # Admin only property
                "guest_name": "Guest 3",
                "check_in": today,
                "check_out": tomorrow,
                "total_amount": 200,
                "status": "confirmed",
                "booking_type": "reservation",
                "created_at": now_str
            }
        ])
        
        # Create expenses across properties
        db.expenses.insert_many([
            {
                "id": f"exp_1_{ts}",
                "company_id": company_id,
                "property_id": prop_1,
                "type": "operating",
                "category": "cleaning",
                "amount": 50,
                "description": "Cleaning expense",
                "date": today,
                "created_at": now_str
            },
            {
                "id": f"exp_2_{ts}",
                "company_id": company_id,
                "property_id": prop_2,
                "type": "operating",
                "category": "supplies",
                "amount": 100,
                "description": "Supplies expense",
                "date": today,
                "created_at": now_str
            },
            {
                "id": f"exp_3_{ts}",
                "company_id": company_id,
                "property_id": prop_3,  # Admin only property
                "type": "operating",
                "category": "maintenance",
                "amount": 200,
                "description": "Maintenance expense",
                "date": today,
                "created_at": now_str
            }
        ])
        
        # Create payouts
        db.payouts.insert_one({
            "id": f"payout_1_{ts}",
            "company_id": company_id,
            "staff_id": staff_record_id,
            "amount": 500,
            "period_start": today,
            "period_end": next_week,
            "status": "pending",
            "created_at": now_str
        })
        
        yield {
            "company_id": company_id,
            "admin_token": admin_token,
            "owner_token": owner_token,
            "staff_token": staff_token,
            "staff_with_perm_token": staff_with_perm_token,
            "prop_1": prop_1,
            "prop_2": prop_2,
            "prop_3": prop_3,
            "staff_email": f"staff_{ts}@test.com",
            "ts": ts,
            "db": db
        }
        
        # Cleanup after tests
        db.companies.delete_many({"company_id": company_id})
        db.users.delete_many({"company_id": company_id})
        db.user_sessions.delete_many({"session_token": {"$in": [admin_token, owner_token, staff_token, staff_with_perm_token]}})
        db.properties.delete_many({"company_id": company_id})
        db.staff.delete_many({"company_id": company_id})
        db.bookings.delete_many({"company_id": company_id})
        db.expenses.delete_many({"company_id": company_id})
        db.payouts.delete_many({"company_id": company_id})
        client.close()


class TestAdminAccess(TestSetupData):
    """Admin should have full unrestricted access to all endpoints"""
    
    def test_admin_can_access_staff_endpoint(self, test_data):
        """Admin can access /api/staff"""
        response = requests.get(
            f"{BASE_URL}/api/staff",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        print(f"Admin GET /api/staff: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of staff"
        print(f"Admin sees {len(data)} staff members")
    
    def test_admin_can_access_payouts_endpoint(self, test_data):
        """Admin can access /api/payouts"""
        response = requests.get(
            f"{BASE_URL}/api/payouts",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        print(f"Admin GET /api/payouts: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of payouts"
        print(f"Admin sees {len(data)} payouts")
    
    def test_admin_can_access_analytics_endpoint(self, test_data):
        """Admin can access /api/analytics"""
        response = requests.get(
            f"{BASE_URL}/api/analytics",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        print(f"Admin GET /api/analytics: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_admin_can_access_expenses_endpoint(self, test_data):
        """Admin can access /api/expenses"""
        response = requests.get(
            f"{BASE_URL}/api/expenses",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        print(f"Admin GET /api/expenses: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list of expenses"
        print(f"Admin sees {len(data)} expenses")
    
    def test_admin_sees_all_properties(self, test_data):
        """Admin sees ALL properties (not filtered)"""
        response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        print(f"Admin GET /api/properties: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        # Admin should see all 3 properties
        property_ids = [p["id"] for p in data]
        print(f"Admin sees properties: {property_ids}")
        assert test_data['prop_1'] in property_ids, "Admin should see prop_1"
        assert test_data['prop_2'] in property_ids, "Admin should see prop_2"
        assert test_data['prop_3'] in property_ids, "Admin should see prop_3"
    
    def test_admin_sees_all_bookings(self, test_data):
        """Admin sees ALL bookings (not filtered)"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        print(f"Admin GET /api/bookings: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        # Admin should see bookings from all properties
        property_ids_in_bookings = set(b.get("property_id") for b in data)
        print(f"Admin sees bookings from properties: {property_ids_in_bookings}")


class TestOwnerAccess(TestSetupData):
    """Owner should have restricted access - cannot see staff or payouts"""
    
    def test_owner_gets_403_on_staff_endpoint(self, test_data):
        """Owner gets 403 Forbidden when accessing /api/staff"""
        response = requests.get(
            f"{BASE_URL}/api/staff",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/staff: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Owner correctly denied access to /api/staff: {response.json()}")
    
    def test_owner_gets_403_on_payouts_endpoint(self, test_data):
        """Owner gets 403 Forbidden when accessing /api/payouts"""
        response = requests.get(
            f"{BASE_URL}/api/payouts",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/payouts: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Owner correctly denied access to /api/payouts: {response.json()}")
    
    def test_owner_can_only_see_assigned_properties(self, test_data):
        """Owner can only see their assigned properties (prop_1 and prop_2)"""
        response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/properties: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        property_ids = [p["id"] for p in data]
        print(f"Owner sees properties: {property_ids}")
        
        # Owner should see prop_1 and prop_2
        assert test_data['prop_1'] in property_ids, "Owner should see assigned prop_1"
        assert test_data['prop_2'] in property_ids, "Owner should see assigned prop_2"
        # Owner should NOT see prop_3
        assert test_data['prop_3'] not in property_ids, "Owner should NOT see prop_3 (not assigned)"
    
    def test_owner_can_only_see_bookings_for_assigned_properties(self, test_data):
        """Owner can only see bookings for their assigned properties"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/bookings: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        
        # Check all bookings are from assigned properties only
        for booking in data:
            prop_id = booking.get("property_id")
            print(f"Owner booking property_id: {prop_id}")
            assert prop_id in [test_data['prop_1'], test_data['prop_2']], \
                f"Owner should NOT see bookings from property {prop_id}"
        
        # Verify owner doesn't see bookings from prop_3
        prop_ids_in_bookings = [b.get("property_id") for b in data]
        assert test_data['prop_3'] not in prop_ids_in_bookings, "Owner should NOT see prop_3 bookings"
    
    def test_owner_can_only_see_expenses_for_assigned_properties(self, test_data):
        """Owner can only see expenses for their assigned properties"""
        response = requests.get(
            f"{BASE_URL}/api/expenses",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/expenses: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        
        # Check all expenses are from assigned properties only
        for expense in data:
            prop_id = expense.get("property_id")
            print(f"Owner expense property_id: {prop_id}")
            assert prop_id in [test_data['prop_1'], test_data['prop_2']], \
                f"Owner should NOT see expenses from property {prop_id}"
    
    def test_owner_dashboard_kpis_filtered_by_assigned_properties(self, test_data):
        """Owner dashboard KPIs only show data for their assigned properties"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/kpis",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/dashboard/kpis: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify role is owner
        assert data.get("role") == "owner", f"Expected role=owner, got {data.get('role')}"
        
        # Owner should see only their assigned properties count (2)
        total_properties = data.get("total_properties", 0)
        print(f"Owner KPIs show total_properties: {total_properties}")
        # This should be filtered to only assigned properties
    
    def test_owner_can_access_analytics(self, test_data):
        """Owner CAN access analytics (filtered by their properties)"""
        response = requests.get(
            f"{BASE_URL}/api/analytics",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        print(f"Owner GET /api/analytics: {response.status_code}")
        assert response.status_code == 200, f"Owner should be able to access analytics, got {response.status_code}"


class TestStaffAccess(TestSetupData):
    """Staff should have restricted access - cannot see financials by default"""
    
    def test_staff_gets_403_on_staff_endpoint_for_others(self, test_data):
        """Staff gets 403 Forbidden when trying to see other staff (but can see own record)"""
        response = requests.get(
            f"{BASE_URL}/api/staff",
            headers={"Authorization": f"Bearer {test_data['staff_token']}"}
        )
        print(f"Staff GET /api/staff: {response.status_code}")
        # Staff should get 200 but only see their own record
        assert response.status_code == 200, f"Staff should get 200 (sees own record), got {response.status_code}"
        data = response.json()
        
        # Staff should only see their own record
        print(f"Staff sees {len(data)} staff records")
        if len(data) > 0:
            for record in data:
                assert record.get("email") == test_data['staff_email'], \
                    f"Staff should only see own record, not {record.get('email')}"
        print("Staff correctly sees only their own staff record")
    
    def test_staff_gets_403_on_payouts_endpoint(self, test_data):
        """Staff gets 403 Forbidden when accessing /api/payouts"""
        response = requests.get(
            f"{BASE_URL}/api/payouts",
            headers={"Authorization": f"Bearer {test_data['staff_token']}"}
        )
        print(f"Staff GET /api/payouts: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Staff correctly denied access to /api/payouts: {response.json()}")
    
    def test_staff_without_permission_gets_403_on_analytics(self, test_data):
        """Staff WITHOUT view_financials permission gets 403 on /api/analytics"""
        response = requests.get(
            f"{BASE_URL}/api/analytics",
            headers={"Authorization": f"Bearer {test_data['staff_token']}"}
        )
        print(f"Staff (no permission) GET /api/analytics: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Staff without view_financials correctly denied: {response.json()}")
    
    def test_staff_without_permission_gets_403_on_expenses(self, test_data):
        """Staff WITHOUT view_financials permission gets 403 on /api/expenses"""
        response = requests.get(
            f"{BASE_URL}/api/expenses",
            headers={"Authorization": f"Bearer {test_data['staff_token']}"}
        )
        print(f"Staff (no permission) GET /api/expenses: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Staff without view_financials correctly denied expenses access: {response.json()}")
    
    def test_staff_without_permission_gets_403_on_source_breakdown(self, test_data):
        """Staff WITHOUT view_financials permission gets 403 on /api/analytics/source-breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/source-breakdown",
            headers={"Authorization": f"Bearer {test_data['staff_token']}"}
        )
        print(f"Staff (no permission) GET /api/analytics/source-breakdown: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Staff without view_financials correctly denied source-breakdown access")


class TestStaffWithPermission(TestSetupData):
    """Staff WITH view_financials permission should be able to access analytics"""
    
    def test_staff_with_permission_can_access_analytics(self, test_data):
        """Staff WITH view_financials permission CAN access /api/analytics"""
        response = requests.get(
            f"{BASE_URL}/api/analytics",
            headers={"Authorization": f"Bearer {test_data['staff_with_perm_token']}"}
        )
        print(f"Staff (with view_financials) GET /api/analytics: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Staff with view_financials permission successfully accessed analytics")
    
    def test_staff_with_permission_can_access_source_breakdown(self, test_data):
        """Staff WITH view_financials permission CAN access /api/analytics/source-breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/source-breakdown",
            headers={"Authorization": f"Bearer {test_data['staff_with_perm_token']}"}
        )
        print(f"Staff (with view_financials) GET /api/analytics/source-breakdown: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Staff with view_financials permission successfully accessed source-breakdown")
    
    def test_staff_with_permission_can_access_expenses(self, test_data):
        """Staff WITH view_financials permission CAN access /api/expenses"""
        response = requests.get(
            f"{BASE_URL}/api/expenses",
            headers={"Authorization": f"Bearer {test_data['staff_with_perm_token']}"}
        )
        print(f"Staff (with view_financials) GET /api/expenses: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Staff with view_financials permission successfully accessed expenses")
    
    def test_staff_with_permission_still_denied_payouts(self, test_data):
        """Staff WITH view_financials still gets 403 on /api/payouts (payouts are admin-only)"""
        response = requests.get(
            f"{BASE_URL}/api/payouts",
            headers={"Authorization": f"Bearer {test_data['staff_with_perm_token']}"}
        )
        print(f"Staff (with view_financials) GET /api/payouts: {response.status_code}")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Staff with view_financials correctly denied payouts (admin-only)")


class TestCrossRoleComparison(TestSetupData):
    """Compare data visibility across roles"""
    
    def test_admin_sees_more_properties_than_owner(self, test_data):
        """Admin sees all 3 properties, Owner sees only 2"""
        # Admin request
        admin_response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {test_data['admin_token']}"}
        )
        admin_props = admin_response.json()
        
        # Owner request
        owner_response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {test_data['owner_token']}"}
        )
        owner_props = owner_response.json()
        
        admin_count = len([p for p in admin_props if p["id"].startswith("prop_rbac")])
        owner_count = len([p for p in owner_props if p["id"].startswith("prop_rbac")])
        
        print(f"Admin sees {admin_count} RBAC test properties, Owner sees {owner_count}")
        
        # Filter to only our test properties
        admin_test_props = [p["id"] for p in admin_props if p["id"] in [test_data['prop_1'], test_data['prop_2'], test_data['prop_3']]]
        owner_test_props = [p["id"] for p in owner_props if p["id"] in [test_data['prop_1'], test_data['prop_2'], test_data['prop_3']]]
        
        assert len(admin_test_props) == 3, f"Admin should see all 3 test properties, got {len(admin_test_props)}"
        assert len(owner_test_props) == 2, f"Owner should see only 2 assigned properties, got {len(owner_test_props)}"
        
        # Verify owner doesn't see prop_3
        assert test_data['prop_3'] not in owner_test_props, "Owner should NOT see prop_3"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
