"""
Backend tests for Staff Payouts CRUD and Owner Financial Reports
Tests: POST/GET/PUT/DELETE /api/payouts, GET /api/reports/owner
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://property-hub-dev-1.preview.emergentagent.com')

# Test session/data from MongoDB seed
SESSION_TOKEN = "test_pay_session_1771873001514"
COMPANY_ID = "comp_pay_1771873001514"
PROPERTY_ID = "prop_pay_1771873001514"
STAFF_ID = "staff_pay_1771873001514"


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestPayoutsCRUD:
    """Test Staff Payout CRUD operations"""
    
    created_payout_id = None
    
    def test_01_create_payout_success(self, api_client):
        """POST /api/payouts creates a payout with all fields"""
        payload = {
            "staff_id": STAFF_ID,
            "property_id": PROPERTY_ID,
            "period_start": "2026-01-01",
            "period_end": "2026-01-15",
            "task_description": "Monthly cleaning services",
            "amount": 500.00,
            "payment_method": "Bank Transfer",
            "notes": "Test payout"
        }
        response = api_client.post(f"{BASE_URL}/api/payouts", json=payload)
        print(f"Create payout response: {response.status_code} - {response.text[:200]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify all fields
        assert "id" in data, "Payout ID missing"
        assert data["staff_id"] == STAFF_ID
        assert data["property_id"] == PROPERTY_ID
        assert data["period_start"] == "2026-01-01"
        assert data["period_end"] == "2026-01-15"
        assert data["task_description"] == "Monthly cleaning services"
        assert data["amount"] == 500.00
        assert data["payment_method"] == "Bank Transfer"
        assert data["status"] == "pending"
        assert data["payment_date"] is None
        
        TestPayoutsCRUD.created_payout_id = data["id"]
        print(f"Created payout ID: {TestPayoutsCRUD.created_payout_id}")
    
    def test_02_get_payouts_enriched(self, api_client):
        """GET /api/payouts returns payouts enriched with staff_name, staff_role, property_name"""
        response = api_client.get(f"{BASE_URL}/api/payouts")
        print(f"List payouts response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our created payout
        payout = next((p for p in data if p.get("id") == TestPayoutsCRUD.created_payout_id), None)
        assert payout is not None, "Created payout not found in list"
        
        # Verify enrichment fields
        assert "staff_name" in payout, "staff_name missing"
        assert "staff_role" in payout, "staff_role missing"
        assert "property_name" in payout, "property_name missing"
        assert payout["staff_name"] == "Jane Housekeeper", f"Expected 'Jane Housekeeper', got {payout['staff_name']}"
        assert payout["staff_role"] == "housekeeper"
        assert payout["property_name"] == "Sunset Villa"
        
        print(f"Payout enriched: staff_name={payout['staff_name']}, role={payout['staff_role']}, property={payout['property_name']}")
    
    def test_03_get_payouts_filter_by_staff(self, api_client):
        """GET /api/payouts?staff_id=X filters payouts by staff member"""
        response = api_client.get(f"{BASE_URL}/api/payouts?staff_id={STAFF_ID}")
        print(f"Filtered payouts response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        # All payouts should belong to this staff
        for payout in data:
            assert payout["staff_id"] == STAFF_ID, f"Payout {payout['id']} has wrong staff_id"
        
        print(f"Found {len(data)} payouts for staff {STAFF_ID}")
    
    def test_04_update_payout_mark_as_paid(self, api_client):
        """PUT /api/payouts/{id} updates status to paid (should auto-set payment_date)"""
        assert TestPayoutsCRUD.created_payout_id, "No payout created yet"
        
        payload = {"status": "paid"}
        response = api_client.put(
            f"{BASE_URL}/api/payouts/{TestPayoutsCRUD.created_payout_id}",
            json=payload
        )
        print(f"Update payout response: {response.status_code} - {response.text[:200]}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "paid"
        assert data["payment_date"] is not None, "payment_date should be auto-set when status=paid"
        print(f"Payout marked as paid, payment_date: {data['payment_date']}")
    
    def test_05_create_second_payout_for_deletion(self, api_client):
        """Create a second payout for deletion test"""
        payload = {
            "staff_id": STAFF_ID,
            "property_id": None,  # All properties
            "period_start": "2026-01-16",
            "period_end": "2026-01-31",
            "task_description": "Extra work",
            "amount": 200.00,
            "payment_method": "Cash",
            "notes": "To be deleted"
        }
        response = api_client.post(f"{BASE_URL}/api/payouts", json=payload)
        assert response.status_code == 200
        data = response.json()
        TestPayoutsCRUD.delete_payout_id = data["id"]
        print(f"Created payout for deletion: {TestPayoutsCRUD.delete_payout_id}")
    
    def test_06_delete_payout(self, api_client):
        """DELETE /api/payouts/{id} removes a payout"""
        payout_id = getattr(TestPayoutsCRUD, 'delete_payout_id', None)
        assert payout_id, "No payout to delete"
        
        response = api_client.delete(f"{BASE_URL}/api/payouts/{payout_id}")
        print(f"Delete payout response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Payout deleted"
        
        # Verify deletion
        verify = api_client.get(f"{BASE_URL}/api/payouts")
        payouts = verify.json()
        assert not any(p.get("id") == payout_id for p in payouts), "Deleted payout still exists"
        print(f"Payout {payout_id} successfully deleted")


class TestOwnerReports:
    """Test Owner Financial Reports endpoint"""
    
    def test_01_get_owner_report_default(self, api_client):
        """GET /api/reports/owner returns property-level financial report"""
        response = api_client.get(f"{BASE_URL}/api/reports/owner")
        print(f"Owner report response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "properties" in data
        assert "summary" in data
        assert isinstance(data["properties"], list)
        
        print(f"Report has {len(data['properties'])} properties")
    
    def test_02_get_owner_report_with_filters(self, api_client):
        """GET /api/reports/owner?year=X&month=Y&property_id=Z supports filtering"""
        response = api_client.get(
            f"{BASE_URL}/api/reports/owner?year=2026&month=1&property_id={PROPERTY_ID}"
        )
        print(f"Filtered owner report: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least our test property
        if len(data["properties"]) > 0:
            prop = data["properties"][0]
            assert prop["property_id"] == PROPERTY_ID
            print(f"Property report: {prop['property_name']}")
    
    def test_03_owner_report_has_required_fields(self, api_client):
        """Verify owner report contains all required fields"""
        response = api_client.get(f"{BASE_URL}/api/reports/owner?year=2026&month=1")
        assert response.status_code == 200
        data = response.json()
        
        # Check summary fields
        summary = data.get("summary", {})
        for field in ["total_revenue", "total_expenses", "net_profit", "avg_occupancy"]:
            assert field in summary, f"Summary missing {field}"
        
        # Check property-level fields
        if len(data["properties"]) > 0:
            prop = data["properties"][0]
            required_fields = [
                "property_id", "property_name", "total_bookings", "occupancy_rate",
                "gross_revenue", "revenue_by_source", "total_expenses", "net_profit",
                "owner_share_pct", "owner_payout_amount", "payout_status"
            ]
            for field in required_fields:
                assert field in prop, f"Property report missing {field}"
            
            print(f"Property {prop['property_name']}:")
            print(f"  - Bookings: {prop['total_bookings']}")
            print(f"  - Occupancy: {prop['occupancy_rate']}%")
            print(f"  - Revenue: ${prop['gross_revenue']}")
            print(f"  - Revenue by source: {prop['revenue_by_source']}")
            print(f"  - Expenses: ${prop['total_expenses']}")
            print(f"  - Net Profit: ${prop['net_profit']}")
            print(f"  - Owner Share: {prop['owner_share_pct']}%")
            print(f"  - Payout Amount: ${prop['owner_payout_amount']}")
            print(f"  - Payout Status: {prop['payout_status']}")


class TestResendAPIKey:
    """Verify Resend API key is configured (not placeholder)"""
    
    def test_01_resend_key_configured(self):
        """Backend should have production Resend API key (not placeholder)"""
        import dotenv
        dotenv.load_dotenv('/app/backend/.env')
        
        resend_key = os.environ.get('RESEND_API_KEY', '')
        sender_email = os.environ.get('SENDER_EMAIL', '')
        
        print(f"RESEND_API_KEY starts with: {resend_key[:10]}..." if resend_key else "MISSING")
        print(f"SENDER_EMAIL: {sender_email}")
        
        # Check key is not placeholder
        assert resend_key, "RESEND_API_KEY is not set"
        assert resend_key.startswith("re_"), "RESEND_API_KEY should start with 're_'"
        assert len(resend_key) > 20, "RESEND_API_KEY looks too short (placeholder?)"
        assert "placeholder" not in resend_key.lower(), "RESEND_API_KEY appears to be a placeholder"
        assert "your" not in resend_key.lower(), "RESEND_API_KEY appears to be a placeholder"
        
        # Check sender email
        assert sender_email, "SENDER_EMAIL is not set"
        assert "@" in sender_email, "SENDER_EMAIL must be valid email"
        
        print("Resend API key is properly configured for production!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
