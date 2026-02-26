"""
Test: Staff-Property Linking Automation Feature
- When assigning a Co-Host to a property, the property is auto-added to the co-host's assigned_properties
- When assigning a Housekeeper to a property, the property is auto-added to the housekeeper's assigned_properties  
- Tasks are auto-generated for existing bookings when staff is assigned to a property
- GET /api/staff/housekeepers endpoint returns active housekeepers
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'session_stafflink_1772130568662')

class TestStaffPropertyLink:
    """Tests for automatic staff-property linking when assigned via properties page"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }
    
    def test_auth_me(self):
        """Test authentication works"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data.get("role") == "company_admin"
        print(f"✓ Auth works, user: {data.get('name')}")
    
    def test_get_housekeepers_endpoint(self):
        """Test GET /api/staff/housekeepers endpoint returns active housekeepers"""
        response = requests.get(f"{BASE_URL}/api/staff/housekeepers", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/staff/housekeepers returns {len(data)} housekeepers")
    
    def test_get_cohosts_endpoint(self):
        """Test GET /api/staff/cohosts endpoint returns active co-hosts"""
        response = requests.get(f"{BASE_URL}/api/staff/cohosts", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/staff/cohosts returns {len(data)} co-hosts")


class TestCoHostPropertyAssignment:
    """Test Co-Host assignment from property creates bidirectional link"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }
        self.created_property_id = None
        self.created_cohost_id = None
        self.created_booking_id = None
    
    def test_full_cohost_assignment_flow(self):
        """
        Full flow: 
        1. Create co-host staff WITHOUT properties
        2. Create property WITHOUT assigning co-host
        3. Create booking for the property
        4. Update property to assign co-host
        5. Verify co-host's assigned_properties now includes the property
        6. Verify tasks auto-generated for the booking
        """
        # Step 1: Create co-host WITHOUT assigned properties
        cohost_data = {
            "first_name": "TEST_CoHost",
            "last_name": f"Link_{datetime.now().timestamp()}",
            "phone": "555-0001",
            "email": f"cohost.link.{datetime.now().timestamp()}@test.com",
            "salary": 2000,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "co_host",
            "assigned_properties": []  # IMPORTANT: Start with no properties
        }
        response = requests.post(f"{BASE_URL}/api/staff", headers=self.headers, json=cohost_data)
        assert response.status_code == 201, f"Failed to create co-host: {response.text}"
        cohost = response.json()
        self.created_cohost_id = cohost["id"]
        assert cohost.get("assigned_properties", []) == [], "Co-host should start with no properties"
        print(f"✓ Step 1: Created co-host {cohost['first_name']} {cohost['last_name']} with ID {cohost['id']}")
        
        # Step 2: Create property WITHOUT co-host assigned
        property_data = {
            "name": f"TEST_CoHostLink_Property_{datetime.now().timestamp()}",
            "address": "123 Test Street",
            "property_type": "Apartment",
            "rooms": 2,
            "bathrooms": 1,
            "city": "Test City",
            "country": "United States",
            "owner_first_name": "Test",
            "owner_last_name": "Owner",
            "owner_phone": "555-0002",
            "owner_email": "owner@test.com",
            "units": 1
        }
        response = requests.post(f"{BASE_URL}/api/properties", headers=self.headers, json=property_data)
        assert response.status_code == 201, f"Failed to create property: {response.text}"
        prop = response.json()
        self.created_property_id = prop["id"]
        print(f"✓ Step 2: Created property '{prop['name']}' with ID {prop['id']}")
        
        # Step 3: Create a booking for this property (future dates)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        booking_data = {
            "property_id": prop["id"],
            "guest_name": "TEST_Link Guest",
            "check_in": tomorrow,
            "check_out": checkout,
            "total_amount": 500,
            "guests_count": 2,
            "status": "confirmed"
        }
        response = requests.post(f"{BASE_URL}/api/bookings", headers=self.headers, json=booking_data)
        assert response.status_code == 201, f"Failed to create booking: {response.text}"
        booking = response.json()
        self.created_booking_id = booking["id"]
        print(f"✓ Step 3: Created booking '{booking['guest_name']}' with ID {booking['id']}")
        
        # Step 4: Update property to assign the co-host
        update_data = {"assigned_cohost": self.created_cohost_id}
        response = requests.put(
            f"{BASE_URL}/api/properties/{self.created_property_id}", 
            headers=self.headers, 
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update property: {response.text}"
        updated_prop = response.json()
        assert updated_prop.get("assigned_cohost") == self.created_cohost_id
        print(f"✓ Step 4: Updated property with assigned_cohost = {self.created_cohost_id}")
        
        # Step 5: Verify co-host's assigned_properties now includes the property
        response = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert response.status_code == 200
        staff_list = response.json()
        cohost_updated = next((s for s in staff_list if s["id"] == self.created_cohost_id), None)
        assert cohost_updated is not None, "Co-host not found in staff list"
        assigned_props = cohost_updated.get("assigned_properties", [])
        assert self.created_property_id in assigned_props, \
            f"Property {self.created_property_id} should be in co-host's assigned_properties. Got: {assigned_props}"
        print(f"✓ Step 5: Co-host's assigned_properties now includes {self.created_property_id}")
        
        # Step 6: Verify tasks were auto-generated for the booking
        response = requests.get(f"{BASE_URL}/api/tasks", headers=self.headers)
        assert response.status_code == 200
        tasks = response.json()
        cohost_tasks = [t for t in tasks if t.get("assigned_staff_id") == self.created_cohost_id 
                       and t.get("booking_id") == self.created_booking_id]
        # Co-host should have check_in and check_out tasks
        task_types = [t.get("task_type") for t in cohost_tasks]
        assert "check_in" in task_types or len(cohost_tasks) > 0, \
            f"Expected check_in/check_out tasks for co-host. Got task types: {task_types}"
        print(f"✓ Step 6: Found {len(cohost_tasks)} auto-generated tasks for co-host: {task_types}")
        
        return {
            "cohost_id": self.created_cohost_id,
            "property_id": self.created_property_id,
            "booking_id": self.created_booking_id,
            "tasks_count": len(cohost_tasks)
        }


class TestHousekeeperPropertyAssignment:
    """Test Housekeeper assignment from property creates bidirectional link"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }
    
    def test_full_housekeeper_assignment_flow(self):
        """
        Full flow: 
        1. Create housekeeper staff WITHOUT properties
        2. Create property WITHOUT assigning housekeeper
        3. Create booking for the property
        4. Update property to assign housekeeper
        5. Verify housekeeper's assigned_properties now includes the property
        6. Verify cleaning task auto-generated for the booking
        """
        # Step 1: Create housekeeper WITHOUT assigned properties
        hk_data = {
            "first_name": "TEST_Housekeeper",
            "last_name": f"Link_{datetime.now().timestamp()}",
            "phone": "555-0011",
            "email": f"hk.link.{datetime.now().timestamp()}@test.com",
            "salary": 1500,
            "payment_terms": "Bi-Weekly",
            "payment_type": "per_job",
            "staff_role": "housekeeper",
            "assigned_properties": []
        }
        response = requests.post(f"{BASE_URL}/api/staff", headers=self.headers, json=hk_data)
        assert response.status_code == 201, f"Failed to create housekeeper: {response.text}"
        housekeeper = response.json()
        hk_id = housekeeper["id"]
        assert housekeeper.get("assigned_properties", []) == []
        print(f"✓ Step 1: Created housekeeper {housekeeper['first_name']} with ID {hk_id}")
        
        # Step 2: Create property
        property_data = {
            "name": f"TEST_HKLink_Property_{datetime.now().timestamp()}",
            "address": "456 Test Ave",
            "property_type": "Villa",
            "rooms": 3,
            "bathrooms": 2,
            "city": "Test City",
            "country": "United States",
            "owner_first_name": "Property",
            "owner_last_name": "Owner",
            "owner_phone": "555-0012",
            "owner_email": "owner2@test.com",
            "units": 1
        }
        response = requests.post(f"{BASE_URL}/api/properties", headers=self.headers, json=property_data)
        assert response.status_code == 201
        prop = response.json()
        prop_id = prop["id"]
        print(f"✓ Step 2: Created property '{prop['name']}' with ID {prop_id}")
        
        # Step 3: Create booking
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d")
        booking_data = {
            "property_id": prop_id,
            "guest_name": "TEST_HK Guest",
            "check_in": tomorrow,
            "check_out": checkout,
            "total_amount": 700,
            "guests_count": 3,
            "status": "confirmed"
        }
        response = requests.post(f"{BASE_URL}/api/bookings", headers=self.headers, json=booking_data)
        assert response.status_code == 201
        booking = response.json()
        booking_id = booking["id"]
        print(f"✓ Step 3: Created booking with ID {booking_id}")
        
        # Step 4: Update property to assign housekeeper
        update_data = {"assigned_housekeeper": hk_id}
        response = requests.put(f"{BASE_URL}/api/properties/{prop_id}", headers=self.headers, json=update_data)
        assert response.status_code == 200
        updated_prop = response.json()
        assert updated_prop.get("assigned_housekeeper") == hk_id
        print(f"✓ Step 4: Updated property with assigned_housekeeper = {hk_id}")
        
        # Step 5: Verify housekeeper's assigned_properties includes the property
        response = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert response.status_code == 200
        staff_list = response.json()
        hk_updated = next((s for s in staff_list if s["id"] == hk_id), None)
        assert hk_updated is not None
        assigned_props = hk_updated.get("assigned_properties", [])
        assert prop_id in assigned_props, \
            f"Property {prop_id} should be in housekeeper's assigned_properties. Got: {assigned_props}"
        print(f"✓ Step 5: Housekeeper's assigned_properties now includes {prop_id}")
        
        # Step 6: Verify cleaning task auto-generated
        response = requests.get(f"{BASE_URL}/api/tasks", headers=self.headers)
        assert response.status_code == 200
        tasks = response.json()
        hk_tasks = [t for t in tasks if t.get("assigned_staff_id") == hk_id 
                   and t.get("booking_id") == booking_id]
        task_types = [t.get("task_type") for t in hk_tasks]
        assert "cleaning" in task_types, \
            f"Expected cleaning task for housekeeper. Got task types: {task_types}"
        print(f"✓ Step 6: Found cleaning task for housekeeper: {task_types}")
        
        return {"success": True, "hk_id": hk_id, "prop_id": prop_id, "booking_id": booking_id}


class TestPropertyCreationWithStaffAssigned:
    """Test creating property with staff already assigned during creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }
    
    def test_create_property_with_cohost_and_housekeeper(self):
        """
        Create property with both co-host and housekeeper assigned at creation time
        Verify both staff members get the property added to their assigned_properties
        """
        # Create co-host first
        cohost_data = {
            "first_name": "TEST_PropCreate_CoHost",
            "last_name": f"{datetime.now().timestamp()}",
            "phone": "555-0021",
            "email": f"propcreate.cohost.{datetime.now().timestamp()}@test.com",
            "staff_role": "co_host",
            "assigned_properties": []
        }
        response = requests.post(f"{BASE_URL}/api/staff", headers=self.headers, json=cohost_data)
        assert response.status_code == 201
        cohost = response.json()
        cohost_id = cohost["id"]
        print(f"✓ Created co-host for property creation test: {cohost_id}")
        
        # Create housekeeper
        hk_data = {
            "first_name": "TEST_PropCreate_HK",
            "last_name": f"{datetime.now().timestamp()}",
            "phone": "555-0022",
            "email": f"propcreate.hk.{datetime.now().timestamp()}@test.com",
            "staff_role": "housekeeper",
            "assigned_properties": []
        }
        response = requests.post(f"{BASE_URL}/api/staff", headers=self.headers, json=hk_data)
        assert response.status_code == 201
        hk = response.json()
        hk_id = hk["id"]
        print(f"✓ Created housekeeper for property creation test: {hk_id}")
        
        # Create property with BOTH assigned
        property_data = {
            "name": f"TEST_PropWithBoth_{datetime.now().timestamp()}",
            "address": "789 Combined St",
            "property_type": "House",
            "rooms": 4,
            "bathrooms": 3,
            "city": "Test City",
            "country": "United States",
            "owner_first_name": "Combined",
            "owner_last_name": "Owner",
            "owner_phone": "555-0023",
            "owner_email": "combined@test.com",
            "units": 1,
            "assigned_cohost": cohost_id,
            "assigned_housekeeper": hk_id
        }
        response = requests.post(f"{BASE_URL}/api/properties", headers=self.headers, json=property_data)
        assert response.status_code == 201
        prop = response.json()
        prop_id = prop["id"]
        print(f"✓ Created property with both staff assigned: {prop_id}")
        
        # Verify property has both assigned
        assert prop.get("assigned_cohost") == cohost_id
        assert prop.get("assigned_housekeeper") == hk_id
        
        # Verify both staff members now have this property in their assigned_properties
        response = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert response.status_code == 200
        staff_list = response.json()
        
        cohost_updated = next((s for s in staff_list if s["id"] == cohost_id), None)
        hk_updated = next((s for s in staff_list if s["id"] == hk_id), None)
        
        assert cohost_updated is not None, "Co-host not found"
        assert hk_updated is not None, "Housekeeper not found"
        
        cohost_props = cohost_updated.get("assigned_properties", [])
        hk_props = hk_updated.get("assigned_properties", [])
        
        assert prop_id in cohost_props, \
            f"Property {prop_id} should be in co-host's assigned_properties. Got: {cohost_props}"
        assert prop_id in hk_props, \
            f"Property {prop_id} should be in housekeeper's assigned_properties. Got: {hk_props}"
        
        print(f"✓ Both co-host and housekeeper have property {prop_id} in their assigned_properties")
        print(f"  - Co-host assigned_properties: {cohost_props}")
        print(f"  - Housekeeper assigned_properties: {hk_props}")
        
        return {"success": True, "prop_id": prop_id, "cohost_id": cohost_id, "hk_id": hk_id}


