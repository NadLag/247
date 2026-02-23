"""
Test Suite for Invitation Management Feature (Unified Invite Page)
Tests:
- POST /api/invitations (create with name, assigned_properties, permissions)
- GET /api/invitations (list with dynamically computed status)
- POST /api/invitations/{id}/resend (resend with new token)
- PUT /api/invitations/{id}/cancel (cancel invitation)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestInvitePageAPIs:
    """Tests for invitation management APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test session for each test"""
        import subprocess
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        result = subprocess.run([
            'mongosh', '--quiet', '--eval', f"""
            use('test_database');
            var ts = '{timestamp}';
            var userId = 'test-inv-' + ts;
            var companyId = 'comp_inv_' + ts;
            var sessionToken = 'session_inv_' + ts;
            
            db.companies.insertOne({{
              company_id: companyId,
              name: 'Test Company Inv ' + ts,
              subscription_status: 'trial',
              created_at: new Date(),
              updated_at: new Date()
            }});
            
            db.users.insertOne({{
              user_id: userId,
              email: 'admin.inv.' + ts + '@test.com',
              name: 'Admin Inv ' + ts,
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
            
            db.properties.insertOne({{
              id: 'prop_inv_' + ts + '_1',
              company_id: companyId,
              name: 'Test Property 1',
              address: '123 Test St',
              units: 1,
              owner_first_name: 'Owner',
              owner_last_name: 'One',
              owner_email: 'owner1@test.com',
              active: true,
              created_at: new Date(),
              updated_at: new Date()
            }});
            
            db.properties.insertOne({{
              id: 'prop_inv_' + ts + '_2',
              company_id: companyId,
              name: 'Test Property 2',
              address: '456 Test Ave',
              units: 2,
              owner_first_name: 'Owner',
              owner_last_name: 'Two',
              owner_email: 'owner2@test.com',
              active: true,
              created_at: new Date(),
              updated_at: new Date()
            }});
            
            db.staff.insertOne({{
              id: 'staff_inv_' + ts + '_1',
              company_id: companyId,
              first_name: 'Staff',
              last_name: 'Member',
              email: 'staff1@test.com',
              staff_role: 'housekeeper',
              active: true,
              created_at: new Date(),
              updated_at: new Date()
            }});
            
            print('SESSION:' + sessionToken + ':COMPANY:' + companyId + ':TS:' + ts);
            """
        ], capture_output=True, text=True)
        
        output = result.stdout.strip().split('\n')[-1]
        parts = output.split(':')
        self.session_token = parts[1]
        self.company_id = parts[3]
        self.timestamp = parts[5]
        
        self.headers = {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json"
        }
        
        yield
        
        # Cleanup
        subprocess.run([
            'mongosh', '--quiet', '--eval', f"""
            use('test_database');
            db.users.deleteMany({{user_id: /^test-inv-{self.timestamp}/}});
            db.user_sessions.deleteMany({{session_token: /^session_inv_{self.timestamp}/}});
            db.companies.deleteMany({{company_id: /^comp_inv_{self.timestamp}/}});
            db.properties.deleteMany({{id: /^prop_inv_{self.timestamp}/}});
            db.staff.deleteMany({{id: /^staff_inv_{self.timestamp}/}});
            db.invitations.deleteMany({{company_id: /^comp_inv_{self.timestamp}/}});
            """
        ], capture_output=True, text=True)

    def test_01_invitations_list_empty(self):
        """GET /api/invitations returns empty list initially"""
        response = requests.get(f"{BASE_URL}/api/invitations", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        assert len(data) == 0, "Expected empty list"
        print("PASS: GET /api/invitations returns empty list")

    def test_02_create_invitation_with_name_properties_permissions(self):
        """POST /api/invitations accepts name, assigned_properties, permissions"""
        payload = {
            "email": f"invited.staff.{self.timestamp}@test.com",
            "role": "staff",
            "name": "Invited Staff Member",
            "assigned_properties": [f"prop_inv_{self.timestamp}_1"],
            "permissions": {
                "view_financials": True,
                "manage_bookings": True,
                "manage_tasks": False
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have id"
        assert data["email"] == payload["email"], f"Email mismatch: {data.get('email')}"
        assert data["name"] == payload["name"], f"Name mismatch: {data.get('name')}"
        assert data["role"] == payload["role"], f"Role mismatch: {data.get('role')}"
        assert data["assigned_properties"] == payload["assigned_properties"], f"Properties mismatch"
        assert data["permissions"] == payload["permissions"], f"Permissions mismatch"
        assert data["status"] == "pending", f"Status should be pending, got {data.get('status')}"
        assert "token" in data, "Response should have token"
        assert "expires_at" in data, "Response should have expires_at"
        
        print("PASS: POST /api/invitations creates invitation with name, properties, permissions")
        return data["id"]

    def test_03_invitations_list_after_create(self):
        """GET /api/invitations returns created invitation with computed status"""
        # First create an invitation
        payload = {
            "email": f"test.owner.{self.timestamp}@test.com",
            "role": "owner",
            "name": "Test Owner",
            "assigned_properties": [f"prop_inv_{self.timestamp}_2"],
            "permissions": {}
        }
        create_resp = requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        assert create_resp.status_code == 201
        
        # List invitations
        response = requests.get(f"{BASE_URL}/api/invitations", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, "Should have at least 1 invitation"
        
        inv = data[0]
        assert "id" in inv, "Invitation should have id"
        assert "email" in inv, "Invitation should have email"
        assert "name" in inv, "Invitation should have name"
        assert "role" in inv, "Invitation should have role"
        assert "assigned_properties" in inv, "Invitation should have assigned_properties"
        assert "status" in inv, "Invitation should have computed status"
        assert "created_at" in inv, "Invitation should have created_at"
        assert "expires_at" in inv, "Invitation should have expires_at"
        
        # Status should be dynamically computed as pending for new invitation
        assert inv["status"] == "pending", f"Expected pending status, got {inv['status']}"
        
        print("PASS: GET /api/invitations returns invitations with computed status")

    def test_04_resend_invitation_generates_new_token(self):
        """POST /api/invitations/{id}/resend generates new token"""
        # Create invitation
        payload = {
            "email": f"resend.test.{self.timestamp}@test.com",
            "role": "staff",
            "name": "Resend Test"
        }
        create_resp = requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        assert create_resp.status_code == 201
        created = create_resp.json()
        inv_id = created["id"]
        original_token = created["token"]
        
        # Resend
        resend_resp = requests.post(f"{BASE_URL}/api/invitations/{inv_id}/resend", headers=self.headers)
        assert resend_resp.status_code == 200, f"Expected 200, got {resend_resp.status_code}: {resend_resp.text}"
        
        resend_data = resend_resp.json()
        assert "message" in resend_data
        assert "invalidated" in resend_data["message"].lower() or "queued" in resend_data["message"].lower()
        
        # Verify token changed
        list_resp = requests.get(f"{BASE_URL}/api/invitations", headers=self.headers)
        assert list_resp.status_code == 200
        invitations = list_resp.json()
        
        resent_inv = next((i for i in invitations if i["id"] == inv_id), None)
        assert resent_inv is not None, "Invitation should still exist"
        assert resent_inv["token"] != original_token, "Token should be different after resend"
        assert resent_inv["status"] == "pending", "Status should be pending after resend"
        
        print("PASS: POST /api/invitations/{id}/resend generates new token")

    def test_05_cancel_invitation(self):
        """PUT /api/invitations/{id}/cancel sets status to cancelled"""
        # Create invitation
        payload = {
            "email": f"cancel.test.{self.timestamp}@test.com",
            "role": "owner",
            "name": "Cancel Test Owner"
        }
        create_resp = requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        assert create_resp.status_code == 201
        inv_id = create_resp.json()["id"]
        original_token = create_resp.json()["token"]
        
        # Cancel
        cancel_resp = requests.put(f"{BASE_URL}/api/invitations/{inv_id}/cancel", headers=self.headers)
        assert cancel_resp.status_code == 200, f"Expected 200, got {cancel_resp.status_code}: {cancel_resp.text}"
        
        cancel_data = cancel_resp.json()
        assert "message" in cancel_data
        assert "cancelled" in cancel_data["message"].lower()
        
        # Verify status is cancelled
        list_resp = requests.get(f"{BASE_URL}/api/invitations", headers=self.headers)
        assert list_resp.status_code == 200
        invitations = list_resp.json()
        
        cancelled_inv = next((i for i in invitations if i["id"] == inv_id), None)
        assert cancelled_inv is not None, "Cancelled invitation should still exist"
        assert cancelled_inv["status"] == "cancelled", f"Status should be cancelled, got {cancelled_inv['status']}"
        assert cancelled_inv["token"] != original_token, "Token should be invalidated after cancel"
        assert cancelled_inv["token"].startswith("cancelled_"), "Token should start with 'cancelled_'"
        
        print("PASS: PUT /api/invitations/{id}/cancel sets status to cancelled")

    def test_06_cannot_resend_cancelled_invitation(self):
        """POST /api/invitations/{id}/resend fails for cancelled invitation"""
        # Create and cancel
        payload = {
            "email": f"no.resend.{self.timestamp}@test.com",
            "role": "staff"
        }
        create_resp = requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        inv_id = create_resp.json()["id"]
        
        requests.put(f"{BASE_URL}/api/invitations/{inv_id}/cancel", headers=self.headers)
        
        # Try to resend
        resend_resp = requests.post(f"{BASE_URL}/api/invitations/{inv_id}/resend", headers=self.headers)
        assert resend_resp.status_code == 400, f"Expected 400, got {resend_resp.status_code}"
        
        print("PASS: Cannot resend cancelled invitation")

    def test_07_create_owner_invitation(self):
        """POST /api/invitations creates owner invitation correctly"""
        payload = {
            "email": f"owner.invite.{self.timestamp}@test.com",
            "role": "owner",
            "name": "Property Owner Test",
            "assigned_properties": [f"prop_inv_{self.timestamp}_1", f"prop_inv_{self.timestamp}_2"],
            "permissions": {}
        }
        
        response = requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        assert response.status_code == 201
        
        data = response.json()
        assert data["role"] == "owner"
        assert len(data["assigned_properties"]) == 2
        
        print("PASS: POST /api/invitations creates owner invitation")

    def test_08_status_columns_in_response(self):
        """GET /api/invitations returns all required columns for table"""
        # Create invitation with all fields
        payload = {
            "email": f"columns.test.{self.timestamp}@test.com",
            "role": "staff",
            "name": "Column Test User",
            "assigned_properties": [f"prop_inv_{self.timestamp}_1"],
            "permissions": {"view_financials": False, "manage_bookings": True}
        }
        requests.post(f"{BASE_URL}/api/invitations", headers=self.headers, json=payload)
        
        response = requests.get(f"{BASE_URL}/api/invitations", headers=self.headers)
        assert response.status_code == 200
        
        invitations = response.json()
        inv = invitations[0]
        
        # Verify all required table columns are present
        required_fields = ["id", "name", "email", "role", "assigned_properties", "status", "created_at", "expires_at", "token"]
        for field in required_fields:
            assert field in inv, f"Missing required field: {field}"
        
        print("PASS: GET /api/invitations returns all required table columns")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
