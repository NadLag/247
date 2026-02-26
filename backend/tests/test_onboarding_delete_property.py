"""
Test Suite for:
1. Onboarding Wizard - Single step with Add/Sync Property options (Manual or OTA via iCal)
2. DELETE /api/properties/{id} - Removes property_id from staff's assigned_properties

Test the two fixes from the problem statement:
- Onboarding wizard should have ONE step for Add/Sync Property
- When deleting a property, the property ID should be removed from staff's assigned_properties array
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "session_del_1772132239235"  # Created by mongosh


class TestDeletePropertyCascade:
    """
    Test DELETE /api/properties/{id} removes property_id from all staff's assigned_properties arrays
    This fixes the issue where raw property IDs like 'prop_22fbacc794c5' show on Team page after deletion
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }

    def test_delete_property_removes_from_staff_assigned_properties(self):
        """
        Test the full flow:
        1. Create a property
        2. Create a staff member with that property in assigned_properties
        3. Verify staff has the property
        4. Delete the property
        5. Verify staff's assigned_properties no longer contains the deleted property ID
        """
        # Step 1: Create a property
        property_data = {
            "name": "Test Property for Deletion Cascade",
            "address": "123 Test Street",
            "property_type": "apartment",
            "owner_first_name": "Test",
            "owner_last_name": "Owner",
            "owner_phone": "1234567890",
            "owner_email": "owner@test.com",
            "units": 1,
            "active": True
        }
        resp = requests.post(f"{BASE_URL}/api/properties", json=property_data, headers=self.headers)
        assert resp.status_code == 201, f"Failed to create property: {resp.text}"
        created_property = resp.json()
        property_id = created_property["id"]
        print(f"Created property: {property_id}")

        # Step 2: Create a staff member with that property in assigned_properties
        staff_data = {
            "first_name": "Test",
            "last_name": "Staff",
            "phone": "1234567890",
            "email": f"teststaff_{int(time.time())}@test.com",
            "salary": 1000,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "housekeeper",
            "assigned_properties": [property_id]
        }
        resp = requests.post(f"{BASE_URL}/api/staff", json=staff_data, headers=self.headers)
        assert resp.status_code == 201, f"Failed to create staff: {resp.text}"
        created_staff = resp.json()
        staff_id = created_staff["id"]
        print(f"Created staff: {staff_id}")

        # Step 3: Verify staff has the property in assigned_properties
        resp = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert resp.status_code == 200
        staff_list = resp.json()
        staff_record = next((s for s in staff_list if s["id"] == staff_id), None)
        assert staff_record is not None, "Staff not found"
        assert property_id in staff_record.get("assigned_properties", []), \
            f"Property {property_id} not in staff's assigned_properties before delete"
        print(f"Verified staff has property {property_id} in assigned_properties")

        # Step 4: Delete the property
        resp = requests.delete(f"{BASE_URL}/api/properties/{property_id}", headers=self.headers)
        assert resp.status_code == 200, f"Failed to delete property: {resp.text}"
        print(f"Deleted property: {property_id}")

        # Step 5: Verify staff's assigned_properties no longer contains the deleted property ID
        resp = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert resp.status_code == 200
        staff_list = resp.json()
        staff_record = next((s for s in staff_list if s["id"] == staff_id), None)
        assert staff_record is not None, "Staff not found after property deletion"
        
        assigned_props = staff_record.get("assigned_properties", [])
        assert property_id not in assigned_props, \
            f"CRITICAL: Property {property_id} STILL in staff's assigned_properties after delete! Got: {assigned_props}"
        print(f"SUCCESS: Property {property_id} removed from staff's assigned_properties")
        print(f"Staff's current assigned_properties: {assigned_props}")

        # Cleanup: Delete the staff
        requests.delete(f"{BASE_URL}/api/staff/{staff_id}", headers=self.headers)

    def test_delete_property_cascades_to_multiple_staff(self):
        """Test that deleting a property removes it from multiple staff members"""
        # Create a property
        property_data = {
            "name": "Multi-Staff Test Property",
            "address": "456 Test Avenue",
            "property_type": "house",
            "owner_first_name": "Test",
            "owner_last_name": "Owner2",
            "owner_phone": "9876543210",
            "owner_email": "owner2@test.com",
            "units": 1,
            "active": True
        }
        resp = requests.post(f"{BASE_URL}/api/properties", json=property_data, headers=self.headers)
        assert resp.status_code == 201
        property_id = resp.json()["id"]
        print(f"Created property: {property_id}")

        # Create two staff members with the same property
        staff_ids = []
        for i, role in enumerate(["housekeeper", "co_host"]):
            staff_data = {
                "first_name": f"Staff{i}",
                "last_name": "Test",
                "phone": f"555000{i}000",
                "email": f"multistaff{i}_{int(time.time())}@test.com",
                "salary": 1000,
                "payment_terms": "Monthly",
                "payment_type": "salary",
                "staff_role": role,
                "assigned_properties": [property_id]
            }
            resp = requests.post(f"{BASE_URL}/api/staff", json=staff_data, headers=self.headers)
            assert resp.status_code == 201
            staff_ids.append(resp.json()["id"])
            print(f"Created {role} staff: {staff_ids[-1]}")

        # Verify both staff have the property
        resp = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        staff_list = resp.json()
        for sid in staff_ids:
            staff = next((s for s in staff_list if s["id"] == sid), None)
            assert property_id in staff.get("assigned_properties", [])

        # Delete the property
        resp = requests.delete(f"{BASE_URL}/api/properties/{property_id}", headers=self.headers)
        assert resp.status_code == 200
        print(f"Deleted property: {property_id}")

        # Verify BOTH staff no longer have the property
        resp = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        staff_list = resp.json()
        for sid in staff_ids:
            staff = next((s for s in staff_list if s["id"] == sid), None)
            assert staff is not None
            assigned = staff.get("assigned_properties", [])
            assert property_id not in assigned, \
                f"Property {property_id} still in staff {sid}'s assigned_properties: {assigned}"
            print(f"SUCCESS: Staff {sid} no longer has deleted property")

        # Cleanup
        for sid in staff_ids:
            requests.delete(f"{BASE_URL}/api/staff/{sid}", headers=self.headers)


