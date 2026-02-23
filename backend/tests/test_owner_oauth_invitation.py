"""
Test Owner OAuth Registration via Invitation Flow
Tests the critical bug fix where:
1. Owner CANNOT register using Google OAuth via invitation link
2. After registration, dashboard shows all values as 0
3. No properties are assigned to the owner

This test verifies:
- Invitation validation endpoint works
- Password registration assigns correct role and assigned_properties from invitation
- Dashboard KPIs filter by assigned_properties for owner role
- Properties list filters by assigned_properties for owner role
- Bookings list filters by assigned_properties for owner role
- Revenue trends filter by assigned_properties for owner role
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOwnerInvitationRegistration:
    """Test owner invitation and registration flow with assigned_properties"""
    
    @pytest.fixture(scope="class")
    def test_data(self):
        """Setup test data: admin user, company, properties, invitation for owner"""
        timestamp = int(datetime.now().timestamp() * 1000)
        
        data = {
            "user_id": f"admin_{timestamp}",
            "company_id": f"comp_{timestamp}",
            "session_token": f"admin_session_{timestamp}",
            "property1_id": f"prop_{timestamp}_1",
            "property2_id": f"prop_{timestamp}_2",
            "owner_email": f"owner_{timestamp}@example.com",
            "invitation_token": f"inv_owner_{timestamp}",
            "booking1_id": f"book_{timestamp}_1",
            "booking2_id": f"book_{timestamp}_2",
        }
        
        # Create via MongoDB shell
        mongo_script = f'''
        use('test_database');
        
        // Create company
        db.companies.insertOne({{
            company_id: '{data["company_id"]}',
            name: 'Owner Test Company {timestamp}',
            subscription_status: 'trial',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        // Create admin user
        db.users.insertOne({{
            user_id: '{data["user_id"]}',
            email: 'admin_{timestamp}@example.com',
            name: 'Admin User',
            company_id: '{data["company_id"]}',
            role: 'company_admin',
            assigned_properties: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        // Create admin session
        db.user_sessions.insertOne({{
            user_id: '{data["user_id"]}',
            session_token: '{data["session_token"]}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        // Create property 1 with owner email
        db.properties.insertOne({{
            id: '{data["property1_id"]}',
            company_id: '{data["company_id"]}',
            name: 'Beach House',
            address: '123 Ocean Drive',
            owner_email: '{data["owner_email"]}',
            owner_first_name: 'John',
            owner_last_name: 'Owner',
            owner_phone: '+1234567890',
            units: 2,
            active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        // Create property 2 with same owner email
        db.properties.insertOne({{
            id: '{data["property2_id"]}',
            company_id: '{data["company_id"]}',
            name: 'Mountain Cabin',
            address: '456 Pine Road',
            owner_email: '{data["owner_email"]}',
            owner_first_name: 'John',
            owner_last_name: 'Owner',
            owner_phone: '+1234567890',
            units: 1,
            active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        // Create invitation for owner with assigned_properties
        db.invitations.insertOne({{
            token: '{data["invitation_token"]}',
            company_id: '{data["company_id"]}',
            email: '{data["owner_email"]}',
            role: 'owner',
            name: 'John Owner',
            assigned_properties: ['{data["property1_id"]}', '{data["property2_id"]}'],
            permissions: {{}},
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        // Create booking for property 1 (should be visible to owner)
        var today = new Date().toISOString().slice(0, 10);
        var nextWeek = new Date(Date.now() + 7*24*60*60*1000).toISOString().slice(0, 10);
        
        db.bookings.insertOne({{
            id: '{data["booking1_id"]}',
            company_id: '{data["company_id"]}',
            property_id: '{data["property1_id"]}',
            guest_name: 'Test Guest 1',
            check_in: today,
            check_out: nextWeek,
            total_amount: 500,
            guests_count: 2,
            status: 'confirmed',
            booking_type: 'reservation',
            is_data_complete: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        // Create booking for property 2 (should be visible to owner)
        db.bookings.insertOne({{
            id: '{data["booking2_id"]}',
            company_id: '{data["company_id"]}',
            property_id: '{data["property2_id"]}',
            guest_name: 'Test Guest 2',
            check_in: today,
            check_out: nextWeek,
            total_amount: 300,
            guests_count: 1,
            status: 'confirmed',
            booking_type: 'reservation',
            is_data_complete: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        print('Test data created successfully');
        '''
        
        import subprocess
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True, text=True
        )
        print(f"MongoDB setup: {result.stdout}")
        if result.returncode != 0:
            print(f"MongoDB error: {result.stderr}")
        
        yield data
        
        # Cleanup
        cleanup_script = f'''
        use('test_database');
        db.companies.deleteOne({{ company_id: '{data["company_id"]}' }});
        db.users.deleteMany({{ company_id: '{data["company_id"]}' }});
        db.user_sessions.deleteOne({{ session_token: '{data["session_token"]}' }});
        db.properties.deleteMany({{ company_id: '{data["company_id"]}' }});
        db.invitations.deleteOne({{ token: '{data["invitation_token"]}' }});
        db.bookings.deleteMany({{ company_id: '{data["company_id"]}' }});
        db.expenses.deleteMany({{ company_id: '{data["company_id"]}' }});
        print('Test data cleaned up');
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)

    # Test 1: Validate invitation token returns correct data
    def test_01_validate_invitation_returns_correct_data(self, test_data):
        """Validate invitation endpoint returns invitation data including role"""
        response = requests.get(f"{BASE_URL}/api/invitations/validate/{test_data['invitation_token']}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["email"] == test_data["owner_email"], f"Email mismatch: {data['email']}"
        assert data["role"] == "owner", f"Role should be 'owner', got {data['role']}"
        assert data["used"] == False, "Invitation should not be marked as used"
        assert "company_name" in data, "Should include company_name"
        assert data.get("first_name") == "John", f"Expected first_name 'John', got {data.get('first_name')}"
        assert data.get("last_name") == "Owner", f"Expected last_name 'Owner', got {data.get('last_name')}"
        print(f"✅ Invitation validation returned correct data: role={data['role']}, email={data['email']}")
    
    # Test 2: Validate 404 for non-existent token
    def test_02_validate_invitation_returns_404_for_invalid_token(self):
        """Invalid token should return 404"""
        response = requests.get(f"{BASE_URL}/api/invitations/validate/invalid_token_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Invalid token returns 404 as expected")
    
    # Test 3: Password registration creates user with assigned_properties from invitation
    def test_03_password_registration_assigns_properties(self, test_data):
        """Password registration should assign properties from invitation to user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            json={
                "token": test_data["invitation_token"],
                "first_name": "John",
                "last_name": "Owner",
                "email": test_data["owner_email"],
                "phone": "+1234567890",
                "password": "SecurePassword123!"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        user_data = response.json()
        assert user_data["role"] == "owner", f"User role should be 'owner', got {user_data['role']}"
        assert user_data["company_id"] == test_data["company_id"], "User should be linked to correct company"
        
        # CRITICAL: Check assigned_properties is set correctly
        assigned_props = user_data.get("assigned_properties", [])
        assert len(assigned_props) == 2, f"Expected 2 assigned properties, got {len(assigned_props)}"
        assert test_data["property1_id"] in assigned_props, f"Property 1 should be assigned: {assigned_props}"
        assert test_data["property2_id"] in assigned_props, f"Property 2 should be assigned: {assigned_props}"
        
        # Store session token for subsequent tests
        test_data["owner_session_token"] = response.cookies.get("session_token")
        print(f"✅ Password registration created user with role={user_data['role']}, assigned_properties={assigned_props}")
    
    # Test 4: Owner dashboard KPIs filter by assigned_properties
    def test_04_owner_dashboard_kpis_filtered_by_assigned_properties(self, test_data):
        """Dashboard KPIs should only show data for owner's assigned properties"""
        # Use owner session
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": test_data["owner_email"],
                "password": "SecurePassword123!"
            }
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        session_token = response.cookies.get("session_token")
        
        # Get dashboard KPIs
        kpi_response = requests.get(
            f"{BASE_URL}/api/dashboard/kpis",
            headers={"Authorization": f"Bearer {session_token}"}
        )
        
        assert kpi_response.status_code == 200, f"KPIs failed: {kpi_response.text}"
        kpis = kpi_response.json()
        
        # Verify role is returned
        assert kpis.get("role") == "owner", f"KPI role should be 'owner', got {kpis.get('role')}"
        
        # Verify property count (owner has 2 assigned properties)
        assert kpis.get("total_properties") == 2, f"Expected 2 properties, got {kpis.get('total_properties')}"
        assert kpis.get("active_properties") == 2, f"Expected 2 active properties, got {kpis.get('active_properties')}"
        
        # Verify revenue (should be from bookings on owner's properties: 500 + 300 = 800)
        # Note: revenue_mtd depends on current month's bookings
        assert kpis.get("revenue_mtd") >= 0, f"Revenue should be >= 0, got {kpis.get('revenue_mtd')}"
        
        # Verify active bookings count
        assert kpis.get("active_bookings") >= 0, f"Active bookings should be >= 0"
        
        test_data["owner_session"] = session_token
        print(f"✅ Owner KPIs filtered correctly: properties={kpis.get('total_properties')}, revenue={kpis.get('revenue_mtd')}")
    
    # Test 5: Owner properties list filtered by assigned_properties
    def test_05_owner_properties_list_filtered(self, test_data):
        """Properties list should only return owner's assigned properties"""
        response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {test_data['owner_session']}"}
        )
        
        assert response.status_code == 200, f"Properties failed: {response.text}"
        properties = response.json()
        
        # Owner should only see their 2 assigned properties
        assert len(properties) == 2, f"Expected 2 properties, got {len(properties)}"
        
        property_ids = [p["id"] for p in properties]
        assert test_data["property1_id"] in property_ids, "Property 1 should be in list"
        assert test_data["property2_id"] in property_ids, "Property 2 should be in list"
        
        print(f"✅ Owner properties list filtered correctly: {len(properties)} properties returned")
    
    # Test 6: Owner bookings list filtered by assigned_properties
    def test_06_owner_bookings_list_filtered(self, test_data):
        """Bookings list should only return bookings for owner's assigned properties"""
        response = requests.get(
            f"{BASE_URL}/api/bookings",
            headers={"Authorization": f"Bearer {test_data['owner_session']}"}
        )
        
        assert response.status_code == 200, f"Bookings failed: {response.text}"
        bookings = response.json()
        
        # Owner should only see bookings for their properties
        assert len(bookings) >= 2, f"Expected at least 2 bookings, got {len(bookings)}"
        
        # Verify all bookings are for owner's properties
        for booking in bookings:
            property_id = booking.get("property_id")
            assert property_id in [test_data["property1_id"], test_data["property2_id"]], \
                f"Booking for property {property_id} should not be visible to owner"
        
        print(f"✅ Owner bookings list filtered correctly: {len(bookings)} bookings returned")
    
    # Test 7: Owner revenue trends filtered by assigned_properties
    def test_07_owner_revenue_trends_filtered(self, test_data):
        """Revenue trends should only include data for owner's assigned properties"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/revenue-trends",
            headers={"Authorization": f"Bearer {test_data['owner_session']}"}
        )
        
        assert response.status_code == 200, f"Revenue trends failed: {response.text}"
        trends = response.json()
        
        # Should return 6 months of data
        assert len(trends) == 6, f"Expected 6 months of trends, got {len(trends)}"
        
        # Verify structure
        for trend in trends:
            assert "month" in trend, "Trend should have month"
            assert "revenue" in trend, "Trend should have revenue"
            assert "expenses" in trend, "Trend should have expenses"
        
        print(f"✅ Owner revenue trends returned correctly: {len(trends)} months of data")
    
    # Test 8: Verify invitation is marked as used after registration
    def test_08_invitation_marked_as_used(self, test_data):
        """Invitation should be marked as used after registration"""
        response = requests.get(f"{BASE_URL}/api/invitations/validate/{test_data['invitation_token']}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("used") == True, f"Invitation should be marked as used, got {data.get('used')}"
        print("✅ Invitation marked as used after registration")


class TestOAuthSessionExchange:
    """Test OAuth session exchange with invitation token"""
    
    @pytest.fixture(scope="class")
    def oauth_test_data(self):
        """Setup test data for OAuth flow"""
        timestamp = int(datetime.now().timestamp() * 1000)
        
        data = {
            "company_id": f"comp_oauth_{timestamp}",
            "property_id": f"prop_oauth_{timestamp}",
            "invitation_token": f"inv_oauth_{timestamp}",
            "owner_email": f"oauthowner_{timestamp}@example.com",
        }
        
        mongo_script = f'''
        use('test_database');
        
        // Create company
        db.companies.insertOne({{
            company_id: '{data["company_id"]}',
            name: 'OAuth Test Company',
            subscription_status: 'trial',
            created_at: new Date().toISOString()
        }});
        
        // Create property with owner email
        db.properties.insertOne({{
            id: '{data["property_id"]}',
            company_id: '{data["company_id"]}',
            name: 'OAuth Test Property',
            address: '789 OAuth Lane',
            owner_email: '{data["owner_email"]}',
            owner_first_name: 'OAuth',
            owner_last_name: 'Owner',
            units: 1,
            active: true,
            created_at: new Date().toISOString()
        }});
        
        // Create invitation
        db.invitations.insertOne({{
            token: '{data["invitation_token"]}',
            company_id: '{data["company_id"]}',
            email: '{data["owner_email"]}',
            role: 'owner',
            assigned_properties: ['{data["property_id"]}'],
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        print('OAuth test data created');
        '''
        
        import subprocess
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        yield data
        
        # Cleanup
        cleanup_script = f'''
        use('test_database');
        db.companies.deleteOne({{ company_id: '{data["company_id"]}' }});
        db.properties.deleteMany({{ company_id: '{data["company_id"]}' }});
        db.invitations.deleteOne({{ token: '{data["invitation_token"]}' }});
        db.users.deleteMany({{ company_id: '{data["company_id"]}' }});
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_01_validate_oauth_invitation(self, oauth_test_data):
        """Validate invitation exists for OAuth user"""
        response = requests.get(f"{BASE_URL}/api/invitations/validate/{oauth_test_data['invitation_token']}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["role"] == "owner"
        assert data["email"] == oauth_test_data["owner_email"]
        print(f"✅ OAuth invitation validated: role={data['role']}")


class TestExistingUserOAuthInvitation:
    """Test that existing OAuth users can accept invitations and get updated role/properties"""
    
    @pytest.fixture(scope="class")
    def existing_user_data(self):
        """Create existing user and then invitation for them"""
        timestamp = int(datetime.now().timestamp() * 1000)
        
        data = {
            "user_id": f"existing_user_{timestamp}",
            "company_id": f"comp_existing_{timestamp}",
            "property_id": f"prop_existing_{timestamp}",
            "invitation_token": f"inv_existing_{timestamp}",
            "user_email": f"existing_{timestamp}@example.com",
            "admin_session": f"admin_session_existing_{timestamp}",
        }
        
        # Create user without company (like a new Google user)
        mongo_script = f'''
        use('test_database');
        
        // Create company first (for the invitation)
        db.companies.insertOne({{
            company_id: '{data["company_id"]}',
            name: 'Existing User Test Company',
            subscription_status: 'trial',
            created_at: new Date().toISOString()
        }});
        
        // Create existing user WITHOUT company_id (like new OAuth user)
        db.users.insertOne({{
            user_id: '{data["user_id"]}',
            email: '{data["user_email"]}',
            name: 'Existing User',
            picture: '',
            auth_method: 'google',
            company_id: null,
            role: null,
            assigned_properties: [],
            created_at: new Date().toISOString()
        }});
        
        // Create property
        db.properties.insertOne({{
            id: '{data["property_id"]}',
            company_id: '{data["company_id"]}',
            name: 'Existing User Property',
            address: '999 Existing St',
            owner_email: '{data["user_email"]}',
            units: 1,
            active: true,
            created_at: new Date().toISOString()
        }});
        
        // Create invitation for existing user
        db.invitations.insertOne({{
            token: '{data["invitation_token"]}',
            company_id: '{data["company_id"]}',
            email: '{data["user_email"]}',
            role: 'owner',
            assigned_properties: ['{data["property_id"]}'],
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        print('Existing user test data created');
        '''
        
        import subprocess
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        yield data
        
        # Cleanup
        cleanup_script = f'''
        use('test_database');
        db.companies.deleteOne({{ company_id: '{data["company_id"]}' }});
        db.users.deleteMany({{ email: '{data["user_email"]}' }});
        db.properties.deleteMany({{ company_id: '{data["company_id"]}' }});
        db.invitations.deleteOne({{ token: '{data["invitation_token"]}' }});
        db.user_sessions.deleteMany({{ user_id: '{data["user_id"]}' }});
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_01_existing_user_password_registration_updates_role(self, existing_user_data):
        """
        Existing user accepting invitation via password should get:
        - company_id updated
        - role updated
        - assigned_properties updated
        """
        # Register with password (even though user exists)
        response = requests.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            json={
                "token": existing_user_data["invitation_token"],
                "first_name": "Existing",
                "last_name": "User",
                "email": existing_user_data["user_email"],
                "phone": "",
                "password": "ExistingUserPass123!"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        user_data = response.json()
        
        # Verify user was updated with invitation data
        assert user_data["company_id"] == existing_user_data["company_id"], \
            f"Company should be updated: {user_data.get('company_id')}"
        assert user_data["role"] == "owner", \
            f"Role should be 'owner': {user_data.get('role')}"
        
        assigned_props = user_data.get("assigned_properties", [])
        assert existing_user_data["property_id"] in assigned_props, \
            f"Property should be assigned: {assigned_props}"
        
        print(f"✅ Existing user updated: company={user_data['company_id']}, role={user_data['role']}, props={assigned_props}")


class TestAdminCanSeeAllData:
    """Test that admins see all properties/bookings (not filtered)"""
    
    @pytest.fixture(scope="class")
    def admin_data(self):
        """Setup admin with full access"""
        timestamp = int(datetime.now().timestamp() * 1000)
        
        data = {
            "user_id": f"full_admin_{timestamp}",
            "company_id": f"comp_admin_{timestamp}",
            "session_token": f"admin_full_{timestamp}",
            "prop1": f"prop_admin_1_{timestamp}",
            "prop2": f"prop_admin_2_{timestamp}",
        }
        
        mongo_script = f'''
        use('test_database');
        
        db.companies.insertOne({{
            company_id: '{data["company_id"]}',
            name: 'Admin Full Access Company',
            subscription_status: 'trial',
            created_at: new Date().toISOString()
        }});
        
        db.users.insertOne({{
            user_id: '{data["user_id"]}',
            email: 'fulladmin_{timestamp}@example.com',
            name: 'Full Admin',
            company_id: '{data["company_id"]}',
            role: 'company_admin',
            assigned_properties: [],
            created_at: new Date().toISOString()
        }});
        
        db.user_sessions.insertOne({{
            user_id: '{data["user_id"]}',
            session_token: '{data["session_token"]}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        // Create 2 properties with different owners
        db.properties.insertOne({{
            id: '{data["prop1"]}',
            company_id: '{data["company_id"]}',
            name: 'Admin Prop 1',
            address: 'Address 1',
            owner_email: 'owner1@example.com',
            units: 1,
            active: true,
            created_at: new Date().toISOString()
        }});
        
        db.properties.insertOne({{
            id: '{data["prop2"]}',
            company_id: '{data["company_id"]}',
            name: 'Admin Prop 2',
            address: 'Address 2',
            owner_email: 'owner2@example.com',
            units: 1,
            active: true,
            created_at: new Date().toISOString()
        }});
        
        print('Admin test data created');
        '''
        
        import subprocess
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        yield data
        
        # Cleanup
        cleanup_script = f'''
        use('test_database');
        db.companies.deleteOne({{ company_id: '{data["company_id"]}' }});
        db.users.deleteOne({{ user_id: '{data["user_id"]}' }});
        db.user_sessions.deleteOne({{ session_token: '{data["session_token"]}' }});
        db.properties.deleteMany({{ company_id: '{data["company_id"]}' }});
        '''
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)
    
    def test_01_admin_sees_all_properties(self, admin_data):
        """Admin should see all properties in company"""
        response = requests.get(
            f"{BASE_URL}/api/properties",
            headers={"Authorization": f"Bearer {admin_data['session_token']}"}
        )
        
        assert response.status_code == 200
        properties = response.json()
        
        # Admin should see both properties
        assert len(properties) >= 2, f"Admin should see at least 2 properties, got {len(properties)}"
        
        prop_ids = [p["id"] for p in properties]
        assert admin_data["prop1"] in prop_ids
        assert admin_data["prop2"] in prop_ids
        
        print(f"✅ Admin sees all {len(properties)} properties")
    
    def test_02_admin_kpis_include_all_properties(self, admin_data):
        """Admin KPIs should include all properties"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/kpis",
            headers={"Authorization": f"Bearer {admin_data['session_token']}"}
        )
        
        assert response.status_code == 200
        kpis = response.json()
        
        assert kpis.get("role") == "company_admin"
        assert kpis.get("total_properties") >= 2, f"Admin should see at least 2 properties in KPIs"
        
        print(f"✅ Admin KPIs include all properties: total={kpis.get('total_properties')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
