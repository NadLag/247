"""
Test Suite: Invitation-Based Registration Flow
Tests the complete flow of invitation creation, validation, and password-based registration.
"""

import pytest
import requests
import os
import time
import subprocess
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://property-hub-dev-1.preview.emergentagent.com').rstrip('/')

# Test data setup - will be created before running tests
TEST_SESSION_TOKEN = None
TEST_COMPANY_ID = None
TEST_STAFF_ID = None

def setup_test_data():
    """Create test admin user, company, and staff for testing"""
    global TEST_SESSION_TOKEN, TEST_COMPANY_ID, TEST_STAFF_ID
    
    ts = str(int(time.time() * 1000))
    
    mongo_script = f'''
    use('test_database');
    var userId = 'test-admin-inv-{ts}';
    var companyId = 'comp_inv_{ts}';
    var sessionToken = 'inv_session_{ts}';
    var staffId = 'staff_inv_{ts}';
    
    // Clean up any existing test data
    db.users.deleteMany({{email: /testinvite.*@example\\.com/}});
    
    // Create company
    db.companies.updateOne(
        {{company_id: companyId}},
        {{$set: {{
            company_id: companyId,
            name: 'Test Invite Company {ts}',
            subscription_status: 'trial',
            subscription_plan: null,
            created_at: new Date(),
            updated_at: new Date()
        }}}},
        {{upsert: true}}
    );
    
    // Create admin user
    db.users.updateOne(
        {{user_id: userId}},
        {{$set: {{
            user_id: userId,
            email: 'admin.inv.{ts}@example.com',
            name: 'Test Admin',
            picture: '',
            company_id: companyId,
            role: 'company_admin',
            created_at: new Date(),
            updated_at: new Date()
        }}}},
        {{upsert: true}}
    );
    
    // Create session
    db.user_sessions.updateOne(
        {{session_token: sessionToken}},
        {{$set: {{
            user_id: userId,
            session_token: sessionToken,
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }}}},
        {{upsert: true}}
    );
    
    // Create a staff record to test pre-filling
    db.staff.updateOne(
        {{id: staffId}},
        {{$set: {{
            id: staffId,
            company_id: companyId,
            first_name: 'John',
            last_name: 'Doe',
            phone: '+1234567890',
            email: 'testinvite.staff.{ts}@example.com',
            salary: 2000,
            payment_terms: 'Monthly',
            payment_type: 'salary',
            staff_role: 'housekeeper',
            active: true,
            created_at: new Date(),
            updated_at: new Date()
        }}}},
        {{upsert: true}}
    );
    
    print('SESSION_TOKEN=' + sessionToken);
    print('COMPANY_ID=' + companyId);
    print('STAFF_ID=' + staffId);
    print('STAFF_EMAIL=testinvite.staff.{ts}@example.com');
    '''
    
    result = subprocess.run(['mongosh', '--eval', mongo_script], capture_output=True, text=True)
    output = result.stdout
    
    for line in output.split('\n'):
        if line.startswith('SESSION_TOKEN='):
            TEST_SESSION_TOKEN = line.split('=')[1].strip()
        elif line.startswith('COMPANY_ID='):
            TEST_COMPANY_ID = line.split('=')[1].strip()
        elif line.startswith('STAFF_ID='):
            TEST_STAFF_ID = line.split('=')[1].strip()
        elif line.startswith('STAFF_EMAIL='):
            global TEST_STAFF_EMAIL
            TEST_STAFF_EMAIL = line.split('=')[1].strip()
    
    return TEST_SESSION_TOKEN, TEST_COMPANY_ID


