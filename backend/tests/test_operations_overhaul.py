"""
Test Operations Page Overhaul Features
- Auto-task generation when staff is created/updated with assigned properties
- Verify Sync Tasks endpoint is still available but button removed from UI
- Task API structure for expandable cards
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session from mongosh setup
TEST_SESSION_TOKEN = "test_ops_session_1772128760701"
TEST_COMPANY_ID = "comp_ops_1772128760701"
TEST_USER_ID = "test-admin-ops-1772128760701"
TEST_PROPERTY_ID = "prop_ops_1772128760701"


@pytest.fixture(scope="module")
def admin_session():
    """Provide admin session for tests"""
    session = requests.Session()
    session.cookies.set("session_token", TEST_SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestAutoTaskGenerationOnStaffCreate:
    """Test that tasks are auto-generated when staff is created with assigned properties"""
    
    def test_auth_me_works(self, admin_session):
        """Verify authentication works"""
        response = admin_session.get(f"{BASE_URL}/api/auth/me")
        print(f"Auth/me response: {response.status_code}")
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("role") == "company_admin"
        print(f"Authenticated as admin: {data.get('name')}")
    
    def test_create_booking_for_auto_task_test(self, admin_session):
        """Create a future booking to test auto-task generation"""
        today = datetime.now()
        check_in = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        check_out = (today + timedelta(days=6)).strftime("%Y-%m-%d")
        
        booking_data = {
            "property_id": TEST_PROPERTY_ID,
            "guest_name": "Auto Task Test Guest",
            "check_in": check_in,
            "check_out": check_out,
            "total_amount": 500,
            "guests_count": 2,
            "status": "confirmed",
            "booking_type": "reservation"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/bookings", json=booking_data)
        print(f"Create booking response: {response.status_code} - {response.text[:200]}")
        assert response.status_code == 201, f"Failed to create booking: {response.text}"
        booking = response.json()
        assert booking.get("id") is not None
        # Store booking_id for cleanup
        TestAutoTaskGenerationOnStaffCreate.test_booking_id = booking["id"]
        print(f"Created booking: {booking['id']}")
    
    def test_create_housekeeper_with_properties_triggers_auto_tasks(self, admin_session):
        """Creating a housekeeper with assigned_properties should auto-generate cleaning tasks"""
        staff_data = {
            "first_name": "Auto",
            "last_name": "Housekeeper",
            "phone": "1234567890",
            "email": f"autohk{uuid.uuid4().hex[:8]}@test.com",
            "salary": 2000,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "housekeeper",
            "assigned_properties": [TEST_PROPERTY_ID]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/staff", json=staff_data)
        print(f"Create housekeeper response: {response.status_code}")
        assert response.status_code == 201, f"Failed to create staff: {response.text}"
        staff = response.json()
        TestAutoTaskGenerationOnStaffCreate.housekeeper_id = staff["id"]
        print(f"Created housekeeper: {staff['id']}")
        
        # Check if tasks were auto-generated
        tasks_response = admin_session.get(f"{BASE_URL}/api/tasks")
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        
        # Look for auto-generated cleaning task for this staff
        auto_tasks = [t for t in tasks if t.get("auto_generated") and t.get("assigned_staff_id") == staff["id"]]
        print(f"Found {len(auto_tasks)} auto-generated tasks for housekeeper")
        
        # Verify at least one cleaning task was created
        cleaning_tasks = [t for t in auto_tasks if t.get("task_type") == "cleaning"]
        assert len(cleaning_tasks) >= 1, "Expected at least 1 cleaning task to be auto-generated"
        print(f"Auto-generated cleaning tasks: {len(cleaning_tasks)}")
    
    def test_create_cohost_with_properties_triggers_auto_tasks(self, admin_session):
        """Creating a co_host with assigned_properties should auto-generate check_in/check_out tasks"""
        staff_data = {
            "first_name": "Auto",
            "last_name": "CoHost",
            "phone": "0987654321",
            "email": f"autoch{uuid.uuid4().hex[:8]}@test.com",
            "salary": 3000,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "co_host",
            "assigned_properties": [TEST_PROPERTY_ID]
        }
        
        response = admin_session.post(f"{BASE_URL}/api/staff", json=staff_data)
        print(f"Create co_host response: {response.status_code}")
        assert response.status_code == 201, f"Failed to create staff: {response.text}"
        staff = response.json()
        TestAutoTaskGenerationOnStaffCreate.cohost_id = staff["id"]
        print(f"Created co_host: {staff['id']}")
        
        # Check if tasks were auto-generated
        tasks_response = admin_session.get(f"{BASE_URL}/api/tasks")
        assert tasks_response.status_code == 200
        tasks = tasks_response.json()
        
        # Look for auto-generated tasks for this co_host
        auto_tasks = [t for t in tasks if t.get("auto_generated") and t.get("assigned_staff_id") == staff["id"]]
        print(f"Found {len(auto_tasks)} auto-generated tasks for co_host")
        
        # Verify check_in and check_out tasks were created
        checkin_tasks = [t for t in auto_tasks if t.get("task_type") == "check_in"]
        checkout_tasks = [t for t in auto_tasks if t.get("task_type") == "check_out"]
        
        assert len(checkin_tasks) >= 1, "Expected at least 1 check_in task"
        assert len(checkout_tasks) >= 1, "Expected at least 1 check_out task"
        print(f"Auto-generated check_in tasks: {len(checkin_tasks)}, check_out tasks: {len(checkout_tasks)}")


class TestAutoTaskGenerationOnStaffUpdate:
    """Test that tasks are auto-generated when staff is updated with new property assignments"""
    
    def test_create_staff_without_properties(self, admin_session):
        """Create staff without assigned properties - no tasks should be generated"""
        staff_data = {
            "first_name": "Update",
            "last_name": "TestStaff",
            "phone": "5555555555",
            "email": f"updatetest{uuid.uuid4().hex[:8]}@test.com",
            "salary": 2500,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "housekeeper",
            "assigned_properties": []  # No properties initially
        }
        
        response = admin_session.post(f"{BASE_URL}/api/staff", json=staff_data)
        assert response.status_code == 201
        staff = response.json()
        TestAutoTaskGenerationOnStaffUpdate.update_test_staff_id = staff["id"]
        print(f"Created staff without properties: {staff['id']}")
        
        # Verify no tasks generated
        tasks_response = admin_session.get(f"{BASE_URL}/api/tasks")
        tasks = tasks_response.json()
        staff_tasks = [t for t in tasks if t.get("assigned_staff_id") == staff["id"]]
        assert len(staff_tasks) == 0, "No tasks should be generated for staff without properties"
        print("Verified no tasks generated for staff without properties")
    
    def test_update_staff_adding_properties_triggers_auto_tasks(self, admin_session):
        """Updating staff to add property assignments should trigger auto-task generation"""
        staff_id = TestAutoTaskGenerationOnStaffUpdate.update_test_staff_id
        
        update_data = {
            "assigned_properties": [TEST_PROPERTY_ID]
        }
        
        response = admin_session.put(f"{BASE_URL}/api/staff/{staff_id}", json=update_data)
        print(f"Update staff response: {response.status_code}")
        assert response.status_code == 200, f"Failed to update staff: {response.text}"
        
        # Check if tasks were auto-generated
        tasks_response = admin_session.get(f"{BASE_URL}/api/tasks")
        tasks = tasks_response.json()
        
        staff_tasks = [t for t in tasks if t.get("assigned_staff_id") == staff_id and t.get("auto_generated")]
        print(f"Found {len(staff_tasks)} auto-generated tasks after staff update")
        
        assert len(staff_tasks) >= 1, "Expected tasks to be auto-generated when properties assigned"
        print(f"Successfully verified auto-task generation on staff update")


class TestTaskAPIStructure:
    """Test task API returns correct structure for expandable cards"""
    
    def test_tasks_list_includes_booking_id(self, admin_session):
        """Verify tasks include booking_id for linking to booking details"""
        response = admin_session.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 200
        tasks = response.json()
        
        # Find an auto-generated task
        auto_tasks = [t for t in tasks if t.get("auto_generated")]
        if auto_tasks:
            task = auto_tasks[0]
            assert "booking_id" in task, "Tasks should include booking_id field"
            print(f"Task includes booking_id: {task.get('booking_id')}")
    
    def test_tasks_include_required_fields(self, admin_session):
        """Verify task API returns all required fields for display"""
        response = admin_session.get(f"{BASE_URL}/api/tasks")
        assert response.status_code == 200
        tasks = response.json()
        
        if tasks:
            task = tasks[0]
            required_fields = ["id", "task_type", "property_id", "due_date", "status", "priority"]
            for field in required_fields:
                assert field in task, f"Task missing required field: {field}"
            print(f"Task has all required fields")
            
            # Check optional but expected fields
            expected_fields = ["assigned_staff_id", "auto_generated", "created_at"]
            for field in expected_fields:
                if field not in task:
                    print(f"Warning: Task missing expected field: {field}")


class TestRegenerateTasksEndpoint:
    """Test the regenerate tasks endpoint exists (for backward compatibility)"""
    
    def test_regenerate_endpoint_exists(self, admin_session):
        """Verify /api/tasks/regenerate-for-bookings endpoint exists"""
        response = admin_session.post(f"{BASE_URL}/api/tasks/regenerate-for-bookings")
        print(f"Regenerate tasks response: {response.status_code}")
        # Should be 200 (success) or require auth (401), but not 404
        assert response.status_code != 404, "Regenerate endpoint should exist"
        if response.status_code == 200:
            data = response.json()
            print(f"Regenerate response: {data}")
            assert "regenerated" in data or "message" in data or "bookings_processed" in data
        print("Regenerate tasks endpoint exists and works")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, admin_session):
        """Clean up test data created during tests"""
        # Delete staff
        staff_ids = []
        if hasattr(TestAutoTaskGenerationOnStaffCreate, 'housekeeper_id'):
            staff_ids.append(TestAutoTaskGenerationOnStaffCreate.housekeeper_id)
        if hasattr(TestAutoTaskGenerationOnStaffCreate, 'cohost_id'):
            staff_ids.append(TestAutoTaskGenerationOnStaffCreate.cohost_id)
        if hasattr(TestAutoTaskGenerationOnStaffUpdate, 'update_test_staff_id'):
            staff_ids.append(TestAutoTaskGenerationOnStaffUpdate.update_test_staff_id)
        
        for staff_id in staff_ids:
            admin_session.delete(f"{BASE_URL}/api/staff/{staff_id}")
            print(f"Deleted staff: {staff_id}")
        
        # Delete booking
        if hasattr(TestAutoTaskGenerationOnStaffCreate, 'test_booking_id'):
            admin_session.delete(f"{BASE_URL}/api/bookings/{TestAutoTaskGenerationOnStaffCreate.test_booking_id}")
            print(f"Deleted booking: {TestAutoTaskGenerationOnStaffCreate.test_booking_id}")
        
        # Delete auto-generated tasks
        tasks_response = admin_session.get(f"{BASE_URL}/api/tasks")
        if tasks_response.status_code == 200:
            tasks = tasks_response.json()
            for task in tasks:
                if task.get("auto_generated"):
                    admin_session.delete(f"{BASE_URL}/api/tasks/{task['id']}")
                    print(f"Deleted auto task: {task['id']}")
        
        print("Cleanup completed")
