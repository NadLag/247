"""
Test email delivery and invitation registration bug fixes

Tests for:
1. GET /api/invitations/validate/{token} - returns 404 for non-existent tokens
2. GET /api/invitations/validate/{token} - returns 400 for cancelled invitations
3. POST /api/auth/register-with-invite - returns 404 for invalid tokens
4. POST /api/auth/register-with-invite - returns 400 for cancelled invitations
5. POST /api/auth/register-with-invite - creates user with assigned_properties and permissions
6. POST /api/auth/register-with-invite - sets session cookie and returns user data
7. POST /api/auth/login - works for password-registered users
8. Backend email from address uses onboarding@resend.dev for Gmail senders
9. Backend invite link URL uses FRONTEND_URL env var
"""

import pytest
import requests
import os
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data prefix for cleanup
TEST_PREFIX = "TEST_EMAIL_FIX_"

class TestInvitationValidation:
    """Test invitation token validation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.timestamp = str(int(datetime.now().timestamp() * 1000))
        
        # Create test admin user and session via mongosh
        import subprocess
        mongo_script = f"""
        use('test_database');
        var companyId = 'comp_emailfix_{self.timestamp}';
        var userId = 'user_emailfix_{self.timestamp}';
        var sessionToken = 'session_emailfix_{self.timestamp}';
        
        db.companies.insertOne({{
            company_id: companyId,
            name: '{TEST_PREFIX}Test Company',
            subscription_status: 'trial',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        db.users.insertOne({{
            user_id: userId,
            email: '{TEST_PREFIX}admin{self.timestamp}@example.com'.toLowerCase(),
            name: '{TEST_PREFIX}Test Admin',
            company_id: companyId,
            role: 'company_admin',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        db.user_sessions.insertOne({{
            user_id: userId,
            session_token: sessionToken,
            expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        // Create a pending invitation
        var pendingToken = 'pending_token_{self.timestamp}';
        db.invitations.insertOne({{
            id: 'inv_pending_{self.timestamp}',
            company_id: companyId,
            email: '{TEST_PREFIX}pending{self.timestamp}@example.com',
            role: 'staff',
            token: pendingToken,
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString(),
            assigned_properties: ['prop1', 'prop2'],
            permissions: {{ view_financials: true, manage_bookings: true }}
        }});
        
        // Create a cancelled invitation
        var cancelledToken = 'cancelled_token_{self.timestamp}';
        db.invitations.insertOne({{
            id: 'inv_cancelled_{self.timestamp}',
            company_id: companyId,
            email: '{TEST_PREFIX}cancelled{self.timestamp}@example.com',
            role: 'owner',
            token: cancelledToken,
            status: 'cancelled',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        // Create an expired invitation
        var expiredToken = 'expired_token_{self.timestamp}';
        db.invitations.insertOne({{
            id: 'inv_expired_{self.timestamp}',
            company_id: companyId,
            email: '{TEST_PREFIX}expired{self.timestamp}@example.com',
            role: 'staff',
            token: expiredToken,
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() - 24*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        // Create an already used invitation
        var usedToken = 'used_token_{self.timestamp}';
        db.invitations.insertOne({{
            id: 'inv_used_{self.timestamp}',
            company_id: companyId,
            email: '{TEST_PREFIX}used{self.timestamp}@example.com',
            role: 'staff',
            token: usedToken,
            status: 'accepted',
            used: true,
            used_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        print('SETUP_DONE:' + sessionToken + ':' + companyId);
        """
        result = subprocess.run(
            ['mongosh', '--quiet', '--eval', mongo_script],
            capture_output=True, text=True
        )
        
        self.session_token = f"session_emailfix_{self.timestamp}"
        self.company_id = f"comp_emailfix_{self.timestamp}"
        self.pending_token = f"pending_token_{self.timestamp}"
        self.cancelled_token = f"cancelled_token_{self.timestamp}"
        self.expired_token = f"expired_token_{self.timestamp}"
        self.used_token = f"used_token_{self.timestamp}"
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('test_database');
        db.companies.deleteMany({{ name: /^{TEST_PREFIX}/ }});
        db.users.deleteMany({{ email: /^{TEST_PREFIX.lower()}/ }});
        db.users.deleteMany({{ email: /^test_email_fix_/ }});
        db.user_sessions.deleteMany({{ session_token: /^session_emailfix_/ }});
        db.invitations.deleteMany({{ email: /^{TEST_PREFIX.lower()}/ }});
        db.invitations.deleteMany({{ email: /^test_email_fix_/ }});
        print('CLEANUP_DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)

    def test_01_validate_nonexistent_token_returns_404(self):
        """GET /api/invitations/validate/{token} returns 404 for non-existent tokens"""
        response = self.session.get(f"{BASE_URL}/api/invitations/validate/nonexistent_token_12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "expired" in data["detail"].lower()
        print(f"✓ Non-existent token returns 404 with message: {data['detail']}")

    def test_02_validate_cancelled_token_returns_400(self):
        """GET /api/invitations/validate/{token} returns 400 for cancelled invitations"""
        response = self.session.get(f"{BASE_URL}/api/invitations/validate/{self.cancelled_token}")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "cancelled" in data["detail"].lower()
        print(f"✓ Cancelled token returns 400 with message: {data['detail']}")

    def test_03_validate_expired_token_returns_400(self):
        """GET /api/invitations/validate/{token} returns 400 for expired invitations"""
        response = self.session.get(f"{BASE_URL}/api/invitations/validate/{self.expired_token}")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "expired" in data["detail"].lower()
        print(f"✓ Expired token returns 400 with message: {data['detail']}")

    def test_04_validate_used_token_shows_already_used(self):
        """GET /api/invitations/validate/{token} returns used=true for already used tokens"""
        response = self.session.get(f"{BASE_URL}/api/invitations/validate/{self.used_token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("used") == True, f"Expected used=true, got: {data}"
        print(f"✓ Used token returns 200 with used=true")

    def test_05_validate_valid_token_returns_invitation_data(self):
        """GET /api/invitations/validate/{token} returns invitation details for valid tokens"""
        response = self.session.get(f"{BASE_URL}/api/invitations/validate/{self.pending_token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("email") is not None, "Missing email"
        assert data.get("role") == "staff", f"Expected role=staff, got {data.get('role')}"
        assert data.get("used") == False, "Expected used=false"
        assert data.get("token") == self.pending_token, "Token mismatch"
        print(f"✓ Valid token returns invitation data: email={data.get('email')}, role={data.get('role')}")


class TestRegisterWithInvite:
    """Test registration with invitation token"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.timestamp = str(int(datetime.now().timestamp() * 1000))
        
        import subprocess
        mongo_script = f"""
        use('test_database');
        var companyId = 'comp_reg_{self.timestamp}';
        
        db.companies.insertOne({{
            company_id: companyId,
            name: '{TEST_PREFIX}Reg Test Company',
            subscription_status: 'trial',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        }});
        
        // Create a valid invitation for registration
        var regToken = 'reg_token_{self.timestamp}';
        db.invitations.insertOne({{
            id: 'inv_reg_{self.timestamp}',
            company_id: companyId,
            email: '{TEST_PREFIX.lower()}newuser{self.timestamp}@example.com',
            role: 'staff',
            token: regToken,
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString(),
            assigned_properties: ['prop_a', 'prop_b'],
            permissions: {{ view_financials: true, manage_bookings: false, manage_tasks: true }}
        }});
        
        // Create a cancelled invitation
        var cancelledToken = 'cancelled_reg_token_{self.timestamp}';
        db.invitations.insertOne({{
            id: 'inv_cancelled_reg_{self.timestamp}',
            company_id: companyId,
            email: '{TEST_PREFIX.lower()}cancelled_reg{self.timestamp}@example.com',
            role: 'owner',
            token: cancelledToken,
            status: 'cancelled',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        
        print('REG_SETUP_DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        self.company_id = f"comp_reg_{self.timestamp}"
        self.reg_token = f"reg_token_{self.timestamp}"
        self.cancelled_token = f"cancelled_reg_token_{self.timestamp}"
        self.test_email = f"{TEST_PREFIX.lower()}newuser{self.timestamp}@example.com"
        self.cancelled_email = f"{TEST_PREFIX.lower()}cancelled_reg{self.timestamp}@example.com"
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('test_database');
        db.companies.deleteMany({{ company_id: /^comp_reg_/ }});
        db.users.deleteMany({{ email: /^{TEST_PREFIX.lower()}/ }});
        db.user_sessions.deleteMany({{ user_id: /^user_reg_/ }});
        db.invitations.deleteMany({{ id: /^inv_reg_|inv_cancelled_reg_/ }});
        db.audit_logs.deleteMany({{ company_id: /^comp_reg_/ }});
        print('REG_CLEANUP_DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)

    def test_01_register_invalid_token_returns_404(self):
        """POST /api/auth/register-with-invite returns 404 for invalid tokens"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            json={
                "token": "invalid_token_xyz",
                "first_name": "John",
                "last_name": "Doe",
                "email": "random@example.com",
                "phone": "+1234567890",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid token returns 404: {data['detail']}")

    def test_02_register_cancelled_token_returns_400(self):
        """POST /api/auth/register-with-invite returns 400 for cancelled invitations"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            json={
                "token": self.cancelled_token,
                "first_name": "Jane",
                "last_name": "Doe",
                "email": self.cancelled_email,
                "phone": "+1234567890",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "cancelled" in data.get("detail", "").lower()
        print(f"✓ Cancelled token returns 400: {data['detail']}")

    def test_03_register_success_creates_user(self):
        """POST /api/auth/register-with-invite creates user with assigned_properties and permissions"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            json={
                "token": self.reg_token,
                "first_name": "Alice",
                "last_name": "Smith",
                "email": self.test_email,
                "phone": "+1555123456",
                "password": "SecurePass456!"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify user data
        assert data.get("email") == self.test_email, f"Email mismatch: {data.get('email')}"
        assert data.get("name") == "Alice Smith", f"Name mismatch: {data.get('name')}"
        assert data.get("first_name") == "Alice", f"First name mismatch: {data.get('first_name')}"
        assert data.get("last_name") == "Smith", f"Last name mismatch: {data.get('last_name')}"
        assert data.get("phone") == "+1555123456", f"Phone mismatch: {data.get('phone')}"
        assert data.get("role") == "staff", f"Role mismatch: {data.get('role')}"
        assert data.get("company_id") == self.company_id, f"Company ID mismatch: {data.get('company_id')}"
        
        # Verify assigned_properties and permissions were copied
        assert data.get("assigned_properties") == ['prop_a', 'prop_b'], f"assigned_properties mismatch: {data.get('assigned_properties')}"
        assert data.get("permissions") == {"view_financials": True, "manage_bookings": False, "manage_tasks": True}, f"permissions mismatch: {data.get('permissions')}"
        
        # Verify password_hash is NOT in response
        assert "password_hash" not in data, "password_hash should not be in response"
        
        print(f"✓ Registration successful: user_id={data.get('user_id')}, role={data.get('role')}")
        print(f"  assigned_properties: {data.get('assigned_properties')}")
        print(f"  permissions: {data.get('permissions')}")

    def test_04_register_sets_session_cookie(self):
        """POST /api/auth/register-with-invite sets session cookie"""
        # Create another valid invitation for this test
        import subprocess
        new_timestamp = str(int(datetime.now().timestamp() * 1000) + 1)
        new_token = f"session_test_token_{new_timestamp}"
        new_email = f"{TEST_PREFIX.lower()}session{new_timestamp}@example.com"
        
        mongo_script = f"""
        use('test_database');
        db.invitations.insertOne({{
            id: 'inv_session_{new_timestamp}',
            company_id: '{self.company_id}',
            email: '{new_email}',
            role: 'staff',
            token: '{new_token}',
            status: 'pending',
            used: false,
            expires_at: new Date(Date.now() + 48*60*60*1000).toISOString(),
            created_at: new Date().toISOString()
        }});
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/register-with-invite",
            json={
                "token": new_token,
                "first_name": "Bob",
                "last_name": "Jones",
                "email": new_email,
                "phone": "",
                "password": "TestPass789!"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check for session_token cookie in response
        cookies = response.cookies
        session_cookie = cookies.get("session_token")
        
        # Note: The cookie might be httpOnly so we check headers too
        set_cookie_header = response.headers.get("set-cookie", "")
        has_session_cookie = "session_token=" in set_cookie_header or session_cookie is not None
        
        assert has_session_cookie, f"Expected session_token cookie, headers: {response.headers}"
        print(f"✓ Session cookie set after registration")


class TestPasswordLogin:
    """Test password-based login for registered users"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test data - a password-registered user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.timestamp = str(int(datetime.now().timestamp() * 1000))
        
        import subprocess
        import bcrypt
        
        # Hash the test password
        test_password = "LoginTestPass123!"
        password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        self.test_email = f"{TEST_PREFIX.lower()}login{self.timestamp}@example.com"
        self.test_password = test_password
        
        mongo_script = f"""
        use('test_database');
        var companyId = 'comp_login_{self.timestamp}';
        var userId = 'user_login_{self.timestamp}';
        
        db.companies.insertOne({{
            company_id: companyId,
            name: '{TEST_PREFIX}Login Test Company',
            subscription_status: 'trial',
            created_at: new Date().toISOString()
        }});
        
        db.users.insertOne({{
            user_id: userId,
            email: '{self.test_email}',
            name: 'Login Test User',
            first_name: 'Login',
            last_name: 'User',
            password_hash: '{password_hash}',
            auth_method: 'password',
            company_id: companyId,
            role: 'staff',
            created_at: new Date().toISOString()
        }});
        
        print('LOGIN_SETUP_DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('test_database');
        db.companies.deleteMany({{ company_id: /^comp_login_/ }});
        db.users.deleteMany({{ email: /^{TEST_PREFIX.lower()}login/ }});
        db.user_sessions.deleteMany({{ user_id: /^user_login_/ }});
        db.audit_logs.deleteMany({{ company_id: /^comp_login_/ }});
        print('LOGIN_CLEANUP_DONE');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)

    def test_01_login_success(self):
        """POST /api/auth/login works for password-registered users"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": self.test_email,
                "password": self.test_password
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("email") == self.test_email, f"Email mismatch: {data.get('email')}"
        assert data.get("role") == "staff", f"Role mismatch: {data.get('role')}"
        assert "password_hash" not in data, "password_hash should not be in response"
        
        print(f"✓ Login successful for password user: {data.get('email')}")

    def test_02_login_invalid_password(self):
        """POST /api/auth/login returns 401 for invalid password"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": self.test_email,
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Invalid password returns 401")

    def test_03_login_nonexistent_user(self):
        """POST /api/auth/login returns 401 for non-existent user"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!"
            }
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"✓ Non-existent user returns 401")


class TestEmailConfiguration:
    """Test email from address and invite link configuration"""
    
    def test_01_sender_email_env_configured(self):
        """Backend has SENDER_EMAIL configured"""
        import subprocess
        result = subprocess.run(
            ['grep', '-E', '^SENDER_EMAIL=', '/app/backend/.env'],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0, "SENDER_EMAIL not found in .env"
        sender_email = result.stdout.strip().split('=')[1]
        print(f"✓ SENDER_EMAIL configured: {sender_email}")

    def test_02_frontend_url_env_configured(self):
        """Backend has FRONTEND_URL configured for invite links"""
        import subprocess
        result = subprocess.run(
            ['grep', '-E', '^FRONTEND_URL=', '/app/backend/.env'],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0, "FRONTEND_URL not found in .env"
        frontend_url = result.stdout.strip().split('=')[1]
        assert 'booking-hub-174.preview.emergentagent.com' in frontend_url or 'http' in frontend_url
        print(f"✓ FRONTEND_URL configured: {frontend_url}")

    def test_03_resend_api_key_configured(self):
        """Backend has RESEND_API_KEY configured"""
        import subprocess
        result = subprocess.run(
            ['grep', '-E', '^RESEND_API_KEY=', '/app/backend/.env'],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0, "RESEND_API_KEY not found in .env"
        api_key = result.stdout.strip().split('=')[1]
        assert api_key.startswith('re_'), f"Invalid Resend API key format: {api_key[:10]}..."
        print(f"✓ RESEND_API_KEY configured: {api_key[:15]}...")

    def test_04_code_uses_onboarding_resend_for_gmail(self):
        """Backend code uses onboarding@resend.dev for Gmail senders"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'onboarding@resend.dev', '/app/backend/server.py'],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0, "onboarding@resend.dev not found in server.py"
        assert '@gmail.com' in open('/app/backend/server.py').read(), "Gmail check not found"
        print(f"✓ Code handles Gmail senders with onboarding@resend.dev")
        print(f"  Found at: {result.stdout.strip()}")

    def test_05_code_uses_frontend_url_for_invite_link(self):
        """Backend code uses FRONTEND_URL for invite links"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', "FRONTEND_URL", '/app/backend/server.py'],
            capture_output=True, text=True
        )
        
        assert result.returncode == 0, "FRONTEND_URL not found in server.py"
        lines = result.stdout.strip().split('\n')
        print(f"✓ FRONTEND_URL used in code at lines: {[l.split(':')[0] for l in lines]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
