"""
Test Unified Invite Page - New Invitation Management Features

Tests for the centralized invitation management system:
1. POST /api/invitations - creates invitation with name, assigned_properties, permissions fields
2. GET /api/invitations - returns invitations with dynamically computed status (pending/accepted/expired/cancelled)
3. POST /api/invitations/{id}/resend - generates new token, new expiry, invalidates old link
4. PUT /api/invitations/{id}/cancel - sets status to cancelled and clears token
5. GET /api/invitations/validate/{token} - rejects cancelled/expired invitation tokens
6. DELETE /api/invitations/{id} - removes invitation
7. Registration stores assigned_properties and permissions from invitation
"""
import pytest
import requests
import os
import time
import subprocess
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://booking-hub-174.preview.emergentagent.com')


@pytest.fixture(scope="module")
def admin_session():
    """Create admin session for testing with company and properties"""
    timestamp = str(int(time.time() * 1000))
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
use('test_database');
var timestamp = {timestamp};
var userId = 'test-invite-pytest-' + timestamp;
var companyId = 'comp_invite_pytest_' + timestamp;
var sessionToken = 'test_invite_session_' + timestamp;
var propId1 = 'prop_test1_' + timestamp;
var propId2 = 'prop_test2_' + timestamp;
var staffId = 'staff_test_' + timestamp;

db.companies.insertOne({{
  company_id: companyId,
  name: 'Invite Pytest Company',
  subscription_status: 'trial',
  created_at: new Date(),
  updated_at: new Date()
}});

db.users.insertOne({{
  user_id: userId,
  email: 'admin.invite.pytest.' + timestamp + '@example.com',
  name: 'Invite Pytest Admin',
  company_id: companyId,
  role: 'company_admin',
  created_at: new Date(),
  updated_at: new Date()
}});

