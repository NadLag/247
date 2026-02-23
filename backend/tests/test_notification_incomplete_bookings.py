"""
Test suite for Missing Booking Details Notification feature:
- Notification API endpoints
- Incomplete bookings filter
- is_data_complete auto-recalculation
- Auto-resolve notifications when all bookings are complete
"""

import pytest
import requests
import os
import time
import subprocess

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://booking-hub-174.preview.emergentagent.com"


# Store test data globally for access across tests
TEST_DATA = {}


def setup_module(module):
    """Create test user, company, and property for the test session"""
    ts = str(int(time.time() * 1000))
    
    session_token = f"test_pytest_notif_{ts}"
    company_id = f"comp_pytest_{ts}"
    property_id = f"prop_pytest_{ts}"
    user_id = f"user_pytest_{ts}"
    
    # Create test data in MongoDB
    mongo_script = f"""
    use('test_database');
    
    db.companies.insertOne({{
      company_id: "{company_id}",
      name: "Pytest Notification Company",
      subscription_status: "trial",
      subscription_plan: null,
      created_at: new Date(),
      updated_at: new Date()
    }});
    
    db.users.insertOne({{
      user_id: "{user_id}",
      email: "pytest.notif.{ts}@example.com",
      name: "Pytest User",
      picture: "",
      company_id: "{company_id}",
      role: "company_admin",
      created_at: new Date(),
      updated_at: new Date()
    }});
    
    db.user_sessions.insertOne({{
      user_id: "{user_id}",
      session_token: "{session_token}",
      expires_at: new Date(Date.now() + 7*24*60*60*1000),
      created_at: new Date()
    }});
    
    db.properties.insertOne({{
      id: "{property_id}",
      company_id: "{company_id}",
      name: "Pytest Test Property",
      address: "123 Test St",
      property_type: "vacation_home",
      rooms: 3, suites: 1, bathrooms: 2,
      city: "Test City", country: "USA",
      notes: "", assigned_cohost: null,
      owner_first_name: "Owner",
      owner_last_name: "Test",
      owner_phone: "555-1234",
      owner_email: "owner@test.com",
      units: 1, active: true,
      created_at: new Date(),
      updated_at: new Date()
    }});
    
    print("SETUP COMPLETE");
    """
    
    result = subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True, text=True)
    
    TEST_DATA['session_token'] = session_token
    TEST_DATA['company_id'] = company_id
    TEST_DATA['property_id'] = property_id
    TEST_DATA['user_id'] = user_id
    TEST_DATA['ts'] = ts
    
    print(f"Test setup complete: company_id={company_id}")


def teardown_module(module):
    """Cleanup test data"""
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{user_id: /^user_pytest_/}});
    db.user_sessions.deleteMany({{session_token: /^test_pytest_notif_/}});
    db.companies.deleteMany({{company_id: /^comp_pytest_/}});
    db.properties.deleteMany({{id: /^prop_pytest_/}});
    db.bookings.deleteMany({{company_id: /^comp_pytest_/}});
    db.notifications.deleteMany({{company_id: /^comp_pytest_/}});
    print("CLEANUP COMPLETE");
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)


class TestNotificationEndpoints:
    """Test notification API endpoints"""
    
    def test_01_notifications_empty_initially(self):
        """GET /api/notifications returns empty list for new company"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/notifications returns {len(data)} notifications initially")
    
    def test_02_unread_count_zero_initially(self):
        """GET /api/notifications/unread-count returns 0 for new company"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == 0
        print(f"✓ Unread count is 0 initially")


