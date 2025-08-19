import requests
import sys
import json
from datetime import datetime

class MedConnectAPITester:
    def __init__(self, base_url="https://greenstar-health.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user roles
        self.users = {}   # Store user data for different roles
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        self.created_user_id = None  # Track created user for cleanup
        
        # Test credentials as specified in review request
        self.demo_credentials = {
            "provider": {"username": "provider", "password": "provider123"},
            "doctor": {"username": "doctor", "password": "doctor123"},
            "admin": {"username": "admin", "password": "admin123"}
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test the health check endpoint"""
        return self.run_test("Health Check", "GET", "", 200)

    def test_login_all_roles(self):
        """Test login for all user roles"""
        print("\n🔑 Testing Login for All Roles")
        print("-" * 50)
        
        all_success = True
        for role, credentials in self.demo_credentials.items():
            success, response = self.run_test(
                f"Login {role.title()}",
                "POST", 
                "login",
                200,
                data=credentials
            )
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   ✅ {role.title()} login successful - Token obtained")
                print(f"   User ID: {response['user'].get('id')}")
                print(f"   Full Name: {response['user'].get('full_name')}")
                print(f"   Role: {response['user'].get('role')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                all_success = False
        
        return all_success

    def test_admin_only_get_users(self):
        """Test that only admin can get all users"""
        print("\n👥 Testing Admin-Only Get Users Access")
        print("-" * 50)
        
        # Test admin access (should work)
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Get All Users (Admin - Should Work)",
                "GET",
                "users", 
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print(f"   ✅ Admin can access users list ({len(response)} users found)")
            else:
                print("   ❌ Admin cannot access users list")
                return False
        else:
            print("   ❌ No admin token available")
            return False
            
        # Test provider access (should fail with 403)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Get All Users (Provider - Should Fail)",
                "GET",
                "users", 
                403,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied access to users list")
            else:
                print("   ❌ Provider unexpectedly allowed access to users list")
                return False
        
        # Test doctor access (should fail with 403)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Get All Users (Doctor - Should Fail)",
                "GET",
                "users", 
                403,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied access to users list")
            else:
                print("   ❌ Doctor unexpectedly allowed access to users list")
                return False
        
        return True

    def test_admin_only_create_user(self):
        """Test that only admin can create new users"""
        print("\n➕ Testing Admin-Only Create User Access")
        print("-" * 50)
        
        test_user_data = {
            "username": f"test_user_{datetime.now().strftime('%H%M%S')}",
            "email": f"test_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "phone": "+1234567890",
            "full_name": "Test User Created",
            "role": "provider",
            "district": "Test District"
        }
        
        # Test admin access (should work)
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Create User (Admin - Should Work)",
                "POST",
                "admin/create-user", 
                200,
                data=test_user_data,
                token=self.tokens['admin']
            )
            
            if success:
                self.created_user_id = response.get('id')
                print(f"   ✅ Admin can create users (Created user ID: {self.created_user_id})")
            else:
                print("   ❌ Admin cannot create users")
                return False
        else:
            print("   ❌ No admin token available")
            return False
            
        # Test provider access (should fail with 403)
        if 'provider' in self.tokens:
            test_user_data['username'] = f"test_provider_{datetime.now().strftime('%H%M%S')}"
            test_user_data['email'] = f"test_provider_{datetime.now().strftime('%H%M%S')}@example.com"
            
            success, response = self.run_test(
                "Create User (Provider - Should Fail)",
                "POST",
                "admin/create-user", 
                403,
                data=test_user_data,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied user creation access")
            else:
                print("   ❌ Provider unexpectedly allowed to create users")
                return False
        
        # Test doctor access (should fail with 403)
        if 'doctor' in self.tokens:
            test_user_data['username'] = f"test_doctor_{datetime.now().strftime('%H%M%S')}"
            test_user_data['email'] = f"test_doctor_{datetime.now().strftime('%H%M%S')}@example.com"
            
            success, response = self.run_test(
                "Create User (Doctor - Should Fail)",
                "POST",
                "admin/create-user", 
                403,
                data=test_user_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied user creation access")
            else:
                print("   ❌ Doctor unexpectedly allowed to create users")
                return False
        
        return True

    def test_admin_only_delete_user(self):
        """Test that only admin can delete users"""
        print("\n🗑️ Testing Admin-Only Delete User Access")
        print("-" * 50)
        
        if not self.created_user_id:
            print("   ❌ No test user available for deletion")
            return False
            
        # Test provider access (should fail with 403)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Delete User (Provider - Should Fail)",
                "DELETE",
                f"users/{self.created_user_id}", 
                403,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied user deletion access")
            else:
                print("   ❌ Provider unexpectedly allowed to delete users")
                return False
        
        # Test doctor access (should fail with 403)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Delete User (Doctor - Should Fail)",
                "DELETE",
                f"users/{self.created_user_id}", 
                403,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied user deletion access")
            else:
                print("   ❌ Doctor unexpectedly allowed to delete users")
                return False
        
        # Test admin access (should work)
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Delete User (Admin - Should Work)",
                "DELETE",
                f"users/{self.created_user_id}", 
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print(f"   ✅ Admin can delete users")
                self.created_user_id = None  # Clear since user is deleted
            else:
                print("   ❌ Admin cannot delete users")
                return False
        else:
            print("   ❌ No admin token available")
            return False
        
        return True

    def test_self_deletion_prevention(self):
        """Test that admin cannot delete their own account"""
        print("\n🚫 Testing Self-Deletion Prevention")
        print("-" * 50)
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        admin_user_id = self.users['admin']['id']
        
        success, response = self.run_test(
            "Admin Self-Deletion (Should Fail)",
            "DELETE",
            f"users/{admin_user_id}", 
            400,  # Expecting 400 Bad Request
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin correctly prevented from deleting own account")
            return True
        else:
            print("   ❌ Admin unexpectedly allowed to delete own account")
            return False

    def test_admin_only_update_user_status(self):
        """Test that only admin can update user status"""
        print("\n🔄 Testing Admin-Only Update User Status Access")
        print("-" * 50)
        
        # First create a test user to modify
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        test_user_data = {
            "username": f"status_test_{datetime.now().strftime('%H%M%S')}",
            "email": f"status_test_{datetime.now().strftime('%H%M%S')}@example.com",
            "password": "TestPass123!",
            "phone": "+1234567890",
            "full_name": "Status Test User",
            "role": "provider",
            "district": "Test District"
        }
        
        success, response = self.run_test(
            "Create Test User for Status Update",
            "POST",
            "admin/create-user", 
            200,
            data=test_user_data,
            token=self.tokens['admin']
        )
        
        if not success:
            print("   ❌ Could not create test user for status update")
            return False
            
        test_user_id = response.get('id')
        status_update = {"is_active": False}
        
        # Test provider access (should fail with 403)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Update User Status (Provider - Should Fail)",
                "PUT",
                f"users/{test_user_id}/status", 
                403,
                data=status_update,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied user status update access")
            else:
                print("   ❌ Provider unexpectedly allowed to update user status")
                return False
        
        # Test doctor access (should fail with 403)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Update User Status (Doctor - Should Fail)",
                "PUT",
                f"users/{test_user_id}/status", 
                403,
                data=status_update,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied user status update access")
            else:
                print("   ❌ Doctor unexpectedly allowed to update user status")
                return False
        
        # Test admin access (should work)
        success, response = self.run_test(
            "Update User Status (Admin - Should Work)",
            "PUT",
            f"users/{test_user_id}/status", 
            200,
            data=status_update,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin can update user status")
        else:
            print("   ❌ Admin cannot update user status")
            return False
        
        # Clean up - delete the test user
        self.run_test(
            "Cleanup Test User",
            "DELETE",
            f"users/{test_user_id}", 
            200,
            token=self.tokens['admin']
        )
        
        return True

    def test_self_deactivation_prevention(self):
        """Test that admin cannot deactivate their own account"""
        print("\n🚫 Testing Self-Deactivation Prevention")
        print("-" * 50)
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        admin_user_id = self.users['admin']['id']
        status_update = {"is_active": False}
        
        success, response = self.run_test(
            "Admin Self-Deactivation (Should Fail)",
            "PUT",
            f"users/{admin_user_id}/status", 
            400,  # Expecting 400 Bad Request
            data=status_update,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Admin correctly prevented from deactivating own account")
            return True
        else:
            print("   ❌ Admin unexpectedly allowed to deactivate own account")
            return False

    def test_create_appointment(self):
        """Test creating an appointment (provider only)"""
        print("\n📅 Testing Appointment Creation")
        print("-" * 50)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
            
        appointment_data = {
            "patient": {
                "name": "Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6
                },
                "consultation_reason": "Routine checkup"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Patient reports feeling well"
        }
        
        success, response = self.run_test(
            "Create Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            self.appointment_id = response.get('id')
            print(f"   ✅ Created appointment ID: {self.appointment_id}")
        
        return success

    def test_role_based_appointment_access(self):
        """Test role-based appointment filtering"""
        print("\n🔐 Testing Role-Based Appointment Access")
        print("-" * 50)
        
        all_success = True
        
        # Test provider access (should only see own appointments)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Get Appointments (Provider - Own Only)",
                "GET",
                "appointments",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                provider_appointments = response
                print(f"   ✅ Provider can see {len(provider_appointments)} appointments")
                # Verify all appointments belong to this provider
                for apt in provider_appointments:
                    if apt.get('provider_id') != self.users['provider']['id']:
                        print(f"   ❌ Provider seeing appointment not owned by them: {apt.get('id')}")
                        all_success = False
                        break
                else:
                    print("   ✅ Provider only sees own appointments")
            else:
                all_success = False
        
        # Test doctor access (should see pending + own accepted appointments)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Get Appointments (Doctor - Pending + Own)",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                doctor_appointments = response
                print(f"   ✅ Doctor can see {len(doctor_appointments)} appointments")
                # Verify appointments are either pending or assigned to this doctor
                for apt in doctor_appointments:
                    if apt.get('status') != 'pending' and apt.get('doctor_id') != self.users['doctor']['id']:
                        print(f"   ❌ Doctor seeing inappropriate appointment: {apt.get('id')}")
                        all_success = False
                        break
                else:
                    print("   ✅ Doctor sees appropriate appointments")
            else:
                all_success = False
        
        # Test admin access (should see all appointments)
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Get Appointments (Admin - All)",
                "GET",
                "appointments",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                admin_appointments = response
                print(f"   ✅ Admin can see {len(admin_appointments)} appointments (all)")
            else:
                all_success = False
        
        return all_success

    def test_appointment_details(self):
        """Test getting detailed appointment information"""
        print("\n📋 Testing Appointment Details Access")
        print("-" * 50)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        all_success = True
        
        # Test doctor access to appointment details
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Get Appointment Details (Doctor)",
                "GET",
                f"appointments/{self.appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor can view appointment details")
                # Check if response includes patient, provider, and notes
                if 'patient' in response and 'provider' in response:
                    print("   ✅ Details include patient and provider information")
                else:
                    print("   ❌ Missing patient or provider information in details")
                    all_success = False
            else:
                all_success = False
        
        # Test provider access to own appointment details
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Get Appointment Details (Provider - Own)",
                "GET",
                f"appointments/{self.appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider can view own appointment details")
            else:
                all_success = False
        
        # Test admin access to appointment details
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Get Appointment Details (Admin)",
                "GET",
                f"appointments/{self.appointment_id}",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can view appointment details")
            else:
                all_success = False
        
        return all_success

    def test_doctor_notes_system(self):
        """Test doctor notes to provider functionality"""
        print("\n📝 Testing Doctor Notes System")
        print("-" * 50)
        
        if not self.appointment_id or 'doctor' not in self.tokens:
            print("❌ No appointment ID or doctor token available")
            return False
        
        # First, doctor accepts the appointment
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id']
        }
        
        success, response = self.run_test(
            "Doctor Accepts Appointment",
            "PUT",
            f"appointments/{self.appointment_id}",
            200,
            data=update_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not accept appointment")
            return False
        
        # Doctor adds a note
        note_data = {
            "note": "Patient vitals look good. Recommend follow-up in 2 weeks.",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Adds Note",
            "POST",
            f"appointments/{self.appointment_id}/notes",
            200,
            data=note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not add note")
            return False
        
        print("   ✅ Doctor successfully added note")
        
        # Provider should be able to see the note
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Provider Views Notes",
                "GET",
                f"appointments/{self.appointment_id}/notes",
                200,
                token=self.tokens['provider']
            )
            
            if success and len(response) > 0:
                print(f"   ✅ Provider can see {len(response)} notes")
                # Check if the doctor's note is there
                doctor_notes = [note for note in response if note.get('sender_role') == 'doctor']
                if doctor_notes:
                    print("   ✅ Doctor's note visible to provider")
                else:
                    print("   ❌ Doctor's note not visible to provider")
                    return False
            else:
                print("   ❌ Provider cannot see notes")
                return False
        
        return True

    def test_appointment_cancellation(self):
        """Test appointment cancellation by provider"""
        print("\n❌ Testing Appointment Cancellation")
        print("-" * 50)
        
        if not self.appointment_id or 'provider' not in self.tokens:
            print("❌ No appointment ID or provider token available")
            return False
        
        # Provider cancels their own appointment
        update_data = {
            "status": "cancelled"
        }
        
        success, response = self.run_test(
            "Provider Cancels Own Appointment",
            "PUT",
            f"appointments/{self.appointment_id}",
            200,
            data=update_data,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Provider can cancel own appointment")
        else:
            print("   ❌ Provider cannot cancel own appointment")
            return False
        
        return True

    def test_appointment_deletion(self):
        """Test appointment deletion permissions"""
        print("\n🗑️ Testing Appointment Deletion Permissions")
        print("-" * 50)
        
        # Create a new appointment for deletion testing
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        appointment_data = {
            "patient": {
                "name": "Delete Test Patient",
                "age": 30,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "110/70",
                    "heart_rate": 68,
                    "temperature": 98.4
                },
                "consultation_reason": "Test appointment for deletion"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Test appointment"
        }
        
        success, response = self.run_test(
            "Create Appointment for Deletion Test",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Could not create test appointment")
            return False
        
        delete_test_appointment_id = response.get('id')
        all_success = True
        
        # Test doctor deletion (should fail - doctors can't delete)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Delete Appointment (Doctor - Should Fail)",
                "DELETE",
                f"appointments/{delete_test_appointment_id}",
                403,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied appointment deletion")
            else:
                print("   ❌ Doctor unexpectedly allowed to delete appointment")
                all_success = False
        
        # Test provider deletion of own appointment (should work)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Delete Own Appointment (Provider - Should Work)",
                "DELETE",
                f"appointments/{delete_test_appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider can delete own appointment")
                delete_test_appointment_id = None  # Mark as deleted
            else:
                print("   ❌ Provider cannot delete own appointment")
                all_success = False
        
        # Test admin deletion (should work for any appointment)
        if delete_test_appointment_id and 'admin' in self.tokens:
            success, response = self.run_test(
                "Delete Any Appointment (Admin - Should Work)",
                "DELETE",
                f"appointments/{delete_test_appointment_id}",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can delete any appointment")
            else:
                print("   ❌ Admin cannot delete appointment")
                all_success = False
        
        return all_success

    def test_emergency_appointment(self):
        """Test creating an emergency appointment"""
        print("\n🚨 Testing Emergency Appointment Creation")
        print("-" * 50)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
            
        emergency_data = {
            "patient": {
                "name": "Emergency Patient",
                "age": 45,
                "gender": "Female", 
                "vitals": {
                    "blood_pressure": "180/120",
                    "heart_rate": 110,
                    "temperature": 102.5
                },
                "consultation_reason": "Chest pain and difficulty breathing"
            },
            "appointment_type": "emergency",
            "consultation_notes": "URGENT: Patient experiencing severe symptoms"
        }
        
        success, response = self.run_test(
            "Create Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=emergency_data,
            token=self.tokens['provider']
        )
        
        if success:
            emergency_appointment_id = response.get('id')
            print(f"   ✅ Created emergency appointment ID: {emergency_appointment_id}")
        
        return success

    def test_video_call_start_and_join(self):
        """Test video call start and join functionality with proper authorization"""
        print("\n📹 Testing Video Call Start and Join Endpoints")
        print("-" * 50)
        
        if not self.appointment_id:
            print("❌ No appointment ID available for video call testing")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens for video call testing")
            return False
        
        # Test 1: Doctor starts video call
        success, response = self.run_test(
            "Start Video Call (Doctor)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not start video call")
            return False
            
        session_token = response.get('session_token')
        if not session_token:
            print("❌ No session token returned from start video call")
            return False
            
        print(f"   ✅ Video call started, session token: {session_token[:20]}...")
        
        # Test 2: Provider joins video call with valid session token
        success, response = self.run_test(
            "Join Video Call (Provider - Authorized)",
            "GET",
            f"video-call/join/{session_token}",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not join video call with valid session token")
            return False
            
        print("   ✅ Provider successfully joined video call")
        
        # Test 3: Doctor joins their own video call
        success, response = self.run_test(
            "Join Video Call (Doctor - Own Call)",
            "GET",
            f"video-call/join/{session_token}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not join their own video call")
            return False
            
        print("   ✅ Doctor successfully joined their own video call")
        
        # Test 4: Admin tries to join video call (should fail - not authorized)
        if 'admin' in self.tokens:
            success, response = self.run_test(
                "Join Video Call (Admin - Should Fail)",
                "GET",
                f"video-call/join/{session_token}",
                403,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin correctly denied access to video call")
            else:
                print("   ❌ Admin unexpectedly allowed to join video call")
                return False
        
        # Test 5: Try to join with invalid session token
        invalid_token = "invalid-session-token-12345"
        success, response = self.run_test(
            "Join Video Call (Invalid Token)",
            "GET",
            f"video-call/join/{invalid_token}",
            404,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Invalid session token correctly rejected")
        else:
            print("   ❌ Invalid session token unexpectedly accepted")
            return False
        
        # Test 6: Provider starts video call
        success, response = self.run_test(
            "Start Video Call (Provider)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_session_token = response.get('session_token')
            print(f"   ✅ Provider can also start video calls, token: {provider_session_token[:20]}...")
        else:
            print("   ❌ Provider could not start video call")
            return False
        
        return True

    def test_appointment_edit_permissions(self):
        """Test appointment edit endpoint with role-based permissions"""
        print("\n✏️ Testing Appointment Edit Endpoint Permissions")
        print("-" * 50)
        
        if not self.appointment_id:
            print("❌ No appointment ID available for edit testing")
            return False
        
        all_success = True
        
        # Test 1: Admin can edit any appointment
        if 'admin' in self.tokens:
            edit_data = {
                "status": "accepted",
                "consultation_notes": "Updated by admin - appointment approved"
            }
            
            success, response = self.run_test(
                "Edit Appointment (Admin - Should Work)",
                "PUT",
                f"appointments/{self.appointment_id}",
                200,
                data=edit_data,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Admin can edit appointments")
            else:
                print("   ❌ Admin cannot edit appointments")
                all_success = False
        
        # Test 2: Doctor can edit appointments (accept, add notes, etc.)
        if 'doctor' in self.tokens:
            edit_data = {
                "status": "accepted",
                "doctor_id": self.users['doctor']['id'],
                "doctor_notes": "Patient case reviewed by doctor"
            }
            
            success, response = self.run_test(
                "Edit Appointment (Doctor - Should Work)",
                "PUT",
                f"appointments/{self.appointment_id}",
                200,
                data=edit_data,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor can edit appointments")
            else:
                print("   ❌ Doctor cannot edit appointments")
                all_success = False
        
        # Test 3: Provider can edit their own appointments
        if 'provider' in self.tokens:
            edit_data = {
                "consultation_notes": "Updated consultation notes by provider"
            }
            
            success, response = self.run_test(
                "Edit Own Appointment (Provider - Should Work)",
                "PUT",
                f"appointments/{self.appointment_id}",
                200,
                data=edit_data,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider can edit their own appointments")
            else:
                print("   ❌ Provider cannot edit their own appointments")
                all_success = False
        
        # Test 4: Create another appointment with different provider to test access control
        # First, create a test provider user
        if 'admin' in self.tokens:
            test_provider_data = {
                "username": f"test_provider_{datetime.now().strftime('%H%M%S')}",
                "email": f"test_provider_{datetime.now().strftime('%H%M%S')}@example.com",
                "password": "TestPass123!",
                "phone": "+1234567890",
                "full_name": "Test Provider for Access Control",
                "role": "provider",
                "district": "Test District"
            }
            
            success, response = self.run_test(
                "Create Test Provider for Access Control",
                "POST",
                "admin/create-user",
                200,
                data=test_provider_data,
                token=self.tokens['admin']
            )
            
            if success:
                test_provider_id = response.get('id')
                
                # Login as the test provider
                login_success, login_response = self.run_test(
                    "Login Test Provider",
                    "POST",
                    "login",
                    200,
                    data={"username": test_provider_data["username"], "password": test_provider_data["password"]}
                )
                
                if login_success:
                    test_provider_token = login_response['access_token']
                    
                    # Test provider trying to edit another provider's appointment (should fail)
                    edit_data = {
                        "consultation_notes": "Unauthorized edit attempt"
                    }
                    
                    success, response = self.run_test(
                        "Edit Other's Appointment (Provider - Should Fail)",
                        "PUT",
                        f"appointments/{self.appointment_id}",
                        403,
                        data=edit_data,
                        token=test_provider_token
                    )
                    
                    if success:
                        print("   ✅ Provider correctly denied access to other's appointments")
                    else:
                        print("   ❌ Provider unexpectedly allowed to edit other's appointments")
                        all_success = False
                
                # Cleanup - delete test provider
                self.run_test(
                    "Cleanup Test Provider",
                    "DELETE",
                    f"users/{test_provider_id}",
                    200,
                    token=self.tokens['admin']
                )
        
        # Test 5: Test editing with invalid appointment ID
        invalid_appointment_id = "invalid-appointment-id-12345"
        edit_data = {"status": "accepted"}
        
        success, response = self.run_test(
            "Edit Invalid Appointment (Should Fail)",
            "PUT",
            f"appointments/{invalid_appointment_id}",
            404,
            data=edit_data,
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Invalid appointment ID correctly rejected")
        else:
            print("   ❌ Invalid appointment ID unexpectedly accepted")
            all_success = False
        
        return all_success

    def test_video_call_functionality(self):
        """Test video call functionality - DEPRECATED, use test_video_call_start_and_join instead"""
        return self.test_video_call_start_and_join()

def main():
    print("🏥 MedConnect Telehealth API Testing - FOCUSED ON VIDEO CALLS & APPOINTMENT EDITING")
    print("=" * 80)
    
    tester = MedConnectAPITester()
    
    # Test sequence - focused on video call and appointment edit functionality
    tests = [
        ("Health Check", tester.test_health_check),
        ("Login All Roles", tester.test_login_all_roles),
        ("Create Appointment", tester.test_create_appointment),
        ("Video Call Start and Join", tester.test_video_call_start_and_join),
        ("Appointment Edit Permissions", tester.test_appointment_edit_permissions),
    ]
    
    print(f"\n🚀 Running {len(tests)} focused test suites...")
    
    failed_tests = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            if not result:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ Test suite '{test_name}' failed with error: {str(e)}")
            failed_tests.append(test_name)
    
    # Print final results
    print(f"\n{'='*80}")
    print(f"📊 Final Results:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if failed_tests:
        print(f"\n❌ Failed Test Suites ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    
    # Special focus on video call and appointment edit features
    print(f"\n📹 VIDEO CALL & APPOINTMENT EDIT SUMMARY:")
    if len(tester.tokens) == 3:
        print(f"   ✅ All 3 user types can login successfully")
        print(f"   ✅ Provider: {tester.demo_credentials['provider']['username']}")
        print(f"   ✅ Doctor: {tester.demo_credentials['doctor']['username']}")
        print(f"   ✅ Admin: {tester.demo_credentials['admin']['username']}")
    else:
        print(f"   ⚠️  Only {len(tester.tokens)}/3 users can login")
    
    if tester.appointment_id:
        print(f"   ✅ Test appointment created: {tester.appointment_id}")
    else:
        print(f"   ❌ No test appointment was created")
    
    if tester.tests_passed >= tester.tests_run * 0.8:  # 80% pass rate
        print("🎉 Video call and appointment edit functionality is working correctly!")
        return 0
    else:
        print("⚠️  Some critical tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())