db.user_sessions.insertOne({{
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});

// Create test properties
db.properties.insertOne({{
  id: propId1,
  company_id: companyId,
  name: 'Test Beach Villa',
  address: '123 Beach Road',
  property_type: 'villa',
  units: 1,
  active: true,
  owner_first_name: 'John',
  owner_last_name: 'Smith',
  owner_email: 'owner_pytest_{timestamp}@example.com',
  owner_phone: '+1234567890',
  created_at: new Date(),
  updated_at: new Date()
}});

db.properties.insertOne({{
  id: propId2,
  company_id: companyId,
  name: 'Test Mountain Cabin',
  address: '456 Mountain Lane',
  property_type: 'cabin',
  units: 1,
  active: true,
  owner_first_name: 'Jane',
  owner_last_name: 'Doe',
  owner_email: 'owner2_pytest_{timestamp}@example.com',
  owner_phone: '+0987654321',
  created_at: new Date(),
  updated_at: new Date()
}});

// Create test staff member
db.staff.insertOne({{
  id: staffId,
  company_id: companyId,
  first_name: 'Test',
  last_name: 'Staff',
  email: 'staff_pytest_{timestamp}@example.com',
  phone: '+1111111111',
  staff_role: 'housekeeper',
  active: true,
  created_at: new Date(),
  updated_at: new Date()
}});

print('SESSION_TOKEN=' + sessionToken);
print('COMPANY_ID=' + companyId);
print('PROPERTY_ID_1=' + propId1);
print('PROPERTY_ID_2=' + propId2);
print('STAFF_ID=' + staffId);
'''
    ], capture_output=True, text=True)
    
    data = {}
    for line in result.stdout.split('\n'):
        if '=' in line and line.startswith(('SESSION_TOKEN', 'COMPANY_ID', 'PROPERTY_ID', 'STAFF_ID')):
            key, val = line.split('=', 1)
            data[key.lower()] = val
    
    assert data.get('session_token'), f"Failed to create session token. Output: {result.stdout}"
    return data


class TestInvitationCreation:
    """Tests for POST /api/invitations with new fields"""
    
    def test_01_create_invitation_with_name(self, admin_session):
        """POST /api/invitations - creates invitation with name field"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": f"named_staff_{int(time.time())}@example.com",
            "role": "staff",
            "name": "John Doe"
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "name" in data, "name field should be in response"
        assert data["name"] == "John Doe", f"Expected name 'John Doe', got '{data['name']}'"
        assert data["role"] == "staff"
        assert data["used"] == False
        assert data["status"] == "pending"
        print(f"✓ Created invitation with name: {data['name']}")
    
    def test_02_create_invitation_with_assigned_properties(self, admin_session):
        """POST /api/invitations - creates invitation with assigned_properties"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        prop_id1 = admin_session.get('property_id_1')
        prop_id2 = admin_session.get('property_id_2')
        
        payload = {
            "email": f"props_staff_{int(time.time())}@example.com",
            "role": "staff",
            "name": "Property Staff",
            "assigned_properties": [prop_id1, prop_id2]
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "assigned_properties" in data, "assigned_properties field should be in response"
        assert isinstance(data["assigned_properties"], list)
        assert len(data["assigned_properties"]) == 2
        assert prop_id1 in data["assigned_properties"]
        assert prop_id2 in data["assigned_properties"]
        print(f"✓ Created invitation with {len(data['assigned_properties'])} assigned properties")
    
    def test_03_create_invitation_with_permissions(self, admin_session):
        """POST /api/invitations - creates invitation with permissions"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": f"perms_staff_{int(time.time())}@example.com",
            "role": "staff",
            "name": "Permission Staff",
            "permissions": {
                "view_financials": False,
                "manage_bookings": True,
                "manage_tasks": True
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "permissions" in data, "permissions field should be in response"
        assert isinstance(data["permissions"], dict)
        assert data["permissions"].get("view_financials") == False
        assert data["permissions"].get("manage_bookings") == True
        assert data["permissions"].get("manage_tasks") == True
        print(f"✓ Created invitation with permissions: {data['permissions']}")
    
    def test_04_create_owner_invitation(self, admin_session):
        """POST /api/invitations - creates owner invitation"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": f"owner_{int(time.time())}@example.com",
            "role": "owner",
            "name": "Property Owner",
            "assigned_properties": [admin_session.get('property_id_1')]
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["role"] == "owner"
        assert "token" in data and len(data["token"]) > 0
        print(f"✓ Created owner invitation for {data['email']}")


class TestInvitationListWithStatus:
    """Tests for GET /api/invitations with dynamic status computation"""
    
    def test_05_list_invitations_returns_status(self, admin_session):
        """GET /api/invitations - returns invitations with status field"""
        headers = {"Authorization": f"Bearer {admin_session['session_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        invitations = response.json()
        
        assert isinstance(invitations, list)
        for inv in invitations:
            assert "status" in inv, "Each invitation should have status field"
            assert inv["status"] in ["pending", "accepted", "expired", "cancelled"], f"Unknown status: {inv['status']}"
            assert "email" in inv
            assert "role" in inv
            assert "created_at" in inv
            assert "expires_at" in inv
        
        print(f"✓ Listed {len(invitations)} invitations with status fields")
    
    def test_06_list_invitations_shows_name_and_properties(self, admin_session):
        """GET /api/invitations - shows name and assigned_properties"""
        headers = {"Authorization": f"Bearer {admin_session['session_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        
        assert response.status_code == 200
        invitations = response.json()
        
        # Find an invitation with name
        named_inv = next((inv for inv in invitations if inv.get("name")), None)
        assert named_inv, "Should have at least one invitation with name"
        
        # Verify structure
        for inv in invitations:
            assert "name" in inv, "name field should exist (even if empty)"
            assert "assigned_properties" in inv, "assigned_properties should exist"
        
        print(f"✓ Invitations contain name and assigned_properties fields")


class TestResendInvitation:
    """Tests for POST /api/invitations/{id}/resend - new token generation"""
    
    def test_07_resend_generates_new_token(self, admin_session):
        """POST /api/invitations/{id}/resend - generates new token and expiry"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"resend_test_{int(time.time())}@example.com",
            "role": "staff",
            "name": "Resend Test"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert create_response.status_code == 201
        inv = create_response.json()
        inv_id = inv["id"]
        old_token = inv["token"]
        old_expires = inv["expires_at"]
        
        # Small delay to ensure different timestamp
        time.sleep(1)
        
        # Resend invitation
        resend_response = requests.post(f"{BASE_URL}/api/invitations/{inv_id}/resend", headers=headers)
        
        assert resend_response.status_code == 200, f"Expected 200, got {resend_response.status_code}: {resend_response.text}"
        data = resend_response.json()
        assert "message" in data
        assert "invalidated" in data["message"].lower() or "new" in data["message"].lower()
        
        # Verify token changed
        list_response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        invitations = list_response.json()
        updated_inv = next((i for i in invitations if i["id"] == inv_id), None)
        
        assert updated_inv, f"Could not find invitation {inv_id}"
        assert updated_inv["token"] != old_token, "Token should be different after resend"
        assert updated_inv["expires_at"] != old_expires, "Expiry should be updated"
        
        print(f"✓ Resend generated new token (old: {old_token[:10]}..., new: {updated_inv['token'][:10]}...)")
    
    def test_08_old_token_invalid_after_resend(self, admin_session):
        """Old token should not work after resend"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"old_token_test_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert create_response.status_code == 201
        inv = create_response.json()
        inv_id = inv["id"]
        old_token = inv["token"]
        
        # Resend to invalidate old token
        requests.post(f"{BASE_URL}/api/invitations/{inv_id}/resend", headers=headers)
        
        # Try to validate old token
        validate_response = requests.get(f"{BASE_URL}/api/invitations/validate/{old_token}")
        
        # Old token should now be invalid (404)
        assert validate_response.status_code == 404, f"Expected 404 for old token, got {validate_response.status_code}"
        print("✓ Old token is correctly invalidated after resend")


class TestCancelInvitation:
    """Tests for PUT /api/invitations/{id}/cancel"""
    
    def test_09_cancel_invitation_sets_status(self, admin_session):
        """PUT /api/invitations/{id}/cancel - sets status to cancelled"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"cancel_test_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert create_response.status_code == 201
        inv = create_response.json()
        inv_id = inv["id"]
        token = inv["token"]
        
        # Cancel invitation
        cancel_response = requests.put(f"{BASE_URL}/api/invitations/{inv_id}/cancel", headers=headers)
        
        assert cancel_response.status_code == 200, f"Expected 200, got {cancel_response.status_code}: {cancel_response.text}"
        data = cancel_response.json()
        assert "message" in data
        assert "cancelled" in data["message"].lower()
        
        # Verify status is cancelled
        list_response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        invitations = list_response.json()
        cancelled_inv = next((i for i in invitations if i["id"] == inv_id), None)
        
        assert cancelled_inv, f"Could not find invitation {inv_id}"
        assert cancelled_inv["status"] == "cancelled", f"Expected status 'cancelled', got '{cancelled_inv['status']}'"
        
        print(f"✓ Invitation cancelled successfully")
    
    def test_10_cancelled_token_cleared(self, admin_session):
        """PUT /api/invitations/{id}/cancel - invalidates the token"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"token_clear_test_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert create_response.status_code == 201
        inv = create_response.json()
        inv_id = inv["id"]
        original_token = inv["token"]
        
        # Cancel invitation
        cancel_response = requests.put(f"{BASE_URL}/api/invitations/{inv_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
        
        # Verify token is changed (old token no longer valid)
        list_response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        invitations = list_response.json()
        cancelled_inv = next((i for i in invitations if i["id"] == inv_id), None)
        
        # Token should be different from original (either cancelled_* or empty)
        current_token = cancelled_inv.get("token", "")
        assert current_token != original_token, f"Token should change after cancel"
        # Token is replaced with cancelled_* prefix or cleared
        assert current_token == "" or current_token.startswith("cancelled_") or current_token is None, f"Unexpected token: {current_token}"
        print("✓ Token invalidated after cancellation")


class TestValidateInvitation:
    """Tests for GET /api/invitations/validate/{token}"""
    
    def test_11_validate_cancelled_token_rejected(self, admin_session):
        """GET /api/invitations/validate/{token} - rejects cancelled invitation"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create and get token before cancelling
        payload = {
            "email": f"validate_cancel_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        inv = create_response.json()
        inv_id = inv["id"]
        token = inv["token"]
        
        # Cancel the invitation
        cancel_response = requests.put(f"{BASE_URL}/api/invitations/{inv_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
        
        # Try to validate with the original token (which is now removed/invalid)
        validate_response = requests.get(f"{BASE_URL}/api/invitations/validate/{token}")
        
        # Should fail because token was removed ($unset) from the invitation
        assert validate_response.status_code in [400, 404], f"Expected 400/404 for cancelled invitation, got {validate_response.status_code}"
        print("✓ Cancelled invitation token correctly rejected")
    
    def test_12_validate_valid_token_works(self, admin_session):
        """GET /api/invitations/validate/{token} - validates valid token"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"validate_good_{int(time.time())}@example.com",
            "role": "staff",
            "name": "Valid User"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        inv = create_response.json()
        token = inv["token"]
        
        # Validate token
        validate_response = requests.get(f"{BASE_URL}/api/invitations/validate/{token}")
        
        assert validate_response.status_code == 200, f"Expected 200, got {validate_response.status_code}: {validate_response.text}"
        data = validate_response.json()
        
        assert data["email"] == payload["email"]
        assert data["role"] == "staff"
        assert "company_name" in data
        assert "used" in data
        assert data["used"] == False
        print(f"✓ Valid token validated successfully for {data['email']}")


class TestDeleteInvitation:
    """Tests for DELETE /api/invitations/{id}"""
    
    def test_13_delete_invitation(self, admin_session):
        """DELETE /api/invitations/{id} - removes invitation"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"delete_test_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        inv = create_response.json()
        inv_id = inv["id"]
        
        # Delete invitation
        delete_response = requests.delete(f"{BASE_URL}/api/invitations/{inv_id}", headers=headers)
        
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        
        # Verify it's gone
        list_response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        invitations = list_response.json()
        deleted_inv = next((i for i in invitations if i["id"] == inv_id), None)
        
        assert deleted_inv is None, f"Invitation {inv_id} should be deleted"
        print("✓ Invitation deleted successfully")
    
    def test_14_delete_nonexistent_returns_404(self, admin_session):
        """DELETE /api/invitations/{invalid_id} - returns 404"""
        headers = {"Authorization": f"Bearer {admin_session['session_token']}"}
        
        response = requests.delete(f"{BASE_URL}/api/invitations/inv_nonexistent_xyz", headers=headers)
        
        assert response.status_code == 404
        print("✓ Delete nonexistent invitation returns 404")


class TestResendCannotResendCancelled:
    """Tests that cancelled invitations cannot be resent"""
    
    def test_15_resend_cancelled_fails(self, admin_session):
        """POST /api/invitations/{id}/resend - fails for cancelled invitation"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create invitation
        payload = {
            "email": f"resend_cancelled_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        inv = create_response.json()
        inv_id = inv["id"]
        
        # Cancel the invitation
        cancel_response = requests.put(f"{BASE_URL}/api/invitations/{inv_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
        
        # Try to resend - should fail because invitation is cancelled
        resend_response = requests.post(f"{BASE_URL}/api/invitations/{inv_id}/resend", headers=headers)
        
        assert resend_response.status_code == 400, f"Expected 400 for cancelled invitation resend, got {resend_response.status_code}: {resend_response.text}"
        assert "cancelled" in resend_response.json()["detail"].lower()
        print("✓ Cannot resend cancelled invitation")


class TestInvitation48HourExpiry:
    """Tests for 48-hour token expiry"""
    
    def test_16_invitation_expires_in_48_hours(self, admin_session):
        """POST /api/invitations - creates invitation with 48-hour expiry"""
        headers = {
            "Authorization": f"Bearer {admin_session['session_token']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": f"expiry_test_{int(time.time())}@example.com",
            "role": "staff"
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert response.status_code == 201
        data = response.json()
        
        # Parse expiry and verify it's approximately 48 hours from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        now = datetime.now(expires_at.tzinfo)
        
        # Should be within 48 hours + 5 minute buffer
        expected_expiry = now + timedelta(hours=48)
        diff = abs((expires_at - expected_expiry).total_seconds())
        
        assert diff < 300, f"Expiry should be ~48 hours from now, diff was {diff} seconds"
        print(f"✓ Invitation expires in 48 hours (at {expires_at.isoformat()})")


class TestCleanup:
    """Cleanup test data"""
    
    def test_99_cleanup(self, admin_session):
        """Cleanup test invitations"""
        headers = {"Authorization": f"Bearer {admin_session['session_token']}"}
        
        # Get all invitations created during test
        response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        if response.status_code == 200:
            invitations = response.json()
            for inv in invitations:
                requests.delete(f"{BASE_URL}/api/invitations/{inv['id']}", headers=headers)
        
        print("✓ Test cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
