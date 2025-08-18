import requests
import sys
import json
from datetime import datetime

class MedConnectAPITester:
    def __init__(self, base_url="https://19543fde-1955-4452-861c-5fe800d2c222.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user roles
        self.users = {}   # Store user data for different roles
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        self.created_user_id = None  # Track created user for cleanup
        
        # Demo credentials to test admin access control
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

    def test_get_users(self):
        """Test getting users (admin only)"""
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
            
        success, response = self.run_test(
            "Get All Users (Admin)",
            "GET",
            "users", 
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print(f"   Found {len(response)} users")
        
        return success

    def test_create_appointment(self):
        """Test creating an appointment (provider only)"""
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
            "Create Appointment",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            self.appointment_id = response.get('id')
            print(f"   Created appointment ID: {self.appointment_id}")
        
        return success

    def test_get_appointments(self):
        """Test getting appointments for different roles"""
        for role in ['provider', 'doctor', 'admin']:
            if role not in self.tokens:
                print(f"❌ No {role} token available")
                continue
                
            success, response = self.run_test(
                f"Get Appointments ({role.title()})",
                "GET",
                "appointments",
                200,
                token=self.tokens[role]
            )
            
            if success:
                print(f"   {role.title()} can see {len(response)} appointments")

    def test_update_appointment(self):
        """Test updating appointment status (doctor only)"""
        if 'doctor' not in self.tokens or not self.appointment_id:
            print("❌ No doctor token or appointment ID available")
            return False
            
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id'],
            "consultation_notes": "Appointment accepted by doctor"
        }
        
        success, response = self.run_test(
            "Update Appointment Status",
            "PUT",
            f"appointments/{self.appointment_id}",
            200,
            data=update_data,
            token=self.tokens['doctor']
        )
        
        return success

    def test_start_video_call(self):
        """Test starting a video call"""
        if 'doctor' not in self.tokens or not self.appointment_id:
            print("❌ No doctor token or appointment ID available")
            return False
            
        success, response = self.run_test(
            "Start Video Call",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            session_token = response.get('session_token')
            print(f"   Video call session token: {session_token}")
        
        return success

    def test_emergency_appointment(self):
        """Test creating an emergency appointment"""
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
        
        return success

def main():
    print("🏥 MedConnect Telehealth API Testing - LOGIN CREDENTIALS FIX VERIFICATION")
    print("=" * 80)
    
    tester = MedConnectAPITester()
    
    # Test sequence - focusing on login credentials fix
    tests = [
        ("Health Check", tester.test_health_check),
        ("NEW Demo Login Credentials", tester.test_demo_login_credentials),
        ("OLD Credentials Should Fail", tester.test_old_credentials_fail),
        ("Get Users (Admin Access)", tester.test_get_users),
        ("Create Appointment (Provider)", tester.test_create_appointment),
        ("Get Appointments (All Roles)", tester.test_get_appointments),
        ("Update Appointment (Doctor)", tester.test_update_appointment),
        ("Start Video Call", tester.test_start_video_call),
        ("Emergency Appointment", tester.test_emergency_appointment),
    ]
    
    print(f"\n🚀 Running {len(tests)} test suites...")
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test suite '{test_name}' failed with error: {str(e)}")
    
    # Print final results
    print(f"\n{'='*80}")
    print(f"📊 Final Results:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "No tests run")
    
    # Special focus on login credentials
    print(f"\n🔑 LOGIN CREDENTIALS SUMMARY:")
    if len(tester.tokens) == 3:
        print(f"   ✅ All 3 demo user types can login successfully")
        print(f"   ✅ Provider: {tester.demo_credentials['provider']['username']}")
        print(f"   ✅ Doctor: {tester.demo_credentials['doctor']['username']}")
        print(f"   ✅ Admin: {tester.demo_credentials['admin']['username']}")
    else:
        print(f"   ⚠️  Only {len(tester.tokens)}/3 demo users can login")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Login fix is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())