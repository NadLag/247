"""
Test OTA Mock Simulation and Invitation Email Features

Tests:
1. OTA simulate-sync endpoint (POST /api/ota/simulate-sync)
2. OTA property-specific sync (POST /api/ota/simulate-property-sync/{property_id})
3. OTA sync logs (GET /api/ota-sync-logs)
4. Invitations with email_sent field (POST /api/invitations)
5. Resend invitation email (POST /api/invitations/{id}/resend)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://lodging-dashboard-qa.preview.emergentagent.com')


@pytest.fixture(scope="module")
def admin_session():
    """Create admin session for testing"""
    import subprocess
    timestamp = str(int(time.time() * 1000))
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
use('test_database');
var timestamp = {timestamp};
var userId = 'test-ota-pytest-' + timestamp;
var companyId = 'comp_ota_pytest_' + timestamp;
var sessionToken = 'test_ota_pytest_session_' + timestamp;

db.companies.insertOne({{
  company_id: companyId,
  name: 'OTA Pytest Company',
  subscription_status: 'trial',
  created_at: new Date(),
  updated_at: new Date()
}});

db.users.insertOne({{
  user_id: userId,
  email: 'admin.ota.pytest.' + timestamp + '@example.com',
  name: 'OTA Pytest Admin',
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

print('SESSION_TOKEN=' + sessionToken);
print('COMPANY_ID=' + companyId);
'''
    ], capture_output=True, text=True)
    
    session_token = None
    company_id = None
    for line in result.stdout.split('\n'):
        if line.startswith('SESSION_TOKEN='):
            session_token = line.split('=')[1]
        if line.startswith('COMPANY_ID='):
            company_id = line.split('=')[1]
    
    assert session_token, "Failed to create session token"
    
    return {"session_token": session_token, "company_id": company_id}


@pytest.fixture(scope="module")
def seeded_data(admin_session):
    """Seed demo data for testing"""
    headers = {"Authorization": f"Bearer {admin_session['session_token']}"}
    response = requests.post(f"{BASE_URL}/api/seed-demo-data", headers=headers)
    assert response.status_code == 200
    return admin_session


class TestOTASimulation:
    """Tests for OTA mock simulation endpoints"""
    
    def test_ota_simulate_sync_all_properties(self, seeded_data):
        """POST /api/ota/simulate-sync - creates mock bookings from random OTA sources"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/ota/simulate-sync", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "message" in data
        assert "synced" in data
        assert isinstance(data["synced"], int)
        assert data["synced"] >= 0
        
        if data["synced"] > 0:
            assert "results" in data
            assert len(data["results"]) == data["synced"]
            
            # Verify booking details
            for result in data["results"]:
                assert "property" in result
                assert "source" in result
                assert result["source"] in ["airbnb", "booking.com", "vrbo", "expedia"]
                assert "guest" in result
                assert "check_in" in result
                assert "check_out" in result
    
    def test_ota_simulate_property_sync(self, seeded_data):
        """POST /api/ota/simulate-property-sync/{property_id} - creates mock bookings for specific property"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        # Get a property ID first
        props_response = requests.get(f"{BASE_URL}/api/properties", headers=headers)
        assert props_response.status_code == 200
        properties = props_response.json()
        assert len(properties) > 0
        
        property_id = properties[0]["id"]
        property_name = properties[0]["name"]
        
        response = requests.post(f"{BASE_URL}/api/ota/simulate-property-sync/{property_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "message" in data
        assert "property" in data
        assert data["property"] == property_name
        assert "synced" in data
        assert data["synced"] >= 1  # Always generates 1-3 bookings
        assert data["synced"] <= 3
        
        assert "bookings" in data
        for booking in data["bookings"]:
            assert "source" in booking
            assert booking["source"] in ["airbnb", "booking.com", "vrbo", "expedia"]
            assert "guest" in booking
            assert "check_in" in booking
            assert "check_out" in booking
            assert "amount" in booking
            assert isinstance(booking["amount"], int)
    
    def test_ota_simulate_property_sync_invalid_property(self, seeded_data):
        """POST /api/ota/simulate-property-sync/{invalid_id} - returns 404"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/ota/simulate-property-sync/invalid_prop_id", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_ota_sync_logs(self, seeded_data):
        """GET /api/ota-sync-logs - returns sync logs"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        # First trigger a sync to ensure logs exist
        requests.post(f"{BASE_URL}/api/ota/simulate-sync", headers=headers)
        time.sleep(1)  # Wait for background tasks
        
        response = requests.get(f"{BASE_URL}/api/ota-sync-logs", headers=headers)
        
        assert response.status_code == 200
        logs = response.json()
        
        assert isinstance(logs, list)
        if len(logs) > 0:
            log = logs[0]
            assert "id" in log
            assert "company_id" in log
            assert "source" in log
            assert "event_type" in log
            assert "status" in log
            assert log["status"] in ["pending", "completed", "failed"]
            assert "created_at" in log
    
    def test_ota_sync_logs_filter_by_status(self, seeded_data):
        """GET /api/ota-sync-logs?status=completed - filters by status"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/ota-sync-logs?status=completed", headers=headers)
        
        assert response.status_code == 200
        logs = response.json()
        
        for log in logs:
            assert log["status"] == "completed"
    
    def test_ota_sync_logs_filter_by_source(self, seeded_data):
        """GET /api/ota-sync-logs?source=airbnb - filters by source"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/ota-sync-logs?source=airbnb", headers=headers)
        
        assert response.status_code == 200
        logs = response.json()
        
        for log in logs:
            assert log["source"] == "airbnb"


class TestInvitationsWithEmail:
    """Tests for invitation endpoints with email functionality"""
    
    def test_create_invitation_has_email_sent_field(self, seeded_data):
        """POST /api/invitations - creates invitation with email_sent field"""
        headers = {
            "Authorization": f"Bearer {seeded_data['session_token']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": f"test_staff_{int(time.time())}@example.com",
            "role": "staff"
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check invitation structure
        assert "id" in data
        assert "email" in data
        assert data["email"] == payload["email"]
        assert "role" in data
        assert data["role"] == "staff"
        assert "token" in data
        assert "used" in data
        assert data["used"] == False
        assert "email_sent" in data  # New field!
        assert isinstance(data["email_sent"], bool)
        assert "expires_at" in data
        assert "created_at" in data
    
    def test_create_invitation_owner_role(self, seeded_data):
        """POST /api/invitations - creates owner invitation"""
        headers = {
            "Authorization": f"Bearer {seeded_data['session_token']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": f"test_owner_{int(time.time())}@example.com",
            "role": "owner"
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["role"] == "owner"
        assert "email_sent" in data
    
    def test_list_invitations_shows_email_sent(self, seeded_data):
        """GET /api/invitations - shows email_sent status"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/invitations", headers=headers)
        
        assert response.status_code == 200
        invitations = response.json()
        
        assert isinstance(invitations, list)
        for inv in invitations:
            assert "email_sent" in inv
    
    def test_resend_invitation_email(self, seeded_data):
        """POST /api/invitations/{id}/resend - resends invitation email"""
        headers = {
            "Authorization": f"Bearer {seeded_data['session_token']}",
            "Content-Type": "application/json"
        }
        
        # Create an invitation first
        payload = {
            "email": f"test_resend_{int(time.time())}@example.com",
            "role": "staff"
        }
        create_response = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert create_response.status_code == 201
        invitation = create_response.json()
        inv_id = invitation["id"]
        
        # Resend the email
        resend_response = requests.post(f"{BASE_URL}/api/invitations/{inv_id}/resend", headers=headers)
        
        assert resend_response.status_code == 200
        data = resend_response.json()
        assert "message" in data
        assert "queued" in data["message"].lower() or "resend" in data["message"].lower()
    
    def test_resend_invitation_email_invalid_id(self, seeded_data):
        """POST /api/invitations/{invalid_id}/resend - returns 404"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        response = requests.post(f"{BASE_URL}/api/invitations/invalid_inv_id/resend", headers=headers)
        
        assert response.status_code == 404
    
    def test_create_duplicate_invitation_fails(self, seeded_data):
        """POST /api/invitations - duplicate email fails"""
        headers = {
            "Authorization": f"Bearer {seeded_data['session_token']}",
            "Content-Type": "application/json"
        }
        
        email = f"test_duplicate_{int(time.time())}@example.com"
        payload = {"email": email, "role": "staff"}
        
        # Create first invitation
        response1 = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = requests.post(f"{BASE_URL}/api/invitations", headers=headers, json=payload)
        assert response2.status_code == 400
        assert "already" in response2.json()["detail"].lower()


class TestOTABookingsIntegration:
    """Tests that OTA sync actually creates bookings"""
    
    def test_ota_sync_creates_bookings_with_ota_source(self, seeded_data):
        """Verify OTA sync creates bookings with ota_source field"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        # Get initial booking count
        initial_response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        initial_bookings = initial_response.json()
        initial_count = len(initial_bookings)
        
        # Trigger OTA sync
        sync_response = requests.post(f"{BASE_URL}/api/ota/simulate-sync", headers=headers)
        assert sync_response.status_code == 200
        synced_count = sync_response.json()["synced"]
        
        # Wait for background tasks
        time.sleep(2)
        
        # Check new bookings
        new_response = requests.get(f"{BASE_URL}/api/bookings", headers=headers)
        new_bookings = new_response.json()
        new_count = len(new_bookings)
        
        # Verify bookings were created
        assert new_count >= initial_count + synced_count
        
        # Verify OTA bookings have ota_source field
        ota_bookings = [b for b in new_bookings if b.get("ota_source")]
        assert len(ota_bookings) > 0
        
        for booking in ota_bookings:
            assert booking["ota_source"] in ["airbnb", "booking.com", "vrbo", "expedia"]
            assert "ota_external_id" in booking


class TestBookingsPageOTAIntegration:
    """Tests for OTA sync from Bookings page"""
    
    def test_bookings_by_status_includes_ota_bookings(self, seeded_data):
        """GET /api/bookings/by-status - includes OTA synced bookings"""
        headers = {"Authorization": f"Bearer {seeded_data['session_token']}"}
        
        # First trigger OTA sync
        requests.post(f"{BASE_URL}/api/ota/simulate-sync", headers=headers)
        time.sleep(2)
        
        # Get bookings by status
        response = requests.get(f"{BASE_URL}/api/bookings/by-status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all status categories exist
        assert "checked_in_today" in data
        assert "upcoming" in data
        assert "confirmed" in data
        assert "checked_out" in data
        assert "cancelled" in data
        
        # Check for OTA bookings in confirmed or upcoming
        all_bookings = data.get("confirmed", []) + data.get("upcoming", [])
        ota_bookings = [b for b in all_bookings if b.get("ota_source")]
        
        # Should have some OTA bookings after sync
        assert len(ota_bookings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
