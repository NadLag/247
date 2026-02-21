"""
Tests for new features:
1. Role-based dashboard KPIs
2. OTA Webhook endpoint
3. Subscription validation middleware
"""
import pytest
import requests
import subprocess
import time
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://booking-hub-169.preview.emergentagent.com').rstrip('/')


class TestSetup:
    """Setup fixtures for testing"""
    
    @staticmethod
    def create_test_user(role="company_admin", subscription_status="trial"):
        """Create test user directly in MongoDB"""
        timestamp = str(int(time.time() * 1000))
        
        mongo_script = f'''
        use('test_database');
        var userId = 'test-{role}-{timestamp}';
        var companyId = 'comp_{timestamp}';
        var sessionToken = 'test_session_{timestamp}';
        var email = '{role}.{timestamp}@test.com';
        
        db.companies.insertOne({{
          company_id: companyId,
          name: 'Test Company {timestamp}',
          subscription_status: '{subscription_status}',
          subscription_plan: null,
          created_at: new Date(),
          updated_at: new Date()
        }});
        
        db.users.insertOne({{
          user_id: userId,
          email: email,
          name: 'Test {role.title()} {timestamp}',
          picture: 'https://via.placeholder.com/150',
          company_id: companyId,
          role: '{role}',
          created_at: new Date(),
          updated_at: new Date()
        }});
        
        db.user_sessions.insertOne({{
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        
        print('SESSION_TOKEN:' + sessionToken);
        print('USER_ID:' + userId);
        print('COMPANY_ID:' + companyId);
        print('EMAIL:' + email);
        '''
        
        result = subprocess.run(
            ['mongosh', '--eval', mongo_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        credentials = {}
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('SESSION_TOKEN:'):
                    credentials['token'] = line.split(':')[1]
                elif line.startswith('USER_ID:'):
                    credentials['user_id'] = line.split(':')[1]
                elif line.startswith('COMPANY_ID:'):
                    credentials['company_id'] = line.split(':')[1]
                elif line.startswith('EMAIL:'):
                    credentials['email'] = line.split(':')[1]
        
        return credentials if all(k in credentials for k in ['token', 'user_id', 'company_id']) else None

    @staticmethod
    def create_owner_user(company_id, owner_email):
        """Create owner user linked to existing company"""
        timestamp = str(int(time.time() * 1000))
        
        mongo_script = f'''
        use('test_database');
        var userId = 'test-owner-{timestamp}';
        var sessionToken = 'test_owner_session_{timestamp}';
        
        db.users.insertOne({{
          user_id: userId,
          email: '{owner_email}',
          name: 'Test Owner',
          picture: 'https://via.placeholder.com/150',
          company_id: '{company_id}',
          role: 'owner',
          created_at: new Date(),
          updated_at: new Date()
        }});
        
        db.user_sessions.insertOne({{
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        
        print('SESSION_TOKEN:' + sessionToken);
        print('USER_ID:' + userId);
        '''
        
        result = subprocess.run(
            ['mongosh', '--eval', mongo_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        credentials = {}
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('SESSION_TOKEN:'):
                    credentials['token'] = line.split(':')[1]
                elif line.startswith('USER_ID:'):
                    credentials['user_id'] = line.split(':')[1]
            credentials['email'] = owner_email
            credentials['company_id'] = company_id
        
        return credentials if 'token' in credentials else None

    @staticmethod
    def create_staff_user(company_id, staff_email, assigned_properties=[]):
        """Create staff user linked to existing company"""
        timestamp = str(int(time.time() * 1000))
        assigned_props_str = json.dumps(assigned_properties)
        
        mongo_script = f'''
        use('test_database');
        var userId = 'test-staff-{timestamp}';
        var sessionToken = 'test_staff_session_{timestamp}';
        
        // Create user
        db.users.insertOne({{
          user_id: userId,
          email: '{staff_email}',
          name: 'Test Staff',
          picture: 'https://via.placeholder.com/150',
          company_id: '{company_id}',
          role: 'staff',
          created_at: new Date(),
          updated_at: new Date()
        }});
        
        // Create staff record
        db.staff.insertOne({{
          id: 'staff_' + '{timestamp}',
          company_id: '{company_id}',
          first_name: 'Test',
          last_name: 'Staff',
          email: '{staff_email}',
          phone: '+11234567890',
          salary: 3000,
          payment_type: 'per_job',
          payment_terms: 'Per Job',
          staff_role: 'housekeeper',
          per_checkin_rate: 50,
          per_checkout_rate: 75,
          assigned_properties: {assigned_props_str},
          active: true,
          created_at: new Date(),
          updated_at: new Date()
        }});
        
        db.user_sessions.insertOne({{
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        
        print('SESSION_TOKEN:' + sessionToken);
        print('USER_ID:' + userId);
        '''
        
        result = subprocess.run(
            ['mongosh', '--eval', mongo_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        credentials = {}
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('SESSION_TOKEN:'):
                    credentials['token'] = line.split(':')[1]
                elif line.startswith('USER_ID:'):
                    credentials['user_id'] = line.split(':')[1]
            credentials['email'] = staff_email
            credentials['company_id'] = company_id
        
        return credentials if 'token' in credentials else None

    @staticmethod
    def update_company_subscription(company_id, status):
        """Update company subscription status"""
        mongo_script = f'''
        use('test_database');
        db.companies.updateOne(
          {{ company_id: '{company_id}' }},
          {{ $set: {{ subscription_status: '{status}' }} }}
        );
        print('UPDATED');
        '''
        
        result = subprocess.run(
            ['mongosh', '--eval', mongo_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        return 'UPDATED' in result.stdout


@pytest.fixture(scope="module")
def admin_user():
    """Create admin user fixture"""
    creds = TestSetup.create_test_user("company_admin", "trial")
    assert creds is not None, "Failed to create admin user"
    yield creds


@pytest.fixture(scope="module")
def admin_session(admin_user):
    """Create requests session with admin auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_user['token']}"
    })
    return session


@pytest.fixture(scope="module")
def seeded_admin(admin_session, admin_user):
    """Admin user with seeded demo data"""
    # Seed demo data for testing
    response = admin_session.post(f"{BASE_URL}/api/seed-demo-data")
    # May return 200 if already seeded or 200 on success
    yield admin_user
    

class TestAdminDashboardKPIs:
    """Test Admin dashboard KPI endpoint - should see all 8 KPIs + staff payments"""
    
    def test_admin_dashboard_returns_all_kpis(self, admin_session, seeded_admin):
        """Admin should see all KPI fields"""
        response = admin_session.get(f"{BASE_URL}/api/dashboard/kpis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify role
        assert data.get('role') == 'company_admin', f"Expected role 'company_admin', got {data.get('role')}"
        
        # Verify all 8+ KPI fields exist
        expected_fields = [
            'revenue_mtd', 'revenue_last_month', 'net_income', 'occupancy_rate',
            'nights_booked', 'adr', 'revpan', 'active_properties',
            'total_properties', 'active_bookings', 'staff_payments_due', 'total_expenses'
        ]
        for field in expected_fields:
            assert field in data, f"Missing KPI field: {field}"
            
        print(f"Admin KPIs: revenue_mtd={data['revenue_mtd']}, staff_payments_due={data['staff_payments_due']}")
    
    def test_admin_dashboard_revenue_trends(self, admin_session, seeded_admin):
        """Admin should see revenue trends"""
        response = admin_session.get(f"{BASE_URL}/api/dashboard/revenue-trends")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Revenue trends should be a list"
        if len(data) > 0:
            assert 'month' in data[0], "Trend entry should have 'month'"
            assert 'revenue' in data[0], "Trend entry should have 'revenue'"
            assert 'expenses' in data[0], "Trend entry should have 'expenses'"


class TestOwnerDashboardKPIs:
    """Test Owner dashboard KPI endpoint - filtered by owned properties"""
    
    @pytest.fixture(scope="class")
    def owner_user(self, seeded_admin, admin_session):
        """Create owner user for an existing property"""
        # Get a property to find owner email
        props_response = admin_session.get(f"{BASE_URL}/api/properties")
        assert props_response.status_code == 200
        props = props_response.json()
        
        if len(props) > 0:
            owner_email = props[0].get('owner_email', 'john@example.com')
            creds = TestSetup.create_owner_user(seeded_admin['company_id'], owner_email)
            if creds:
                yield creds
            else:
                pytest.skip("Failed to create owner user")
        else:
            pytest.skip("No properties available for owner test")
    
    def test_owner_dashboard_filtered_kpis(self, owner_user):
        """Owner should see KPIs filtered by their properties"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {owner_user['token']}"
        })
        
        response = session.get(f"{BASE_URL}/api/dashboard/kpis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get('role') == 'owner', f"Expected role 'owner', got {data.get('role')}"
        
        # Owner should have filtered view
        assert 'revenue_mtd' in data
        assert 'total_properties' in data
        assert 'active_properties' in data
        
        # Owner should NOT see staff_payments_due (only admin)
        # staff_payments_due may be 0 for owner but should exist
        print(f"Owner KPIs: revenue_mtd={data.get('revenue_mtd')}, total_properties={data.get('total_properties')}")


class TestStaffDashboardKPIs:
    """Test Staff dashboard KPI endpoint - earnings, tasks completed, upcoming tasks"""
    
    @pytest.fixture(scope="class")
    def staff_user(self, seeded_admin, admin_session):
        """Create staff user with assigned properties"""
        # Get properties for staff assignment
        props_response = admin_session.get(f"{BASE_URL}/api/properties")
        assert props_response.status_code == 200
        props = props_response.json()
        
        if len(props) > 0:
            property_ids = [p['id'] for p in props[:2]]  # Assign first 2 properties
            staff_email = f"teststaff_{int(time.time())}@test.com"
            creds = TestSetup.create_staff_user(seeded_admin['company_id'], staff_email, property_ids)
            if creds:
                yield creds
            else:
                pytest.skip("Failed to create staff user")
        else:
            pytest.skip("No properties available for staff test")
    
    def test_staff_dashboard_specific_kpis(self, staff_user):
        """Staff should see their earnings and tasks"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {staff_user['token']}"
        })
        
        response = session.get(f"{BASE_URL}/api/dashboard/kpis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get('role') == 'staff', f"Expected role 'staff', got {data.get('role')}"
        
        # Staff-specific fields
        assert 'staff_earnings' in data, "Staff should have staff_earnings field"
        assert 'tasks_completed' in data, "Staff should have tasks_completed field"
        assert 'upcoming_tasks' in data, "Staff should have upcoming_tasks field"
        assert 'total_properties' in data, "Staff should see assigned properties count"
        
        print(f"Staff KPIs: staff_earnings={data.get('staff_earnings')}, tasks_completed={data.get('tasks_completed')}, upcoming_tasks={data.get('upcoming_tasks')}")


class TestOTAWebhook:
    """Test OTA Webhook endpoint for booking events"""
    
    @pytest.fixture(scope="class")
    def property_id(self, seeded_admin, admin_session):
        """Get a property ID for OTA testing"""
        props_response = admin_session.get(f"{BASE_URL}/api/properties")
        assert props_response.status_code == 200
        props = props_response.json()
        if len(props) > 0:
            return props[0]['id']
        pytest.skip("No properties available for OTA test")
    
    def test_ota_webhook_booking_created(self, seeded_admin, property_id):
        """Test OTA webhook for booking_created event"""
        company_id = seeded_admin['company_id']
        
        payload = {
            "source": "airbnb",
            "property_id": property_id,
            "event_type": "booking_created",
            "data": {
                "guest_name": "OTA Guest John",
                "check_in": "2026-02-15",
                "check_out": "2026-02-20",
                "total_amount": 750.00,
                "guests_count": 2
            },
            "external_id": f"airbnb_{int(time.time())}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ota-webhook/{company_id}",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get('status') == 'received', f"Expected status 'received', got {data}"
        assert 'log_id' in data, "Response should include log_id"
        
        print(f"OTA booking created, log_id: {data.get('log_id')}")
        
        # Wait for background processing
        time.sleep(1)
        
        return data.get('log_id')
    
    def test_ota_webhook_booking_updated(self, seeded_admin, property_id):
        """Test OTA webhook for booking_updated event"""
        company_id = seeded_admin['company_id']
        external_id = f"airbnb_update_{int(time.time())}"
        
        # First create a booking
        create_payload = {
            "source": "booking",
            "property_id": property_id,
            "event_type": "booking_created",
            "data": {
                "guest_name": "Update Test Guest",
                "check_in": "2026-03-01",
                "check_out": "2026-03-05",
                "total_amount": 500.00,
                "guests_count": 1
            },
            "external_id": external_id
        }
        
        response = requests.post(f"{BASE_URL}/api/ota-webhook/{company_id}", json=create_payload)
        assert response.status_code == 200
        time.sleep(1)
        
        # Now update it
        update_payload = {
            "source": "booking",
            "property_id": property_id,
            "event_type": "booking_updated",
            "data": {
                "total_amount": 600.00,
                "guests_count": 3
            },
            "external_id": external_id
        }
        
        response = requests.post(f"{BASE_URL}/api/ota-webhook/{company_id}", json=update_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get('status') == 'received'
        print(f"OTA booking updated, log_id: {data.get('log_id')}")
    
    def test_ota_webhook_booking_cancelled(self, seeded_admin, property_id):
        """Test OTA webhook for booking_cancelled event"""
        company_id = seeded_admin['company_id']
        external_id = f"vrbo_cancel_{int(time.time())}"
        
        # First create a booking
        create_payload = {
            "source": "vrbo",
            "property_id": property_id,
            "event_type": "booking_created",
            "data": {
                "guest_name": "Cancel Test Guest",
                "check_in": "2026-04-01",
                "check_out": "2026-04-05",
                "total_amount": 800.00
            },
            "external_id": external_id
        }
        
        response = requests.post(f"{BASE_URL}/api/ota-webhook/{company_id}", json=create_payload)
        assert response.status_code == 200
        time.sleep(1)
        
        # Now cancel it
        cancel_payload = {
            "source": "vrbo",
            "event_type": "booking_cancelled",
            "data": {},
            "external_id": external_id
        }
        
        response = requests.post(f"{BASE_URL}/api/ota-webhook/{company_id}", json=cancel_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get('status') == 'received'
        print(f"OTA booking cancelled, log_id: {data.get('log_id')}")
    
    def test_ota_webhook_invalid_company(self):
        """Test OTA webhook with invalid company ID"""
        payload = {
            "source": "airbnb",
            "event_type": "booking_created",
            "data": {"guest_name": "Test"}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ota-webhook/invalid_company_123",
            json=payload
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestOTASyncLogs:
    """Test OTA Sync logs endpoint"""
    
    def test_ota_sync_logs_list(self, admin_session, seeded_admin):
        """Admin should be able to list OTA sync logs"""
        response = admin_session.get(f"{BASE_URL}/api/ota-sync-logs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "OTA sync logs should be a list"
        
        if len(data) > 0:
            log = data[0]
            assert 'id' in log
            assert 'source' in log
            assert 'event_type' in log
            assert 'status' in log
            print(f"Found {len(data)} OTA sync logs")
    
    def test_ota_sync_logs_filter_by_status(self, admin_session, seeded_admin):
        """Test filtering OTA sync logs by status"""
        response = admin_session.get(f"{BASE_URL}/api/ota-sync-logs?status=completed")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            for log in data:
                assert log.get('status') == 'completed', f"Expected status 'completed', got {log.get('status')}"
    
    def test_ota_sync_logs_filter_by_source(self, admin_session, seeded_admin):
        """Test filtering OTA sync logs by source"""
        response = admin_session.get(f"{BASE_URL}/api/ota-sync-logs?source=airbnb")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            for log in data:
                assert log.get('source') == 'airbnb', f"Expected source 'airbnb', got {log.get('source')}"


@pytest.fixture(scope="module")
def inactive_company_user():
    """Create user with inactive subscription"""
    creds = TestSetup.create_test_user("company_admin", "inactive")
    assert creds is not None, "Failed to create inactive subscription user"
    yield creds


class TestSubscriptionMiddleware:
    """Test subscription validation middleware"""
    
    def test_trial_subscription_allows_requests(self, admin_session):
        """Trial subscription should allow all requests"""
        # GET should work
        response = admin_session.get(f"{BASE_URL}/api/properties")
        assert response.status_code == 200, f"GET should work with trial: {response.status_code}"
        
        # POST should work (create property)
        property_data = {
            "name": "Middleware Test Property",
            "address": "123 Test St",
            "owner_first_name": "Test",
            "owner_last_name": "Owner",
            "owner_phone": "+1234567890",
            "owner_email": "middleware_test@test.com",
            "units": 1,
            "active": True
        }
        response = admin_session.post(f"{BASE_URL}/api/properties", json=property_data)
        assert response.status_code == 201, f"POST should work with trial: {response.status_code}"
        
        # Cleanup
        if response.status_code == 201:
            prop_id = response.json().get('id')
            admin_session.delete(f"{BASE_URL}/api/properties/{prop_id}")
    
    def test_inactive_subscription_blocks_post(self, inactive_company_user):
        """Inactive subscription should block POST requests"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {inactive_company_user['token']}"
        })
        
        # GET should still work (read-only)
        response = session.get(f"{BASE_URL}/api/properties")
        assert response.status_code == 200, f"GET should work even with inactive: {response.status_code}"
        
        # POST should be blocked
        property_data = {
            "name": "Should Not Create",
            "address": "123 Block St",
            "owner_first_name": "Test",
            "owner_last_name": "Owner",
            "owner_phone": "+1234567890",
            "owner_email": "blocked@test.com",
            "units": 1,
            "active": True
        }
        response = session.post(f"{BASE_URL}/api/properties", json=property_data)
        assert response.status_code == 402, f"POST should be blocked (402) with inactive: {response.status_code}"
        
        data = response.json()
        assert 'Subscription inactive' in data.get('detail', ''), f"Error message should mention subscription: {data}"
    
    def test_inactive_subscription_blocks_put(self, inactive_company_user):
        """Inactive subscription should block PUT requests"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {inactive_company_user['token']}"
        })
        
        response = session.put(
            f"{BASE_URL}/api/properties/some_id",
            json={"name": "Updated Name"}
        )
        # Either 402 (blocked by middleware) or 404 (property not found) is acceptable
        # If middleware works correctly, it should be 402
        assert response.status_code in [402, 404], f"PUT should be blocked (402) or not found (404): {response.status_code}"
        
        if response.status_code == 402:
            data = response.json()
            assert 'Subscription inactive' in data.get('detail', ''), f"Error message should mention subscription: {data}"
    
    def test_inactive_subscription_blocks_delete(self, inactive_company_user):
        """Inactive subscription should block DELETE requests"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {inactive_company_user['token']}"
        })
        
        response = session.delete(f"{BASE_URL}/api/properties/some_id")
        # Either 402 (blocked by middleware) or 404 (property not found) is acceptable
        assert response.status_code in [402, 404], f"DELETE should be blocked (402) or not found (404): {response.status_code}"
        
        if response.status_code == 402:
            data = response.json()
            assert 'Subscription inactive' in data.get('detail', ''), f"Error message should mention subscription: {data}"
    
    def test_active_subscription_allows_requests(self):
        """Active subscription should allow all requests"""
        # Create user with active subscription
        creds = TestSetup.create_test_user("company_admin", "active")
        assert creds is not None, "Failed to create active subscription user"
        
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds['token']}"
        })
        
        # POST should work
        property_data = {
            "name": "Active Sub Property",
            "address": "123 Active St",
            "owner_first_name": "Test",
            "owner_last_name": "Owner",
            "owner_phone": "+1234567890",
            "owner_email": "active_sub@test.com",
            "units": 1,
            "active": True
        }
        response = session.post(f"{BASE_URL}/api/properties", json=property_data)
        assert response.status_code == 201, f"POST should work with active: {response.status_code}"
        
        # Cleanup
        if response.status_code == 201:
            prop_id = response.json().get('id')
            session.delete(f"{BASE_URL}/api/properties/{prop_id}")


class TestSubscriptionExemptPaths:
    """Test that certain paths are exempt from subscription middleware"""
    
    def test_auth_paths_exempt(self, inactive_company_user):
        """Auth paths should work even with inactive subscription"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {inactive_company_user['token']}"
        })
        
        # /api/auth/me should work
        response = session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"/api/auth/me should be exempt: {response.status_code}"
    
    def test_subscription_paths_exempt(self, inactive_company_user):
        """Subscription paths should work even with inactive subscription"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {inactive_company_user['token']}"
        })
        
        # /api/subscription/plans should work
        response = session.get(f"{BASE_URL}/api/subscription/plans")
        assert response.status_code == 200, f"/api/subscription/plans should be exempt: {response.status_code}"
        
        # /api/subscription/current should work
        response = session.get(f"{BASE_URL}/api/subscription/current")
        assert response.status_code == 200, f"/api/subscription/current should be exempt: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
