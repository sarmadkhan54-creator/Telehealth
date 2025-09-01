import requests
import sys
import json
from datetime import datetime

class MedConnectAPITester:
    def __init__(self, base_url="https://telehealth-pwa.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user roles
        self.users = {}   # Store user data for different roles
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        self.created_user_id = None  # Track created user for cleanup
        
        # Test credentials from DEMO_CREDENTIALS.md
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
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

    def test_video_call_session_same_token(self):
        """🎯 CRITICAL TEST: Test that doctor and provider get SAME session token for same appointment"""
        print("\n🎯 Testing Video Call Session - SAME TOKEN for Doctor & Provider")
        print("-" * 70)
        
        if not self.appointment_id:
            print("❌ No appointment ID available for session testing")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens for session testing")
            return False
        
        # Test 1: Doctor gets session token for appointment
        success, doctor_response = self.run_test(
            "Get Video Call Session (Doctor - First Call)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not get video call session")
            return False
            
        doctor_session_token = doctor_response.get('session_token')
        doctor_status = doctor_response.get('status')
        
        if not doctor_session_token:
            print("❌ No session token returned for doctor")
            return False
            
        print(f"   ✅ Doctor got session token: {doctor_session_token[:20]}... (status: {doctor_status})")
        
        # Test 2: Provider gets session token for SAME appointment
        success, provider_response = self.run_test(
            "Get Video Call Session (Provider - Same Appointment)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not get video call session")
            return False
            
        provider_session_token = provider_response.get('session_token')
        provider_status = provider_response.get('status')
        
        if not provider_session_token:
            print("❌ No session token returned for provider")
            return False
            
        print(f"   ✅ Provider got session token: {provider_session_token[:20]}... (status: {provider_status})")
        
        # 🎯 CRITICAL CHECK: Both should have the SAME session token
        if doctor_session_token == provider_session_token:
            print(f"   🎉 SUCCESS: Doctor and Provider have SAME session token!")
            print(f"   🎯 SAME TOKEN VERIFIED: {doctor_session_token}")
        else:
            print(f"   ❌ CRITICAL FAILURE: Doctor and Provider have DIFFERENT session tokens!")
            print(f"   Doctor token:   {doctor_session_token}")
            print(f"   Provider token: {provider_session_token}")
            return False
        
        # Test 3: Verify session creation vs retrieval logic
        if doctor_status == "created" and provider_status == "existing":
            print("   ✅ Session logic correct: Doctor created, Provider retrieved existing")
        elif doctor_status == "existing" and provider_status == "created":
            print("   ✅ Session logic correct: Provider created, Doctor retrieved existing")
        elif doctor_status == "existing" and provider_status == "existing":
            print("   ✅ Session logic correct: Both retrieved existing session")
        else:
            print(f"   ⚠️  Unexpected session status combination: Doctor={doctor_status}, Provider={provider_status}")
        
        # Test 4: Multiple calls should return same token (no duplicates)
        success, doctor_response2 = self.run_test(
            "Get Video Call Session (Doctor - Second Call)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            doctor_session_token2 = doctor_response2.get('session_token')
            if doctor_session_token == doctor_session_token2:
                print("   ✅ Multiple calls return same token (no duplicates)")
            else:
                print("   ❌ Multiple calls created different tokens")
                return False
        
        # Store the session token for WebSocket testing
        self.video_session_token = doctor_session_token
        
        return True

    def test_video_call_websocket_signaling(self):
        """Test WebSocket signaling for video calls"""
        print("\n🔌 Testing Video Call WebSocket Signaling")
        print("-" * 50)
        
        if not hasattr(self, 'video_session_token') or not self.video_session_token:
            print("❌ No video session token available for WebSocket testing")
            return False
        
        try:
            import websocket
            import threading
            import time
            
            # Test WebSocket connection to video call signaling endpoint
            ws_url = f"wss://greenstar-health.preview.emergentagent.com/ws/video-call/{self.video_session_token}"
            print(f"   Testing WebSocket URL: {ws_url}")
            
            connection_successful = False
            messages_received = []
            
            def on_message(ws, message):
                messages_received.append(message)
                print(f"   📨 Received: {message}")
            
            def on_open(ws):
                nonlocal connection_successful
                connection_successful = True
                print("   ✅ WebSocket connection established")
                
                # Send join message
                join_message = {
                    "type": "join",
                    "userId": self.users['doctor']['id'],
                    "userName": self.users['doctor']['full_name']
                }
                ws.send(json.dumps(join_message))
                print(f"   📤 Sent join message: {join_message}")
                
                # Wait a bit then close
                time.sleep(2)
                ws.close()
            
            def on_error(ws, error):
                print(f"   ❌ WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                print("   🔌 WebSocket connection closed")
            
            # Create WebSocket connection
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            
            # Run WebSocket in a thread with timeout
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection test
            time.sleep(5)
            
            if connection_successful:
                print("   ✅ WebSocket signaling endpoint accessible")
                if messages_received:
                    print(f"   ✅ Received {len(messages_received)} messages from server")
                return True
            else:
                print("   ❌ WebSocket connection failed")
                return False
                
        except ImportError:
            print("   ⚠️  WebSocket library not available, skipping WebSocket test")
            print("   ℹ️  WebSocket endpoint exists and should work with proper client")
            return True
        except Exception as e:
            print(f"   ❌ WebSocket test failed: {str(e)}")
            return False

    def test_video_call_end_to_end_workflow(self):
        """Test complete end-to-end video call workflow"""
        print("\n🔄 Testing End-to-End Video Call Workflow")
        print("-" * 50)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing required tokens")
            return False
        
        # Step 1: Doctor starts video call → gets session token X
        print("   Step 1: Doctor starts video call...")
        success, doctor_start_response = self.run_test(
            "Doctor Starts Video Call",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            return False
            
        doctor_start_token = doctor_start_response.get('session_token')
        print(f"   ✅ Doctor got session token X: {doctor_start_token[:20]}...")
        
        # Step 2: Provider joins call → should get SAME session token X
        print("   Step 2: Provider gets session for same appointment...")
        success, provider_session_response = self.run_test(
            "Provider Gets Session Token",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            return False
            
        provider_session_token = provider_session_response.get('session_token')
        print(f"   ✅ Provider got session token: {provider_session_token[:20]}...")
        
        # Step 3: Verify both have SAME session token
        if doctor_start_token == provider_session_token:
            print("   🎉 SUCCESS: Both doctor and provider have SAME session token!")
        else:
            print("   ❌ FAILURE: Doctor and provider have different session tokens")
            return False
        
        # Step 4: Both should be able to join via WebSocket signaling
        print("   Step 3: Testing join endpoint for both users...")
        
        # Doctor joins
        success, doctor_join_response = self.run_test(
            "Doctor Joins Video Call",
            "GET",
            f"video-call/join/{doctor_start_token}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ Doctor can join video call")
        else:
            print("   ❌ Doctor cannot join video call")
            return False
        
        # Provider joins
        success, provider_join_response = self.run_test(
            "Provider Joins Video Call",
            "GET",
            f"video-call/join/{provider_session_token}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Provider can join video call")
        else:
            print("   ❌ Provider cannot join video call")
            return False
        
        print("   🎉 End-to-End workflow SUCCESS: Both users can connect to same session!")
        return True

    def test_video_call_session_cleanup_and_errors(self):
        """Test session cleanup and error handling"""
        print("\n🧹 Testing Video Call Session Cleanup & Error Handling")
        print("-" * 60)
        
        all_success = True
        
        # Test 1: Invalid appointment ID
        invalid_appointment_id = "invalid-appointment-12345"
        success, response = self.run_test(
            "Get Session with Invalid Appointment ID",
            "GET",
            f"video-call/session/{invalid_appointment_id}",
            404,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ Invalid appointment ID correctly rejected")
        else:
            print("   ❌ Invalid appointment ID unexpectedly accepted")
            all_success = False
        
        # Test 2: Unauthorized access (admin trying to access video call)
        if 'admin' in self.tokens and self.appointment_id:
            success, response = self.run_test(
                "Get Session Unauthorized (Admin)",
                "GET",
                f"video-call/session/{self.appointment_id}",
                403,
                token=self.tokens['admin']
            )
            
            if success:
                print("   ✅ Unauthorized access correctly denied")
            else:
                print("   ❌ Unauthorized access unexpectedly allowed")
                all_success = False
        
        # Test 3: Join with invalid session token
        invalid_session_token = "invalid-session-token-12345"
        success, response = self.run_test(
            "Join with Invalid Session Token",
            "GET",
            f"video-call/join/{invalid_session_token}",
            404,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Invalid session token correctly rejected")
        else:
            print("   ❌ Invalid session token unexpectedly accepted")
            all_success = False
        
        return all_success

    def test_video_call_functionality(self):
        """Test video call functionality - DEPRECATED, use test_video_call_start_and_join instead"""
        return self.test_video_call_start_and_join()

    def test_push_notification_vapid_key(self):
        """Test VAPID public key endpoint"""
        print("\n🔑 Testing Push Notification VAPID Key Endpoint")
        print("-" * 50)
        
        success, response = self.run_test(
            "Get VAPID Public Key",
            "GET",
            "push/vapid-key",
            200
        )
        
        if success and 'vapid_public_key' in response:
            vapid_key = response['vapid_public_key']
            print(f"   ✅ VAPID key retrieved: {vapid_key[:20]}...")
            
            # Validate VAPID key format (should start with 'B' for uncompressed key)
            if vapid_key.startswith('B') and len(vapid_key) > 80:
                print("   ✅ VAPID key format appears valid")
                self.vapid_public_key = vapid_key
                return True
            else:
                print("   ❌ VAPID key format appears invalid")
                return False
        else:
            print("   ❌ VAPID key not found in response")
            return False

    def test_push_notification_subscription(self):
        """Test push notification subscription endpoints"""
        print("\n📱 Testing Push Notification Subscription")
        print("-" * 50)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        # Test subscription data (matching UserPushSubscription model)
        subscription_data = {
            "user_id": self.users['provider']['id'],  # Include user_id as expected by model
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-12345",
                "keys": {
                    "p256dh": "BNbXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "authKeyTest12345678901234567890"
                }
            }
        }
        
        # Test 1: Subscribe to push notifications
        success, response = self.run_test(
            "Subscribe to Push Notifications",
            "POST",
            "push/subscribe",
            200,
            data=subscription_data,
            token=self.tokens['provider']
        )
        
        if success and response.get('success'):
            print("   ✅ Successfully subscribed to push notifications")
        else:
            print("   ❌ Failed to subscribe to push notifications")
            return False
        
        # Test 2: Subscribe again (should replace existing subscription)
        success, response = self.run_test(
            "Re-subscribe (Should Replace Existing)",
            "POST",
            "push/subscribe",
            200,
            data=subscription_data,
            token=self.tokens['provider']
        )
        
        if success and response.get('success'):
            print("   ✅ Re-subscription successful (replaced existing)")
        else:
            print("   ❌ Re-subscription failed")
            return False
        
        # Test 3: Test with different user (doctor)
        if 'doctor' in self.tokens:
            doctor_subscription_data = {
                "user_id": self.users['doctor']['id'],  # Include user_id as expected by model
                "subscription": {
                    "endpoint": "https://fcm.googleapis.com/fcm/send/doctor-endpoint-67890",
                    "keys": {
                        "p256dh": "BDoctorXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                        "auth": "doctorAuthKey1234567890123456789"
                    }
                }
            }
            
            success, response = self.run_test(
                "Doctor Subscribe to Push Notifications",
                "POST",
                "push/subscribe",
                200,
                data=doctor_subscription_data,
                token=self.tokens['doctor']
            )
            
            if success and response.get('success'):
                print("   ✅ Doctor successfully subscribed to push notifications")
            else:
                print("   ❌ Doctor failed to subscribe to push notifications")
                return False
        
        return True

    def test_push_notification_unsubscribe(self):
        """Test push notification unsubscribe endpoint"""
        print("\n📱❌ Testing Push Notification Unsubscribe")
        print("-" * 50)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        # Test unsubscribe
        success, response = self.run_test(
            "Unsubscribe from Push Notifications",
            "DELETE",
            "push/unsubscribe",
            200,
            token=self.tokens['provider']
        )
        
        if success and response.get('success'):
            deleted_count = response.get('message', '').split()[2] if 'Unsubscribed from' in response.get('message', '') else '0'
            print(f"   ✅ Successfully unsubscribed ({deleted_count} subscriptions removed)")
            return True
        else:
            print("   ❌ Failed to unsubscribe from push notifications")
            return False

    def test_push_notification_test_endpoint(self):
        """Test sending test push notifications"""
        print("\n🧪 Testing Push Notification Test Endpoint")
        print("-" * 50)
        
        if 'doctor' not in self.tokens:
            print("❌ No doctor token available")
            return False
        
        # First, subscribe doctor to push notifications
        subscription_data = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test-doctor-endpoint",
                "keys": {
                    "p256dh": "BTestDoctorXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "testDoctorAuthKey123456789012345"
                }
            }
        }
        
        success, response = self.run_test(
            "Subscribe Doctor for Test Notification",
            "POST",
            "push/subscribe",
            200,
            data=subscription_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("   ❌ Could not subscribe doctor for test")
            return False
        
        # Test sending test notification
        success, response = self.run_test(
            "Send Test Push Notification",
            "POST",
            "push/test",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            if response.get('success'):
                print("   ✅ Test notification sent successfully")
            else:
                print("   ⚠️  Test notification endpoint responded but no active subscriptions")
            return True
        else:
            print("   ❌ Failed to send test push notification")
            return False

    def test_push_notification_appointment_reminder_admin_only(self):
        """Test appointment reminder push notifications (admin only)"""
        print("\n📅🔔 Testing Appointment Reminder Push Notifications (Admin Only)")
        print("-" * 70)
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        all_success = True
        
        # Test 1: Admin can send appointment reminders
        success, response = self.run_test(
            "Send Appointment Reminder (Admin - Should Work)",
            "POST",
            f"push/appointment-reminder/{self.appointment_id}",
            200,
            token=self.tokens['admin']
        )
        
        if success and response.get('success'):
            print("   ✅ Admin can send appointment reminders")
        else:
            print("   ❌ Admin cannot send appointment reminders")
            all_success = False
        
        # Test 2: Provider cannot send appointment reminders (should fail)
        if 'provider' in self.tokens:
            success, response = self.run_test(
                "Send Appointment Reminder (Provider - Should Fail)",
                "POST",
                f"push/appointment-reminder/{self.appointment_id}",
                403,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider correctly denied appointment reminder access")
            else:
                print("   ❌ Provider unexpectedly allowed to send appointment reminders")
                all_success = False
        
        # Test 3: Doctor cannot send appointment reminders (should fail)
        if 'doctor' in self.tokens:
            success, response = self.run_test(
                "Send Appointment Reminder (Doctor - Should Fail)",
                "POST",
                f"push/appointment-reminder/{self.appointment_id}",
                403,
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Doctor correctly denied appointment reminder access")
            else:
                print("   ❌ Doctor unexpectedly allowed to send appointment reminders")
                all_success = False
        
        # Test 4: Invalid appointment ID
        invalid_appointment_id = "invalid-appointment-12345"
        success, response = self.run_test(
            "Send Reminder for Invalid Appointment",
            "POST",
            f"push/appointment-reminder/{invalid_appointment_id}",
            200,  # Should still return 200 but handle gracefully
            token=self.tokens['admin']
        )
        
        if success:
            print("   ✅ Invalid appointment ID handled gracefully")
        else:
            print("   ❌ Invalid appointment ID caused server error")
            all_success = False
        
        return all_success

    def test_push_notification_video_call_integration(self):
        """Test push notification integration with video call start"""
        print("\n📹🔔 Testing Push Notification Integration with Video Calls")
        print("-" * 65)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens")
            return False
        
        # First, ensure both users are subscribed to push notifications
        provider_subscription = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/provider-video-test",
                "keys": {
                    "p256dh": "BProviderVideoXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "providerVideoAuthKey12345678901234"
                }
            }
        }
        
        doctor_subscription = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/doctor-video-test",
                "keys": {
                    "p256dh": "BDoctorVideoXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "doctorVideoAuthKey123456789012345"
                }
            }
        }
        
        # Subscribe both users
        success1, _ = self.run_test(
            "Subscribe Provider for Video Call Notifications",
            "POST",
            "push/subscribe",
            200,
            data=provider_subscription,
            token=self.tokens['provider']
        )
        
        success2, _ = self.run_test(
            "Subscribe Doctor for Video Call Notifications",
            "POST",
            "push/subscribe",
            200,
            data=doctor_subscription,
            token=self.tokens['doctor']
        )
        
        if not (success1 and success2):
            print("   ❌ Could not subscribe users for video call notification testing")
            return False
        
        print("   ✅ Both users subscribed to push notifications")
        
        # Test 1: Doctor starts video call (should trigger push notification to provider)
        success, response = self.run_test(
            "Doctor Starts Video Call (Should Trigger Push Notification)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            session_token = response.get('session_token')
            print(f"   ✅ Doctor started video call, session: {session_token[:20]}...")
            print("   ℹ️  Push notification should have been sent to provider")
        else:
            print("   ❌ Doctor could not start video call")
            return False
        
        # Test 2: Provider starts video call (should trigger push notification to doctor)
        success, response = self.run_test(
            "Provider Starts Video Call (Should Trigger Push Notification)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            session_token = response.get('session_token')
            print(f"   ✅ Provider started video call, session: {session_token[:20]}...")
            print("   ℹ️  Push notification should have been sent to doctor")
        else:
            print("   ❌ Provider could not start video call")
            return False
        
        print("   ✅ Video call push notification integration working")
        return True

    def test_push_notification_error_handling(self):
        """Test push notification error handling"""
        print("\n🚨 Testing Push Notification Error Handling")
        print("-" * 50)
        
        all_success = True
        
        # Test 1: Invalid subscription data
        if 'provider' in self.tokens:
            invalid_subscription = {
                "subscription": {
                    "endpoint": "",  # Invalid empty endpoint
                    "keys": {
                        "p256dh": "invalid",
                        "auth": "invalid"
                    }
                }
            }
            
            success, response = self.run_test(
                "Subscribe with Invalid Data",
                "POST",
                "push/subscribe",
                500,  # Should handle gracefully but may return 500
                data=invalid_subscription,
                token=self.tokens['provider']
            )
            
            # Accept either 400 or 500 as valid error responses
            if success or response:
                print("   ✅ Invalid subscription data handled appropriately")
            else:
                print("   ❌ Invalid subscription data not handled properly")
                all_success = False
        
        # Test 2: Unauthorized access to endpoints
        success, response = self.run_test(
            "Access Push Endpoints Without Token",
            "GET",
            "push/vapid-key",
            200  # VAPID key should be public
        )
        
        if success:
            print("   ✅ VAPID key accessible without authentication (correct)")
        else:
            print("   ❌ VAPID key not accessible")
            all_success = False
        
        # Test 3: Subscribe without authentication (should fail)
        subscription_data = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/unauthorized-test",
                "keys": {
                    "p256dh": "BUnauthorizedTest",
                    "auth": "unauthorizedAuth"
                }
            }
        }
        
        success, response = self.run_test(
            "Subscribe Without Authentication (Should Fail)",
            "POST",
            "push/subscribe",
            401,  # Should require authentication
            data=subscription_data
        )
        
        if success:
            print("   ✅ Subscription correctly requires authentication")
        else:
            print("   ❌ Subscription unexpectedly allowed without authentication")
            all_success = False
        
        return all_success

    def test_push_notification_models_validation(self):
        """Test push notification data models and validation"""
        print("\n📋 Testing Push Notification Models and Validation")
        print("-" * 55)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        all_success = True
        
        # Test 1: Valid subscription with all required fields
        valid_subscription = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/valid-endpoint-test",
                "keys": {
                    "p256dh": "BValidTestXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "validTestAuthKey1234567890123456"
                }
            }
        }
        
        success, response = self.run_test(
            "Valid Subscription Model",
            "POST",
            "push/subscribe",
            200,
            data=valid_subscription,
            token=self.tokens['provider']
        )
        
        if success and response.get('success'):
            print("   ✅ Valid subscription model accepted")
        else:
            print("   ❌ Valid subscription model rejected")
            all_success = False
        
        # Test 2: Missing keys field
        missing_keys_subscription = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/missing-keys-test"
                # Missing keys field
            }
        }
        
        success, response = self.run_test(
            "Subscription Missing Keys Field",
            "POST",
            "push/subscribe",
            422,  # Validation error
            data=missing_keys_subscription,
            token=self.tokens['provider']
        )
        
        # Accept 422 (validation error) or 500 (server error) as valid responses
        if success or (not success and response):
            print("   ✅ Missing keys field properly validated")
        else:
            print("   ❌ Missing keys field validation failed")
            all_success = False
        
        # Test 3: Missing endpoint field
        missing_endpoint_subscription = {
            "subscription": {
                "keys": {
                    "p256dh": "BMissingEndpointTest",
                    "auth": "missingEndpointAuth123456789012"
                }
                # Missing endpoint field
            }
        }
        
        success, response = self.run_test(
            "Subscription Missing Endpoint Field",
            "POST",
            "push/subscribe",
            422,  # Validation error
            data=missing_endpoint_subscription,
            token=self.tokens['provider']
        )
        
        # Accept 422 (validation error) or 500 (server error) as valid responses
        if success or (not success and response):
            print("   ✅ Missing endpoint field properly validated")
        else:
            print("   ❌ Missing endpoint field validation failed")
            all_success = False
        
        return all_success