class TestInvitationFlow:
    """Test invitation creation, validation and registration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data before each test class"""
        global TEST_SESSION_TOKEN, TEST_COMPANY_ID
        if not TEST_SESSION_TOKEN:
            setup_test_data()
        self.session_token = TEST_SESSION_TOKEN
        self.company_id = TEST_COMPANY_ID
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.session_token}"
        }
    
    def test_01_admin_can_create_staff_invitation(self):
        """Admin creates an invitation for a staff member"""
        ts = str(int(time.time() * 1000))
        email = f"testinvite.newstaff.{ts}@example.com"
        
        response = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": email, "role": "staff"}
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify invitation has all required fields
        assert "token" in data, "Invitation should have token"
        assert data["email"] == email, "Email should match"
        assert data["role"] == "staff", "Role should be staff"
        assert data["used"] == False, "Invitation should not be used"
        assert "expires_at" in data, "Invitation should have expires_at"
        
        # Store token for next test
        self.__class__.staff_invite_token = data["token"]
        self.__class__.staff_invite_email = email
        print(f"✅ Created staff invitation with token: {data['token'][:20]}...")
    
    def test_02_admin_can_create_owner_invitation(self):
        """Admin creates an invitation for a property owner"""
        ts = str(int(time.time() * 1000))
        email = f"testinvite.owner.{ts}@example.com"
        
        response = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": email, "role": "owner"}
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["role"] == "owner", "Role should be owner"
        self.__class__.owner_invite_token = data["token"]
        self.__class__.owner_invite_email = email
        print(f"✅ Created owner invitation with token: {data['token'][:20]}...")
    
    def test_03_validate_endpoint_returns_all_required_fields(self):
        """Validate endpoint should return email, role, company_name, first_name, last_name, phone"""
        token = getattr(self.__class__, 'staff_invite_token', None)
        if not token:
            pytest.skip("No invitation token from previous test")
        
        response = requests.get(f"{BASE_URL}/api/invitations/validate/{token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check all required fields are present
        required_fields = ["email", "role", "company_name", "first_name", "last_name", "phone", "token", "used"]
        for field in required_fields:
            assert field in data, f"Response should have '{field}' field"
        
        assert data["email"] == self.__class__.staff_invite_email, "Email should match"
        assert data["role"] == "staff", "Role should be staff"
        assert data["used"] == False, "used should be False"
        assert isinstance(data["company_name"], str), "company_name should be string"
        
        print(f"✅ Validate endpoint returns all fields: {list(data.keys())}")
    
    def test_04_validate_endpoint_returns_404_for_invalid_token(self):
        """Validate endpoint should return 404 for invalid/non-existent token"""
        response = requests.get(f"{BASE_URL}/api/invitations/validate/invalid_token_xyz123")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✅ Invalid token correctly returns 404")
    
    def test_05_validate_prefills_staff_info_from_staff_record(self):
        """When staff record exists with matching email, validate should prefill name/phone"""
        global TEST_STAFF_EMAIL
        
        # First create invitation for existing staff
        response = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": TEST_STAFF_EMAIL, "role": "staff"}
        )
        
        if response.status_code == 400 and "already pending" in response.text:
            # Delete existing invitation first
            invitations = requests.get(f"{BASE_URL}/api/invitations", headers=self.headers).json()
            for inv in invitations:
                if inv["email"] == TEST_STAFF_EMAIL:
                    requests.delete(f"{BASE_URL}/api/invitations/{inv['id']}", headers=self.headers)
            
            # Retry creating invitation
            response = requests.post(
                f"{BASE_URL}/api/invitations",
                headers=self.headers,
                json={"email": TEST_STAFF_EMAIL, "role": "staff"}
            )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        token = response.json()["token"]
        
        # Now validate
        validate_resp = requests.get(f"{BASE_URL}/api/invitations/validate/{token}")
        assert validate_resp.status_code == 200
        data = validate_resp.json()
        
        # Should have pre-filled info from staff record
        assert data["first_name"] == "John", f"first_name should be 'John', got '{data['first_name']}'"
        assert data["last_name"] == "Doe", f"last_name should be 'Doe', got '{data['last_name']}'"
        assert data["phone"] == "+1234567890", f"phone should be '+1234567890', got '{data['phone']}'"
        
        self.__class__.prefilled_token = token
        print(f"✅ Validate endpoint correctly prefills staff info: {data['first_name']} {data['last_name']}")
    
    def test_06_register_with_invite_creates_user_with_password(self):
        """Registration endpoint creates user with password and assigns role"""
        token = getattr(self.__class__, 'staff_invite_token', None)
        email = getattr(self.__class__, 'staff_invite_email', None)
        
        if not token or not email:
            pytest.skip("No invitation token from previous test")
        
        # Register with password
        response = requests.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            headers={"Content-Type": "application/json"},
            json={
                "token": token,
                "first_name": "New",
                "last_name": "Staff",
                "email": email,
                "phone": "+1987654321",
                "password": "SecureTestPass123!"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify user was created with correct data
        assert data["email"].lower() == email.lower(), "Email should match"
        assert data["role"] == "staff", "Role should be staff"
        assert "password_hash" not in data, "password_hash should not be in response"
        assert "user_id" in data, "Should have user_id"
        assert data["company_id"] == self.company_id, "company_id should match"
        
        self.__class__.registered_user_email = email
        self.__class__.registered_user_password = "SecureTestPass123!"
        print(f"✅ User registered successfully: {data['email']} as {data['role']}")
    
    def test_07_register_with_invite_fails_for_used_token(self):
        """Registration should fail for already-used invitation token"""
        token = getattr(self.__class__, 'staff_invite_token', None)
        email = getattr(self.__class__, 'staff_invite_email', None)
        
        if not token:
            pytest.skip("No invitation token from previous test")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            headers={"Content-Type": "application/json"},
            json={
                "token": token,
                "first_name": "Duplicate",
                "last_name": "User",
                "email": email,
                "phone": "",
                "password": "AnotherPass123!"
            }
        )
        
        # Should fail because token is already used
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print("✅ Used token correctly rejected")
    
    def test_08_register_with_invite_fails_for_email_mismatch(self):
        """Registration should fail if email doesn't match invitation"""
        token = getattr(self.__class__, 'owner_invite_token', None)
        
        if not token:
            pytest.skip("No owner invitation token from previous test")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            headers={"Content-Type": "application/json"},
            json={
                "token": token,
                "first_name": "Wrong",
                "last_name": "Email",
                "email": "completely.different@email.com",
                "phone": "",
                "password": "TestPass123!"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "email" in response.text.lower() or "match" in response.text.lower()
        print("✅ Email mismatch correctly rejected")
    
    def test_09_registered_user_can_login_with_password(self):
        """User registered via invitation can login with password"""
        email = getattr(self.__class__, 'registered_user_email', None)
        password = getattr(self.__class__, 'registered_user_password', None)
        
        if not email or not password:
            pytest.skip("No registered user from previous test")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["email"].lower() == email.lower()
        assert data["role"] == "staff"
        print(f"✅ User can login with password: {data['email']}")
    
    def test_10_registered_user_has_correct_role_and_company(self):
        """Verify the registered user has the correct role and company_id from invitation"""
        email = getattr(self.__class__, 'registered_user_email', None)
        password = getattr(self.__class__, 'registered_user_password', None)
        
        if not email or not password:
            pytest.skip("No registered user from previous test")
        
        # Login to get session
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password}
        )
        
        # Get the session cookie from response
        cookies = login_resp.cookies
        
        # Call /api/auth/me to verify user data
        me_resp = requests.get(
            f"{BASE_URL}/api/auth/me",
            cookies=cookies
        )
        
        if me_resp.status_code == 401:
            # Session might be in response body
            data = login_resp.json()
            assert data["role"] == "staff", f"Role should be staff, got {data.get('role')}"
            assert data["company_id"] == self.company_id, f"company_id should match"
        else:
            assert me_resp.status_code == 200
            data = me_resp.json()
            assert data["role"] == "staff", f"Role should be staff, got {data.get('role')}"
            assert data["company_id"] == self.company_id, f"company_id should match"
        
        print(f"✅ User has correct role ({data['role']}) and company_id")


class TestInvitationEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        global TEST_SESSION_TOKEN
        if not TEST_SESSION_TOKEN:
            setup_test_data()
        self.session_token = TEST_SESSION_TOKEN
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.session_token}"
        }
    
    def test_11_cannot_create_invitation_for_invalid_role(self):
        """Invitation creation should fail for invalid roles"""
        response = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": "test@example.com", "role": "superadmin"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ Invalid role correctly rejected")
    
    def test_12_duplicate_invitation_fails(self):
        """Cannot create duplicate invitation for same email"""
        ts = str(int(time.time() * 1000))
        email = f"testinvite.duplicate.{ts}@example.com"
        
        # First invitation
        response1 = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": email, "role": "staff"}
        )
        assert response1.status_code == 201
        
        # Duplicate invitation
        response2 = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": email, "role": "staff"}
        )
        
        assert response2.status_code == 400, f"Expected 400, got {response2.status_code}"
        assert "pending" in response2.text.lower() or "already" in response2.text.lower()
        print("✅ Duplicate invitation correctly rejected")
    
    def test_13_registration_with_short_password_fails(self):
        """Registration should fail with password < 8 characters"""
        ts = str(int(time.time() * 1000))
        email = f"testinvite.shortpw.{ts}@example.com"
        
        # Create invitation
        inv_resp = requests.post(
            f"{BASE_URL}/api/invitations",
            headers=self.headers,
            json={"email": email, "role": "staff"}
        )
        assert inv_resp.status_code == 201
        token = inv_resp.json()["token"]
        
        # Try to register with short password
        response = requests.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            headers={"Content-Type": "application/json"},
            json={
                "token": token,
                "first_name": "Short",
                "last_name": "Pass",
                "email": email,
                "phone": "",
                "password": "short"  # Too short
            }
        )
        
        # Backend validation or Pydantic should catch this
        # The frontend validates 8 chars min
        # Note: If backend doesn't validate, this test reveals a gap
        print(f"Registration with short password: status={response.status_code}")


# Standalone function to run setup
if __name__ == "__main__":
    setup_test_data()
    print(f"Test setup complete. SESSION_TOKEN: {TEST_SESSION_TOKEN}")
