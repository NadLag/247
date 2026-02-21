import requests
import json
import sys
from datetime import datetime
import time

class PropertyManagementAPITester:
    def __init__(self, base_url="https://revenue-dashboard-38.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.company_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name} - {details}")
        
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        
        # Default headers
        default_headers = {'Content-Type': 'application/json'}
        if self.token:
            default_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            default_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Expected {expected_status}, got {response.status_code}"
            if not success and response.status_code != expected_status:
                try:
                    error_response = response.json()
                    details += f" - {error_response.get('detail', 'Unknown error')}"
                except:
                    details += f" - {response.text[:100]}"

            self.log_result(name, success, details if not success else "")
            
            if success:
                try:
                    return response.json()
                except:
                    return {}
            return None

        except requests.exceptions.RequestException as e:
            self.log_result(name, False, f"Request failed: {str(e)}")
            return None

    def test_subscription_plans(self):
        """Test subscription plans endpoint (public)"""
        print("\n🔍 Testing Subscription Plans...")
        result = self.run_test("Get Subscription Plans", "GET", "api/subscription/plans", 200)
        if result:
            expected_plans = ["starter", "professional", "enterprise"]
            if all(plan in result for plan in expected_plans):
                self.log_result("Plans contain expected tiers", True)
            else:
                self.log_result("Plans contain expected tiers", False, f"Missing plans: {result}")

    def test_auth_endpoints_without_auth(self):
        """Test auth endpoints without authentication"""
        print("\n🔍 Testing Auth Endpoints (No Auth)...")
        self.run_test("Get /api/auth/me (401 expected)", "GET", "api/auth/me", 401)

    def create_test_user_with_mongodb(self):
        """Create test user directly in MongoDB using the auth_testing.md approach"""
        print("\n🔍 Creating test user with MongoDB...")
        
        import subprocess
        timestamp = str(int(time.time()))
        
        # Create user with company (admin role)
        mongo_script = f'''
        use('test_database');
        var userId = 'test-admin-{timestamp}';
        var companyId = 'comp_{timestamp}';
        var sessionToken = 'test_admin_session_{timestamp}';
        
        db.companies.insertOne({{
          company_id: companyId,
          name: 'Test Company {timestamp}',
          subscription_status: 'trial',
          subscription_plan: null,
          created_at: new Date(),
          updated_at: new Date()
        }});
        
        db.users.insertOne({{
          user_id: userId,
          email: 'admin.{timestamp}@example.com',
          name: 'Test Admin {timestamp}',
          picture: 'https://via.placeholder.com/150',
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
        
        print('SESSION_TOKEN:' + sessionToken);
        print('USER_ID:' + userId);
        print('COMPANY_ID:' + companyId);
        '''
        
        try:
            result = subprocess.run(
                ['mongosh', '--eval', mongo_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.startswith('SESSION_TOKEN:'):
                        self.token = line.split(':')[1]
                    elif line.startswith('USER_ID:'):
                        self.user_id = line.split(':')[1]
                    elif line.startswith('COMPANY_ID:'):
                        self.company_id = line.split(':')[1]
                
                if self.token and self.user_id and self.company_id:
                    self.log_result("Create test user in MongoDB", True)
                    return True
                else:
                    self.log_result("Create test user in MongoDB", False, "Failed to extract credentials from output")
                    return False
            else:
                self.log_result("Create test user in MongoDB", False, f"MongoDB command failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_result("Create test user in MongoDB", False, f"Exception: {str(e)}")
            return False

    def test_auth_endpoints_with_auth(self):
        """Test auth endpoints with valid authentication"""
        print("\n🔍 Testing Auth Endpoints (With Auth)...")
        if not self.token:
            self.log_result("Auth token available for testing", False, "No auth token")
            return
            
        user_data = self.run_test("Get /api/auth/me (200 expected)", "GET", "api/auth/me", 200)
        if user_data:
            if user_data.get('user_id') == self.user_id:
                self.log_result("User data matches created user", True)
            else:
                self.log_result("User data matches created user", False, f"ID mismatch: {user_data.get('user_id')} vs {self.user_id}")

    def test_company_endpoints(self):
        """Test company endpoints"""
        print("\n🔍 Testing Company Endpoints...")
        if not self.token:
            self.log_result("Company endpoints require auth", False, "No auth token")
            return
            
        company_data = self.run_test("Get company info", "GET", "api/companies/me", 200)
        if company_data and company_data.get('company_id') == self.company_id:
            self.log_result("Company data matches created company", True)

    def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        print("\n🔍 Testing Dashboard Endpoints...")
        if not self.token:
            self.log_result("Dashboard endpoints require auth", False, "No auth token")
            return
            
        self.run_test("Get dashboard KPIs", "GET", "api/dashboard/kpis", 200)
        self.run_test("Get revenue trends", "GET", "api/dashboard/revenue-trends", 200)

    def test_properties_crud(self):
        """Test Properties CRUD operations with new fields"""
        print("\n🔍 Testing Properties CRUD with new fields...")
        if not self.token:
            self.log_result("Properties CRUD requires auth", False, "No auth token")
            return
            
        # List properties (should be empty initially)
        properties = self.run_test("List properties", "GET", "api/properties", 200)
        
        # Create property with new fields
        property_data = {
            "name": "Test Villa Property",
            "address": "123 Test St, Test City",
            "property_type": "Villa",
            "rooms": 4,
            "suites": 2,
            "bathrooms": 3,
            "city": "Miami",
            "country": "United States",
            "notes": "Beautiful waterfront villa with amazing views",
            "assigned_cohost": None,  # Will assign later after creating co-host
            "owner_first_name": "John",
            "owner_last_name": "Doe", 
            "owner_phone": "+1234567890",
            "owner_email": "john@example.com",
            "units": 5,
            "active": True
        }
        
        created_property = self.run_test("Create property with new fields", "POST", "api/properties", 201, property_data)
        if created_property:
            property_id = created_property.get('id')
            if property_id:
                # Verify new fields are saved
                if (created_property.get('property_type') == 'Villa' and
                    created_property.get('rooms') == 4 and
                    created_property.get('city') == 'Miami' and
                    created_property.get('notes') == 'Beautiful waterfront villa with amazing views'):
                    self.log_result("Property new fields saved correctly", True)
                else:
                    self.log_result("Property new fields saved correctly", False, f"Field mismatch: {created_property}")
                
                # Update property with new fields
                update_data = {
                    "name": "Updated Test Villa",
                    "property_type": "Resort",
                    "rooms": 6,
                    "suites": 3,
                    "bathrooms": 4,
                    "city": "Orlando",
                    "notes": "Updated: Premium resort with luxury amenities"
                }
                updated_property = self.run_test("Update property new fields", "PUT", f"api/properties/{property_id}", 200, update_data)
                
                if updated_property:
                    if (updated_property.get('property_type') == 'Resort' and
                        updated_property.get('rooms') == 6 and
                        updated_property.get('city') == 'Orlando'):
                        self.log_result("Property new fields updated correctly", True)
                    else:
                        self.log_result("Property new fields updated correctly", False, "Update field mismatch")
                
                # Keep property for co-host assignment test
                self.test_property_id = property_id
                return property_id

    def test_staff_crud(self):
        """Test Staff CRUD operations with new fields"""
        print("\n🔍 Testing Staff CRUD with new fields...")
        if not self.token:
            self.log_result("Staff CRUD requires auth", False, "No auth token")
            return
            
        # List staff
        self.run_test("List staff", "GET", "api/staff", 200)
        
        # Create regular staff with new fields
        staff_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+1987654321",
            "email": "jane@example.com",
            "salary": 3500.00,
            "payment_terms": "Monthly",
            "payment_type": "salary",
            "staff_role": "housekeeper",
            "assigned_properties": []
        }
        
        created_staff = self.run_test("Create housekeeper staff", "POST", "api/staff", 200, staff_data)
        if created_staff:
            staff_id = created_staff.get('id')
            if staff_id:
                # Verify new fields are saved
                if (created_staff.get('payment_type') == 'salary' and
                    created_staff.get('staff_role') == 'housekeeper'):
                    self.log_result("Staff new fields saved correctly", True)
                else:
                    self.log_result("Staff new fields saved correctly", False, f"Field mismatch: {created_staff}")
                
                # Delete regular staff
                self.run_test("Delete housekeeper staff", "DELETE", f"api/staff/{staff_id}", 200)
        
        # Create co-host with per-job rates
        cohost_data = {
            "first_name": "Mike",
            "last_name": "Johnson", 
            "phone": "+1555123456",
            "email": "mike@example.com",
            "salary": 2000.00,
            "payment_terms": "Per Job",
            "payment_type": "per_job",
            "staff_role": "co_host",
            "per_checkin_rate": 50.00,
            "per_checkout_rate": 75.00,
            "assigned_properties": []
        }
        
        created_cohost = self.run_test("Create co-host with rates", "POST", "api/staff", 200, cohost_data)
        if created_cohost:
            cohost_id = created_cohost.get('id')
            if cohost_id:
                # Verify co-host specific fields
                if (created_cohost.get('staff_role') == 'co_host' and
                    created_cohost.get('payment_type') == 'per_job' and
                    created_cohost.get('per_checkin_rate') == 50.00 and
                    created_cohost.get('per_checkout_rate') == 75.00):
                    self.log_result("Co-host rates saved correctly", True)
                else:
                    self.log_result("Co-host rates saved correctly", False, f"Rate mismatch: {created_cohost}")
                
                # Update co-host rates
                update_data = {
                    "per_checkin_rate": 60.00,
                    "per_checkout_rate": 80.00,
                    "payment_type": "commission"
                }
                updated_cohost = self.run_test("Update co-host rates", "PUT", f"api/staff/{cohost_id}", 200, update_data)
                
                if updated_cohost:
                    if (updated_cohost.get('per_checkin_rate') == 60.00 and
                        updated_cohost.get('payment_type') == 'commission'):
                        self.log_result("Co-host fields updated correctly", True)
                    else:
                        self.log_result("Co-host fields updated correctly", False, "Update field mismatch")
                
                # Keep co-host for property assignment and cohosts endpoint test
                self.test_cohost_id = cohost_id
                return cohost_id

    def test_cohosts_endpoint(self):
        """Test GET /api/staff/cohosts endpoint"""
        print("\n🔍 Testing Co-hosts Endpoint...")
        if not self.token:
            self.log_result("Co-hosts endpoint requires auth", False, "No auth token")
            return
            
        cohosts_result = self.run_test("List co-hosts only", "GET", "api/staff/cohosts", 200)
        if cohosts_result is not None:
            # Should only contain staff with staff_role = 'co_host'
            if isinstance(cohosts_result, list):
                cohost_roles = [staff.get('staff_role') for staff in cohosts_result]
                if all(role == 'co_host' for role in cohost_roles):
                    self.log_result("Co-hosts endpoint returns only co-hosts", True)
                else:
                    self.log_result("Co-hosts endpoint returns only co-hosts", False, f"Found non-cohost roles: {cohost_roles}")
                
                # Check if our created co-host is in the list
                if hasattr(self, 'test_cohost_id'):
                    cohost_ids = [staff.get('id') for staff in cohosts_result]
                    if self.test_cohost_id in cohost_ids:
                        self.log_result("Created co-host found in cohosts list", True)
                    else:
                        self.log_result("Created co-host found in cohosts list", False, "Co-host not in list")
            else:
                self.log_result("Co-hosts endpoint returns list", False, f"Expected list, got: {type(cohosts_result)}")

    def test_property_cohost_assignment(self):
        """Test assigning co-host to property"""
        print("\n🔍 Testing Property Co-host Assignment...")
        if not self.token:
            self.log_result("Property assignment requires auth", False, "No auth token")
            return
            
        if not hasattr(self, 'test_property_id') or not hasattr(self, 'test_cohost_id'):
            self.log_result("Property co-host assignment test", False, "Missing test property or co-host")
            return
            
        # Update property to assign co-host
        update_data = {"assigned_cohost": self.test_cohost_id}
        updated_property = self.run_test("Assign co-host to property", "PUT", f"api/properties/{self.test_property_id}", 200, update_data)
        
        if updated_property:
            if updated_property.get('assigned_cohost') == self.test_cohost_id:
                self.log_result("Co-host assigned to property successfully", True)
            else:
                self.log_result("Co-host assigned to property successfully", False, f"Assignment failed: {updated_property.get('assigned_cohost')}")

    def test_expenses_crud(self):
        """Test Expenses CRUD operations"""
        print("\n🔍 Testing Expenses CRUD...")
        if not self.token:
            self.log_result("Expenses CRUD requires auth", False, "No auth token")
            return
            
        # Create a property first for expenses
        property_data = {
            "name": "Expense Test Property",
            "address": "123 Expense St",
            "owner_first_name": "Test",
            "owner_last_name": "Owner",
            "owner_phone": "+1111111111",
            "owner_email": "test@example.com",
            "units": 1,
            "active": True
        }
        
        created_property = self.run_test("Create property for expenses", "POST", "api/properties", 200, property_data)
        if not created_property:
            return
            
        property_id = created_property.get('id')
        
        # List expenses
        self.run_test("List expenses", "GET", "api/expenses", 200)
        
        # Create expense
        expense_data = {
            "property_id": property_id,
            "type": "fixed",
            "category": "Insurance",
            "amount": 500.00,
            "description": "Monthly insurance payment",
            "date": "2024-01-15",
            "recurring": True,
            "recurring_frequency": "monthly"
        }
        
        created_expense = self.run_test("Create expense", "POST", "api/expenses", 200, expense_data)
        if created_expense:
            expense_id = created_expense.get('id')
            if expense_id:
                # Update expense
                update_data = {"amount": 600.00}
                self.run_test("Update expense", "PUT", f"api/expenses/{expense_id}", 200, update_data)
                
                # Delete expense
                self.run_test("Delete expense", "DELETE", f"api/expenses/{expense_id}", 200)
        
        # Cleanup property
        self.run_test("Delete test property", "DELETE", f"api/properties/{property_id}", 200)

    def test_bookings_crud(self):
        """Test Bookings CRUD operations with new fields"""
        print("\n🔍 Testing Bookings CRUD with new fields...")
        if not self.token:
            self.log_result("Bookings CRUD requires auth", False, "No auth token")
            return
            
        # Use existing test property if available, or create new one
        property_id = getattr(self, 'test_property_id', None)
        if not property_id:
            # Create a property for bookings
            property_data = {
                "name": "Booking Test Property",
                "address": "123 Booking St",
                "owner_first_name": "Test",
                "owner_last_name": "Owner",
                "owner_phone": "+1111111111",
                "owner_email": "test@example.com", 
                "units": 1,
                "active": True
            }
            
            created_property = self.run_test("Create property for bookings", "POST", "api/properties", 200, property_data)
            if not created_property:
                return
            property_id = created_property.get('id')
        
        # List bookings
        self.run_test("List bookings", "GET", "api/bookings", 200)
        
        # Create booking with new fields
        cohost_id = getattr(self, 'test_cohost_id', None)
        booking_data = {
            "property_id": property_id,
            "guest_name": "Test Guest Family",
            "check_in": "2024-02-01",
            "check_out": "2024-02-05",
            "total_amount": 1200.00,
            "guests_count": 4,
            "assigned_cohost": cohost_id,
            "status": "confirmed"
        }
        
        created_booking = self.run_test("Create booking with new fields", "POST", "api/bookings", 200, booking_data)
        if created_booking:
            booking_id = created_booking.get('id')
            if booking_id:
                # Verify new fields are saved
                if (created_booking.get('guests_count') == 4 and
                    created_booking.get('assigned_cohost') == cohost_id):
                    self.log_result("Booking new fields saved correctly", True)
                else:
                    self.log_result("Booking new fields saved correctly", False, f"Field mismatch: {created_booking}")
                
                # Update booking with new fields
                update_data = {
                    "status": "checked_in",
                    "guests_count": 6,
                    "total_amount": 1500.00
                }
                updated_booking = self.run_test("Update booking new fields", "PUT", f"api/bookings/{booking_id}", 200, update_data)
                
                if updated_booking:
                    if (updated_booking.get('guests_count') == 6 and
                        updated_booking.get('status') == 'checked_in'):
                        self.log_result("Booking new fields updated correctly", True)
                    else:
                        self.log_result("Booking new fields updated correctly", False, "Update field mismatch")
        
        # Clean up if we created the property here
        if not hasattr(self, 'test_property_id'):
            self.run_test("Delete booking test property", "DELETE", f"api/properties/{property_id}", 200)

    def test_invitations_crud(self):
        """Test Invitations CRUD operations"""
        print("\n🔍 Testing Invitations CRUD...")
        if not self.token:
            self.log_result("Invitations CRUD requires auth", False, "No auth token")
            return
            
        # List invitations
        self.run_test("List invitations", "GET", "api/invitations", 200)
        
        # Create invitation
        invitation_data = {
            "email": "invite@example.com",
            "role": "staff"
        }
        
        created_invitation = self.run_test("Create invitation", "POST", "api/invitations", 200, invitation_data)
        if created_invitation:
            invitation_id = created_invitation.get('id')
            token = created_invitation.get('token')
            
            if token:
                # Validate invitation
                self.run_test("Validate invitation token", "GET", f"api/invitations/validate/{token}", 200)
            
            if invitation_id:
                # Delete invitation
                self.run_test("Delete invitation", "DELETE", f"api/invitations/{invitation_id}", 200)

    def test_seed_demo_data(self):
        """Test seed demo data endpoint"""
        print("\n🔍 Testing Seed Demo Data...")
        if not self.token:
            self.log_result("Seed demo data requires auth", False, "No auth token")
            return
            
        self.run_test("Seed demo data", "POST", "api/seed-demo-data", 200)

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🔍 Cleaning up test data...")
        
        # Clean up in reverse order of creation
        if hasattr(self, 'test_property_id'):
            self.run_test("Delete test property", "DELETE", f"api/properties/{self.test_property_id}", 200)
        
        if hasattr(self, 'test_cohost_id'):
            self.run_test("Delete test co-host", "DELETE", f"api/staff/{self.test_cohost_id}", 200)

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Property Management API Tests...")
        print(f"Backend URL: {self.base_url}")
        
        # Public endpoints
        self.test_subscription_plans()
        self.test_auth_endpoints_without_auth()
        
        # Create test user
        if self.create_test_user_with_mongodb():
            # Auth-protected endpoints
            self.test_auth_endpoints_with_auth()
            self.test_company_endpoints()
            self.test_dashboard_endpoints()
            
            # CRUD operations with new fields
            self.test_properties_crud()
            self.test_staff_crud()
            self.test_cohosts_endpoint()
            self.test_property_cohost_assignment()
            self.test_expenses_crud()
            self.test_bookings_crud()
            self.test_invitations_crud()
            
            # Seed data
            self.test_seed_demo_data()
            
            # Clean up test data
            self.cleanup_test_data()
        else:
            print("❌ Skipping authenticated tests due to user creation failure")
        
        # Print summary
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed!")
            return 1

def main():
    tester = PropertyManagementAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())