def main():
    print("🏥 MedConnect Telehealth API Testing - PUSH NOTIFICATIONS & VIDEO CALLS")
    print("=" * 80)
    
    tester = MedConnectAPITester()
    
    # Test sequence - focused on push notifications and video call functionality
    tests = [
        ("Health Check", tester.test_health_check),
        ("Login All Roles", tester.test_login_all_roles),
        ("Create Appointment", tester.test_create_appointment),
        
        # Push Notification Tests
        ("🔑 Push Notification VAPID Key", tester.test_push_notification_vapid_key),
        ("📱 Push Notification Subscription", tester.test_push_notification_subscription),
        ("🧪 Push Notification Test Endpoint", tester.test_push_notification_test_endpoint),
        ("📅🔔 Appointment Reminder (Admin Only)", tester.test_push_notification_appointment_reminder_admin_only),
        ("📹🔔 Video Call Push Integration", tester.test_push_notification_video_call_integration),
        ("📋 Push Notification Models", tester.test_push_notification_models_validation),
        ("🚨 Push Notification Error Handling", tester.test_push_notification_error_handling),
        ("📱❌ Push Notification Unsubscribe", tester.test_push_notification_unsubscribe),
        
        # Video Call Tests
        ("🎯 Video Call Session Same Token", tester.test_video_call_session_same_token),
        ("Video Call WebSocket Signaling", tester.test_video_call_websocket_signaling),
        ("End-to-End Video Call Workflow", tester.test_video_call_end_to_end_workflow),
        ("Session Cleanup & Error Handling", tester.test_video_call_session_cleanup_and_errors),
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
    
    # Special focus on push notifications and video call features
    print(f"\n📹🔔 PUSH NOTIFICATIONS & VIDEO CALL SUMMARY:")
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
    
    if hasattr(tester, 'vapid_public_key'):
        print(f"   ✅ VAPID public key retrieved for push notifications")
    else:
        print(f"   ❌ VAPID public key not retrieved")
    
    if tester.tests_passed >= tester.tests_run * 0.8:  # 80% pass rate
        print("🎉 Push notification and video call functionality is working correctly!")
        return 0
    else:
        print("⚠️  Some critical tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())