class TestTeamPageShowsAssignedProperties:
    """Test that Team page shows assigned_properties for each team member"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SESSION_TOKEN}"
        }
    
    def test_staff_endpoint_includes_assigned_properties(self):
        """Verify GET /api/staff returns assigned_properties field for each staff member"""
        # First create a staff with assigned properties
        prop_response = requests.get(f"{BASE_URL}/api/properties", headers=self.headers)
        properties = prop_response.json() if prop_response.ok else []
        prop_ids = [p["id"] for p in properties[:2]] if properties else []
        
        staff_data = {
            "first_name": "TEST_TeamPage",
            "last_name": f"Staff_{datetime.now().timestamp()}",
            "phone": "555-0031",
            "email": f"teampage.{datetime.now().timestamp()}@test.com",
            "staff_role": "co_host",
            "assigned_properties": prop_ids
        }
        response = requests.post(f"{BASE_URL}/api/staff", headers=self.headers, json=staff_data)
        assert response.status_code == 201
        created_staff = response.json()
        staff_id = created_staff["id"]
        print(f"✓ Created staff {staff_id} with assigned_properties: {prop_ids}")
        
        # Get staff list and verify assigned_properties field exists
        response = requests.get(f"{BASE_URL}/api/staff", headers=self.headers)
        assert response.status_code == 200
        staff_list = response.json()
        
        staff_record = next((s for s in staff_list if s["id"] == staff_id), None)
        assert staff_record is not None
        assert "assigned_properties" in staff_record, \
            "Staff record should include assigned_properties field"
        assert staff_record["assigned_properties"] == prop_ids, \
            f"Expected assigned_properties {prop_ids}, got {staff_record['assigned_properties']}"
        
        print(f"✓ Staff endpoint returns assigned_properties for team member display")
        return {"success": True}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
