"""
Backend API tests for:
- Password-based registration with invitation
- Password-based login
- Tasks CRUD operations
- Staff earnings endpoint
- Role-specific behavior

Test Session: iteration_7
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token from MongoDB setup
ADMIN_SESSION_TOKEN = "test_admin_session_1771719486488"
COMPANY_ID = "comp_test_1771719486488"
STAFF_ID = "staff_test_1771719486488"


@pytest.fixture
def admin_client():
    """Authenticated admin session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"
    })
    session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
    return session


@pytest.fixture
def unauthenticated_client():
    """Non-authenticated session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestInvitationValidation:
    """Test invitation validation endpoint"""
    
    def test_validate_invalid_token(self, unauthenticated_client):
        """Invalid invitation token returns 404"""
        response = unauthenticated_client.get(f"{BASE_URL}/api/invitations/validate/invalid_token_xyz")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ Invalid invitation token returns 404")


class TestInvitationRegistration:
    """Test password-based registration with invitation"""
    
    @pytest.fixture(autouse=True)
    def setup_invitation(self, admin_client):
        """Create a test invitation for registration tests"""
        self.test_email = f"testuser_{datetime.now().timestamp()}@example.com"
        
        # Create invitation
        response = admin_client.post(f"{BASE_URL}/api/invitations", json={
            "email": self.test_email,
            "role": "staff"
        })
        
        if response.status_code == 201:
            self.invitation = response.json()
            self.invitation_token = self.invitation.get("token")
        else:
            # If invitation creation fails, skip tests
            pytest.skip(f"Failed to create invitation: {response.text}")
        
        yield
        
        # Cleanup: Delete test user if created
        # (Optional - can be done in teardown)
    
    def test_register_with_valid_invite(self, unauthenticated_client):
        """Register with valid invitation token and password"""
        response = unauthenticated_client.post(f"{BASE_URL}/api/auth/register-with-invite", json={
            "token": self.invitation_token,
            "first_name": "Test",
            "last_name": "User",
            "email": self.test_email,
            "phone": "+1234567890",
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("email") == self.test_email.lower()
        assert data.get("first_name") == "Test"
        assert data.get("last_name") == "User"
        assert data.get("role") == "staff"
        assert data.get("company_id") is not None
        assert "password_hash" not in data  # Should not expose password
        print(f"✅ User registered with invitation: {data.get('user_id')}")
    
    def test_register_with_invalid_token(self, unauthenticated_client):
        """Register with invalid token returns 404"""
        response = unauthenticated_client.post(f"{BASE_URL}/api/auth/register-with-invite", json={
            "token": "invalid_token_xyz123",
            "first_name": "Test",
            "last_name": "User",
            "email": "random@example.com",
            "phone": "+1234567890",
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ Invalid token returns 404 for registration")
    
    def test_register_email_mismatch(self, unauthenticated_client):
        """Register with mismatched email returns 400"""
        response = unauthenticated_client.post(f"{BASE_URL}/api/auth/register-with-invite", json={
            "token": self.invitation_token,
            "first_name": "Test",
            "last_name": "User",
            "email": "different@example.com",  # Different from invitation email
            "phone": "+1234567890",
            "password": "SecurePass123!"
        })
        
        # Should be 400 (if invitation exists but used) or 400 (email mismatch)
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}: {response.text}"
        print("✅ Email mismatch correctly handled")


class TestPasswordLogin:
    """Test email/password login"""
    
    @pytest.fixture(autouse=True)
    def setup_user_with_password(self, admin_client):
        """Create a user with password for login tests"""
        self.test_email = f"logintest_{datetime.now().timestamp()}@example.com"
        self.test_password = "LoginTestPass123!"
        
        # Create invitation first
        inv_response = admin_client.post(f"{BASE_URL}/api/invitations", json={
            "email": self.test_email,
            "role": "staff"
        })
        
        if inv_response.status_code != 201:
            pytest.skip(f"Failed to create invitation for login test: {inv_response.text}")
        
        token = inv_response.json().get("token")
        
        # Register user with password
        reg_response = requests.post(f"{BASE_URL}/api/auth/register-with-invite", json={
            "token": token,
            "first_name": "Login",
            "last_name": "Test",
            "email": self.test_email,
            "phone": "+1234567890",
            "password": self.test_password
        })
        
        if reg_response.status_code != 200:
            pytest.skip(f"Failed to register user for login test: {reg_response.text}")
        
        yield
    
    def test_login_success(self, unauthenticated_client):
        """Login with valid credentials"""
        response = unauthenticated_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("email") == self.test_email.lower()
        assert "password_hash" not in data
        print(f"✅ Login successful for {self.test_email}")
    
    def test_login_invalid_password(self, unauthenticated_client):
        """Login with wrong password returns 401"""
        response = unauthenticated_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.test_email,
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ Invalid password returns 401")
    
    def test_login_nonexistent_user(self, unauthenticated_client):
        """Login with non-existent email returns 401"""
        response = unauthenticated_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ Non-existent user returns 401")


class TestTasksCRUD:
    """Test Tasks CRUD operations"""
    
    def test_list_tasks_empty(self, admin_client):
        """List tasks - initially may be empty or have data"""
        response = admin_client.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ GET /api/tasks returned {len(data)} tasks")
    
    def test_create_task(self, admin_client):
        """Create a new task"""
        task_data = {
            "title": "TEST_Clean apartment after checkout",
            "description": "Full cleaning including linens change",
            "task_type": "cleaning",
            "assigned_staff_id": STAFF_ID,
            "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "priority": "high"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        task = response.json()
        assert task.get("title") == task_data["title"]
        assert task.get("task_type") == "cleaning"
        assert task.get("priority") == "high"
        assert task.get("status") == "pending"
        assert "id" in task
        
        # Store task ID for subsequent tests
        self.__class__.created_task_id = task["id"]
        print(f"✅ Created task: {task['id']}")
        return task["id"]
    
    def test_create_task_invalid_staff(self, admin_client):
        """Create task with invalid staff ID returns 404"""
        task_data = {
            "title": "TEST_Invalid staff task",
            "assigned_staff_id": "invalid_staff_id",
            "task_type": "general",
            "priority": "low"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ Invalid staff ID returns 404")
    
    def test_get_task_summary(self, admin_client):
        """Get task summary (for staff)"""
        response = admin_client.get(f"{BASE_URL}/api/tasks/my-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Admin gets default summary (not a staff member)
        assert "pending" in data
        assert "in_progress" in data
        assert "completed_this_month" in data
        print(f"✅ Task summary: pending={data['pending']}, in_progress={data['in_progress']}")
    
    def test_update_task_status(self, admin_client):
        """Update task status"""
        # First create a task
        task_data = {
            "title": "TEST_Status update task",
            "assigned_staff_id": STAFF_ID,
            "task_type": "maintenance",
            "priority": "medium"
        }
        create_response = admin_client.post(f"{BASE_URL}/api/tasks", json=task_data)
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]
        
        # Update status to in_progress
        update_response = admin_client.put(f"{BASE_URL}/api/tasks/{task_id}", json={
            "status": "in_progress"
        })
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated_task = update_response.json()
        assert updated_task.get("status") == "in_progress"
        
        # Update to completed
        complete_response = admin_client.put(f"{BASE_URL}/api/tasks/{task_id}", json={
            "status": "completed"
        })
        assert complete_response.status_code == 200
        completed_task = complete_response.json()
        assert completed_task.get("status") == "completed"
        assert "completed_at" in completed_task
        print(f"✅ Task status updated: pending -> in_progress -> completed")
    
    def test_update_task_fields(self, admin_client):
        """Update task fields (admin)"""
        # Create task
        task_data = {
            "title": "TEST_Field update task",
            "assigned_staff_id": STAFF_ID,
            "task_type": "admin",
            "priority": "low"
        }
        create_response = admin_client.post(f"{BASE_URL}/api/tasks", json=task_data)
        task_id = create_response.json()["id"]
        
        # Update multiple fields
        update_response = admin_client.put(f"{BASE_URL}/api/tasks/{task_id}", json={
            "title": "TEST_Updated title",
            "priority": "urgent",
            "description": "Updated description"
        })
        assert update_response.status_code == 200
        
        updated_task = update_response.json()
        assert updated_task.get("title") == "TEST_Updated title"
        assert updated_task.get("priority") == "urgent"
        assert updated_task.get("description") == "Updated description"
        print("✅ Task fields updated successfully")
    
    def test_filter_tasks_by_status(self, admin_client):
        """Filter tasks by status"""
        response = admin_client.get(f"{BASE_URL}/api/tasks?status=pending")
        assert response.status_code == 200
        
        tasks = response.json()
        for task in tasks:
            assert task.get("status") == "pending"
        print(f"✅ Filtered tasks by status=pending: {len(tasks)} results")
    
    def test_delete_task(self, admin_client):
        """Delete a task"""
        # Create task
        task_data = {
            "title": "TEST_Delete task",
            "assigned_staff_id": STAFF_ID,
            "task_type": "general",
            "priority": "low"
        }
        create_response = admin_client.post(f"{BASE_URL}/api/tasks", json=task_data)
        task_id = create_response.json()["id"]
        
        # Delete task
        delete_response = admin_client.delete(f"{BASE_URL}/api/tasks/{task_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        
        # Verify deletion
        get_response = admin_client.get(f"{BASE_URL}/api/tasks")
        tasks = get_response.json()
        task_ids = [t["id"] for t in tasks]
        assert task_id not in task_ids
        print(f"✅ Task deleted: {task_id}")
    
    def test_delete_nonexistent_task(self, admin_client):
        """Delete non-existent task returns 404"""
        response = admin_client.delete(f"{BASE_URL}/api/tasks/nonexistent_task_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ Delete non-existent task returns 404")


class TestStaffEarnings:
    """Test staff earnings endpoint"""
    
    def test_staff_earnings_requires_staff_role(self, admin_client):
        """Staff earnings endpoint requires staff role"""
        response = admin_client.get(f"{BASE_URL}/api/staff/my-earnings")
        # Admin should get 403 (not a staff member)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✅ Staff earnings endpoint requires staff role (admin gets 403)")


class TestDashboardKPIs:
    """Test dashboard KPIs endpoint"""
    
    def test_dashboard_kpis(self, admin_client):
        """Get dashboard KPIs"""
        response = admin_client.get(f"{BASE_URL}/api/dashboard/kpis")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "role" in data
        assert "revenue_mtd" in data
        assert "occupancy_rate" in data
        assert "active_properties" in data
        assert "active_bookings" in data
        print(f"✅ Dashboard KPIs retrieved: role={data.get('role')}, revenue_mtd={data.get('revenue_mtd')}")


class TestAuthMe:
    """Test auth/me endpoint"""
    
    def test_auth_me(self, admin_client):
        """Get current user info"""
        response = admin_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "role" in data
        assert data.get("role") == "company_admin"
        print(f"✅ Auth/me: user_id={data.get('user_id')}, role={data.get('role')}")
    
    def test_auth_me_unauthenticated(self, unauthenticated_client):
        """Auth/me without session returns 401"""
        response = unauthenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ Unauthenticated auth/me returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