class TestPropertyEndpoints:
    """Test basic property CRUD operations"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }

    def test_create_property_manual(self):
        """Test manual property creation (simulating onboarding wizard manual flow)"""
        property_data = {
            "name": "Manual Test Property",
            "address": "",
            "property_type": "",
            "owner_first_name": "",
            "owner_last_name": "",
            "owner_phone": "",
            "owner_email": "",
            "units": 1,
            "active": True
        }
        resp = requests.post(f"{BASE_URL}/api/properties", json=property_data, headers=self.headers)
        assert resp.status_code == 201, f"Failed to create property: {resp.text}"
        created = resp.json()
        assert created["name"] == "Manual Test Property"
        assert "id" in created
        print(f"Created manual property: {created['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/properties/{created['id']}", headers=self.headers)

    def test_list_properties(self):
        """Test listing properties"""
        resp = requests.get(f"{BASE_URL}/api/properties", headers=self.headers)
        assert resp.status_code == 200, f"Failed to list properties: {resp.text}"
        properties = resp.json()
        assert isinstance(properties, list)
        print(f"Listed {len(properties)} properties")


class TestOTAImportProperty:
    """Test OTA iCal import for onboarding wizard"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }

    def test_ota_import_endpoint_exists(self):
        """Test that the OTA import endpoint exists and handles requests"""
        # Using a mock iCal URL for testing
        import_data = {
            "name": "OTA Import Test Property",
            "source": "airbnb",
            "ical_url": "https://example.com/invalid-ical-url"
        }
        resp = requests.post(f"{BASE_URL}/api/ota/import-property", json=import_data, headers=self.headers)
        # It might fail due to invalid URL, but we're testing the endpoint exists
        # Status should be either success (201) or a specific error (400/422), not 404
        assert resp.status_code != 404, "OTA import endpoint not found"
        print(f"OTA import endpoint response: {resp.status_code} - {resp.text[:200]}")


class TestCompanyOnboarding:
    """Test company onboarding completion flag"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }

    def test_company_onboarding_update(self):
        """Test updating company onboarding_completed flag"""
        update_data = {"onboarding_completed": True}
        resp = requests.put(f"{BASE_URL}/api/companies/me", json=update_data, headers=self.headers)
        assert resp.status_code == 200, f"Failed to update company: {resp.text}"
        print("Company onboarding_completed updated successfully")

        # Verify the company has onboarding_completed
        resp = requests.get(f"{BASE_URL}/api/companies/me", headers=self.headers)
        assert resp.status_code == 200
        company = resp.json()
        assert company.get("onboarding_completed") == True, "onboarding_completed not set"
        print(f"Company onboarding_completed: {company.get('onboarding_completed')}")


class TestStaffAssignedProperties:
    """Test staff assigned_properties field is correctly exposed"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }

    def test_staff_list_includes_assigned_properties(self):
        """Test that GET /api/staff returns assigned_properties field"""
        # Create a property first
        prop_resp = requests.post(f"{BASE_URL}/api/properties", json={
            "name": "Staff Test Property",
            "address": "789 Staff St",
            "property_type": "apartment",
            "owner_first_name": "Owner",
            "owner_last_name": "Test",
            "owner_phone": "1111111111",
            "owner_email": "staffowner@test.com",
            "units": 1,
            "active": True
        }, headers=self.headers)
        assert prop_resp.status_code == 201
        prop_id = prop_resp.json()["id"]

        # Create a staff with assigned properties
        staff_resp = requests.post(f"{BASE_URL}/api/staff", json={
            "first_name": "Assigned",
            "last_name": "Test",
            "phone": "2222222222",
            "email": f"assignedtest_{int(time.time())}@test.com",
            "salary": 1000,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "housekeeper",
            "assigned_properties": [prop_id]
        }, headers=self.headers)
        assert staff_resp.status_code == 201
        staff_id = staff_resp.json()["id"]

        # Get staff list and verify assigned_properties field is present
        resp = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert resp.status_code == 200
        staff_list = resp.json()
        staff = next((s for s in staff_list if s["id"] == staff_id), None)
        assert staff is not None
        assert "assigned_properties" in staff, "assigned_properties field missing from staff response"
        assert prop_id in staff["assigned_properties"]
        print(f"Staff assigned_properties field present and contains {prop_id}")

        # Cleanup
        requests.delete(f"{BASE_URL}/api/staff/{staff_id}", headers=self.headers)
        requests.delete(f"{BASE_URL}/api/properties/{prop_id}", headers=self.headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