class TestIncompleteBookingsFilter:
    """Test incomplete bookings filter"""
    
    def test_03_create_incomplete_booking(self):
        """Create an incomplete booking (missing guest_name and amount)"""
        ts = TEST_DATA['ts']
        booking_id = f"book_pytest_incomplete_{ts}"
        
        mongo_script = f"""
        use('test_database');
        db.bookings.insertOne({{
          id: "{booking_id}",
          company_id: "{TEST_DATA['company_id']}",
          property_id: "{TEST_DATA['property_id']}",
          guest_name: "",
          check_in: "2026-04-01",
          check_out: "2026-04-05",
          total_amount: 0,
          guests_count: 1,
          status: "confirmed",
          booking_type: "reservation",
          ota_source: "airbnb",
          is_data_complete: false,
          created_at: new Date(),
          updated_at: new Date()
        }});
        print("CREATED");
        """
        
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        TEST_DATA['incomplete_booking_id'] = booking_id
        print(f"✓ Created incomplete booking: {booking_id}")
    
    def test_04_incomplete_only_filter(self):
        """GET /api/bookings?incomplete_only=true returns only incomplete bookings"""
        response = requests.get(
            f"{BASE_URL}/api/bookings?incomplete_only=true",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verify all returned bookings have is_data_complete=false
        for booking in data:
            assert booking.get('is_data_complete') == False
        
        print(f"✓ GET /api/bookings?incomplete_only=true returns {len(data)} incomplete bookings")


class TestNotificationCreationAndUpdate:
    """Test notification creation and updates on booking changes"""
    
    def test_05_trigger_notification_creation(self):
        """Updating an incomplete booking triggers notification creation/update"""
        booking_id = TEST_DATA.get('incomplete_booking_id')
        assert booking_id, "No incomplete booking created"
        
        # Update booking to trigger notification check
        response = requests.put(
            f"{BASE_URL}/api/bookings/{booking_id}",
            headers={
                "Authorization": f"Bearer {TEST_DATA['session_token']}",
                "Content-Type": "application/json"
            },
            json={"guest_name": ""}  # Keep it incomplete
        )
        assert response.status_code == 200
        
        # Check notifications
        notif_response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert notif_response.status_code == 200
        notifications = notif_response.json()
        
        # Find incomplete_bookings notification
        incomplete_notif = next(
            (n for n in notifications if n.get('type') == 'incomplete_bookings'),
            None
        )
        
        assert incomplete_notif is not None, "Incomplete bookings notification should be created"
        assert incomplete_notif.get('title') == "Missing Booking Details"
        assert incomplete_notif.get('action_url') == "/bookings?filter=incomplete"
        assert incomplete_notif.get('read') == False
        assert incomplete_notif.get('count') >= 1
        
        TEST_DATA['notification_id'] = incomplete_notif['id']
        print(f"✓ Notification created: {incomplete_notif['title']} with count={incomplete_notif['count']}")
    
    def test_06_unread_count_updated(self):
        """Unread count increases when notification is created"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        print(f"✓ Unread count is {data['count']}")


class TestMarkNotificationRead:
    """Test marking notifications as read"""
    
    def test_07_mark_single_read(self):
        """PUT /api/notifications/{id}/read marks notification as read"""
        notif_id = TEST_DATA.get('notification_id')
        assert notif_id, "No notification ID available"
        
        response = requests.put(
            f"{BASE_URL}/api/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Notification marked as read"
        
        # Verify notification is marked as read
        notif_response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        notifications = notif_response.json()
        notif = next((n for n in notifications if n['id'] == notif_id), None)
        assert notif is not None
        assert notif.get('read') == True
        
        print(f"✓ Notification {notif_id} marked as read")
    
    def test_08_mark_all_read(self):
        """PUT /api/notifications/read-all marks all notifications as read"""
        # First, make notification unread again by triggering an update
        booking_id = TEST_DATA.get('incomplete_booking_id')
        if booking_id:
            requests.put(
                f"{BASE_URL}/api/bookings/{booking_id}",
                headers={
                    "Authorization": f"Bearer {TEST_DATA['session_token']}",
                    "Content-Type": "application/json"
                },
                json={"guest_name": ""}  # Keep incomplete, triggers notification update
            )
        
        # Mark all as read
        response = requests.put(
            f"{BASE_URL}/api/notifications/read-all",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "All notifications marked as read"
        
        # Verify unread count is 0
        count_response = requests.get(
            f"{BASE_URL}/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert count_response.json()["count"] == 0
        
        print("✓ All notifications marked as read")


class TestBookingCompletionAndAutoResolve:
    """Test is_data_complete recalculation and notification auto-resolve"""
    
    def test_09_complete_booking_updates_is_data_complete(self):
        """Updating booking with guest_name and total_amount sets is_data_complete=true"""
        booking_id = TEST_DATA.get('incomplete_booking_id')
        assert booking_id, "No incomplete booking available"
        
        response = requests.put(
            f"{BASE_URL}/api/bookings/{booking_id}",
            headers={
                "Authorization": f"Bearer {TEST_DATA['session_token']}",
                "Content-Type": "application/json"
            },
            json={"guest_name": "Test Guest", "total_amount": 500}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('guest_name') == "Test Guest"
        assert data.get('total_amount') == 500
        assert data.get('is_data_complete') == True
        
        print(f"✓ Booking {booking_id} is now complete (is_data_complete=true)")
    
    def test_10_incomplete_bookings_empty_after_completion(self):
        """GET /api/bookings?incomplete_only=true returns empty after all bookings complete"""
        response = requests.get(
            f"{BASE_URL}/api/bookings?incomplete_only=true",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Filter to only our company's bookings
        company_incomplete = [
            b for b in data 
            if b.get('company_id') == TEST_DATA['company_id']
        ]
        
        assert len(company_incomplete) == 0, "All company bookings should be complete now"
        print("✓ No incomplete bookings remain for company")
    
    def test_11_notification_auto_resolved(self):
        """Notification is auto-resolved when all bookings are complete"""
        notif_id = TEST_DATA.get('notification_id')
        assert notif_id, "No notification ID available"
        
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        notifications = response.json()
        
        notif = next((n for n in notifications if n['id'] == notif_id), None)
        assert notif is not None
        assert notif.get('resolved') == True, "Notification should be auto-resolved"
        assert notif.get('read') == True, "Resolved notification should be marked as read"
        
        print(f"✓ Notification {notif_id} auto-resolved")


class TestNotificationNotFound:
    """Test error cases for notifications"""
    
    def test_12_mark_nonexistent_notification(self):
        """PUT /api/notifications/{invalid_id}/read returns 404"""
        response = requests.put(
            f"{BASE_URL}/api/notifications/notif_nonexistent123/read",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 404
        print("✓ Marking nonexistent notification returns 404")


class TestBookingIsDataCompleteLogic:
    """Test is_data_complete calculation logic"""
    
    def test_13_booking_incomplete_without_guest_name(self):
        """Booking without guest_name is incomplete"""
        ts = str(int(time.time() * 1000))
        booking_id = f"book_pytest_noguestname_{ts}"
        
        mongo_script = f"""
        use('test_database');
        db.bookings.insertOne({{
          id: "{booking_id}",
          company_id: "{TEST_DATA['company_id']}",
          property_id: "{TEST_DATA['property_id']}",
          guest_name: "",
          check_in: "2026-05-01",
          check_out: "2026-05-05",
          total_amount: 500,
          guests_count: 1,
          status: "confirmed",
          booking_type: "reservation",
          ota_source: "vrbo",
          is_data_complete: false,
          created_at: new Date(),
          updated_at: new Date()
        }});
        print("CREATED");
        """
        
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        # Check incomplete filter
        response = requests.get(
            f"{BASE_URL}/api/bookings?incomplete_only=true",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        no_guest = [b for b in data if b.get('id') == booking_id]
        assert len(no_guest) >= 1
        
        print("✓ Booking without guest_name is considered incomplete")
        
        # Cleanup
        subprocess.run(
            ['mongosh', '--quiet', '--eval', f'use("test_database"); db.bookings.deleteOne({{id: "{booking_id}"}});'],
            capture_output=True
        )
    
    def test_14_booking_incomplete_without_amount(self):
        """Booking without total_amount is incomplete"""
        ts = str(int(time.time() * 1000))
        booking_id = f"book_pytest_noamount_{ts}"
        
        mongo_script = f"""
        use('test_database');
        db.bookings.insertOne({{
          id: "{booking_id}",
          company_id: "{TEST_DATA['company_id']}",
          property_id: "{TEST_DATA['property_id']}",
          guest_name: "Has Name",
          check_in: "2026-06-01",
          check_out: "2026-06-05",
          total_amount: 0,
          guests_count: 1,
          status: "confirmed",
          booking_type: "reservation",
          ota_source: "expedia",
          is_data_complete: false,
          created_at: new Date(),
          updated_at: new Date()
        }});
        print("CREATED");
        """
        
        subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
        
        response = requests.get(
            f"{BASE_URL}/api/bookings?incomplete_only=true",
            headers={"Authorization": f"Bearer {TEST_DATA['session_token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        no_amount = [b for b in data if b.get('id') == booking_id]
        assert len(no_amount) >= 1
        
        print("✓ Booking without total_amount is considered incomplete")
        
        # Cleanup
        subprocess.run(
            ['mongosh', '--quiet', '--eval', f'use("test_database"); db.bookings.deleteOne({{id: "{booking_id}"}});'],
            capture_output=True
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
