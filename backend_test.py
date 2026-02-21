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
        """Test Properties CRUD operations"""
        print("\n🔍 Testing Properties CRUD...")
        if not self.token:
            self.log_result("Properties CRUD requires auth", False, "No auth token")
            return
            
        # List properties (should be empty initially)
        properties = self.run_test("List properties", "GET", "api/properties", 200)
        
        # Create property
        property_data = {
            "name": "Test Property",
            "address": "123 Test St, Test City",
            "owner_first_name": "John",
            "owner_last_name": "Doe",
            "owner_phone": "+1234567890",
            "owner_email": "john@example.com",
            "units": 5,
            "active": True
        }
        
        created_property = self.run_test("Create property", "POST", "api/properties", 200, property_data)
        if created_property:
            property_id = created_property.get('id')
            if property_id:
                # Update property
                update_data = {"name": "Updated Test Property", "units": 10}
                self.run_test("Update property", "PUT", f"api/properties/{property_id}", 200, update_data)
                
                # Delete property
                self.run_test("Delete property", "DELETE", f"api/properties/{property_id}", 200)

    def test_staff_crud(self):
        """Test Staff CRUD operations"""
        print("\n🔍 Testing Staff CRUD...")
        if not self.token:
            self.log_result("Staff CRUD requires auth", False, "No auth token")
            return
            
        # List staff
        self.run_test("List staff", "GET", "api/staff", 200)
        
        # Create staff
        staff_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+1987654321",
            "email": "jane@example.com",
            "salary": 3500.00,
            "payment_terms": "Monthly",
            "assigned_properties": []
        }
        
        created_staff = self.run_test("Create staff", "POST", "api/staff", 201, staff_data)
        if created_staff:
            staff_id = created_staff.get('id')
            if staff_id:
                # Update staff
                update_data = {"salary": 4000.00}
                self.run_test("Update staff", "PUT", f"api/staff/{staff_id}", 200, update_data)
                
                # Delete staff
                self.run_test("Delete staff", "DELETE", f"api/staff/{staff_id}", 200)

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
        
        created_property = self.run_test("Create property for expenses", "POST", "api/properties", 201, property_data)
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
        
        created_expense = self.run_test("Create expense", "POST", "api/expenses", 201, expense_data)
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
        """Test Bookings CRUD operations"""
        print("\n🔍 Testing Bookings CRUD...")
        if not self.token:
            self.log_result("Bookings CRUD requires auth", False, "No auth token")
            return
            
        # Create a property first for bookings
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
        
        created_property = self.run_test("Create property for bookings", "POST", "api/properties", 201, property_data)
        if not created_property:
            return
            
        property_id = created_property.get('id')
        
        # List bookings
        self.run_test("List bookings", "GET", "api/bookings", 200)
        
        # Create booking
        booking_data = {
            "property_id": property_id,
            "guest_name": "Test Guest",
            "check_in": "2024-02-01",
            "check_out": "2024-02-05",
            "total_amount": 800.00,
            "status": "confirmed"
        }
        
        created_booking = self.run_test("Create booking", "POST", "api/bookings", 201, booking_data)
        if created_booking:
            booking_id = created_booking.get('id')
            if booking_id:
                # Update booking
                update_data = {"status": "checked_in"}
                self.run_test("Update booking", "PUT", f"api/bookings/{booking_id}", 200, update_data)
        
        # Cleanup property (bookings will be cleaned up automatically due to foreign key constraints or similar)
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
        
        created_invitation = self.run_test("Create invitation", "POST", "api/invitations", 201, invitation_data)
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
            
            # CRUD operations
            self.test_properties_crud()
            self.test_staff_crud() 
            self.test_expenses_crud()
            self.test_bookings_crud()
            self.test_invitations_crud()
            
            # Seed data
            self.test_seed_demo_data()
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