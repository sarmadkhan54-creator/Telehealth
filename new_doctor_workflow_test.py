import requests
import sys
import json
from datetime import datetime

class NewDoctorWorkflowTester:
    def __init__(self, base_url="https://docstream-sync.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        
        # Demo credentials
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
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

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

    def login_all_users(self):
        """Login all demo users"""
        print("\n🔑 Logging in all demo users...")
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
                print(f"   ✅ {role.title()} login successful")
                print(f"   User ID: {response['user'].get('id')}")
                print(f"   Full Name: {response['user'].get('full_name')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                all_success = False
        
        return all_success

    def test_new_doctor_workflow(self):
        """🎯 TEST NEW DOCTOR WORKFLOW AFTER REMOVING ACCEPT FUNCTIONALITY"""
        print("\n🎯 TESTING NEW DOCTOR WORKFLOW AFTER REMOVING ACCEPT FUNCTIONALITY")
        print("=" * 80)
        print("Key Changes:")
        print("- Doctors no longer need to 'accept' appointments before video calling")
        print("- Doctors can write notes to providers without accepting appointments")
        print("- New appointments created by providers should be visible to doctors immediately")
        print("- Doctors can directly video call appointments without needing to accept them first")
        print("=" * 80)
        
        all_success = True
        
        # Step 1: Create a test appointment using demo_provider
        print("\n1️⃣ STEP 1: Create Test Appointment as Provider")
        print("-" * 60)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        appointment_data = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 28,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "140/90",
                    "heart_rate": 95,
                    "temperature": 101.2,
                    "oxygen_saturation": "96%"
                },
                "consultation_reason": "Severe chest pain and shortness of breath - urgent consultation needed"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient reports sudden onset of chest pain 2 hours ago. Vital signs elevated. Requires immediate medical attention."
        }
        
        success, response = self.run_test(
            "Create Emergency Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            self.appointment_id = response.get('id')
            print(f"   ✅ Emergency appointment created successfully")
            print(f"   Appointment ID: {self.appointment_id}")
            print(f"   Patient: {appointment_data['patient']['name']}")
            print(f"   Type: {appointment_data['appointment_type']}")
            print(f"   Reason: {appointment_data['patient']['consultation_reason']}")
        else:
            print("   ❌ Failed to create test appointment")
            all_success = False
            return False
        
        # Step 2: Login as demo_doctor and verify appointment appears immediately
        print("\n2️⃣ STEP 2: Verify Doctor Can See New Appointment Immediately")
        print("-" * 60)
        
        if 'doctor' not in self.tokens:
            print("❌ No doctor token available")
            return False
        
        success, response = self.run_test(
            "Get All Appointments (Doctor)",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            appointments = response
            print(f"   ✅ Doctor can access appointments endpoint")
            print(f"   Total appointments visible to doctor: {len(appointments)}")
            
            # Find our newly created appointment
            new_appointment = None
            for apt in appointments:
                if apt.get('id') == self.appointment_id:
                    new_appointment = apt
                    break
            
            if new_appointment:
                print(f"   ✅ NEW APPOINTMENT IMMEDIATELY VISIBLE TO DOCTOR")
                print(f"   Appointment Status: {new_appointment.get('status', 'N/A')}")
                print(f"   Patient Name: {new_appointment.get('patient', {}).get('name', 'N/A')}")
                print(f"   Provider: {new_appointment.get('provider', {}).get('full_name', 'N/A')}")
                print(f"   Type: {new_appointment.get('appointment_type', 'N/A')}")
                
                # Verify appointment is in pending status (not accepted yet)
                if new_appointment.get('status') == 'pending':
                    print(f"   ✅ Appointment correctly in 'pending' status")
                else:
                    print(f"   ⚠️  Appointment status: {new_appointment.get('status')} (expected 'pending')")
                
                # Verify no doctor_id is set yet
                if not new_appointment.get('doctor_id'):
                    print(f"   ✅ No doctor assigned yet (doctor_id is None)")
                else:
                    print(f"   ⚠️  Doctor already assigned: {new_appointment.get('doctor_id')}")
            else:
                print(f"   ❌ NEW APPOINTMENT NOT VISIBLE TO DOCTOR - CRITICAL ISSUE")
                all_success = False
        else:
            print("   ❌ Doctor cannot access appointments")
            all_success = False
        
        # Step 3: Test that doctors can directly video call appointments without accepting
        print("\n3️⃣ STEP 3: Test Direct Video Call Without Acceptance")
        print("-" * 60)
        
        # Test video call session creation (new Jitsi-based system)
        success, response = self.run_test(
            "Create Video Call Session (Doctor - No Acceptance Required)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ DOCTOR CAN DIRECTLY CREATE VIDEO CALL SESSION")
            print(f"   Jitsi URL: {response.get('jitsi_url', 'N/A')}")
            print(f"   Room Name: {response.get('room_name', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
            
            # Verify Jitsi URL format
            jitsi_url = response.get('jitsi_url', '')
            if 'meet.jit.si' in jitsi_url and self.appointment_id in jitsi_url:
                print(f"   ✅ Jitsi URL format correct and includes appointment ID")
            else:
                print(f"   ❌ Jitsi URL format incorrect: {jitsi_url}")
                all_success = False
        else:
            print("   ❌ Doctor cannot create video call session without acceptance")
            all_success = False
        
        # Test provider can also join the same video call
        success, response = self.run_test(
            "Provider Joins Same Video Call Session",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print(f"   ✅ PROVIDER CAN JOIN SAME VIDEO CALL SESSION")
            provider_jitsi_url = response.get('jitsi_url', '')
            print(f"   Provider Jitsi URL: {provider_jitsi_url}")
            
            # Verify both doctor and provider get the same Jitsi room
            if provider_jitsi_url == jitsi_url:
                print(f"   ✅ SAME JITSI ROOM FOR BOTH DOCTOR AND PROVIDER")
            else:
                print(f"   ❌ Different Jitsi rooms - video call won't work properly")
                all_success = False
        else:
            print("   ❌ Provider cannot join video call session")
            all_success = False
        
        # Step 4: Test that doctors can write notes without accepting appointments
        print("\n4️⃣ STEP 4: Test Writing Notes Without Acceptance")
        print("-" * 60)
        
        note_data = {
            "note": "Based on the patient's symptoms (chest pain, elevated vitals), I recommend immediate ECG and blood work. Please prepare the patient for potential emergency transport if symptoms worsen. I will join the video call shortly to assess further.",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Writes Note Without Accepting Appointment",
            "POST",
            f"appointments/{self.appointment_id}/notes",
            200,
            data=note_data,
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ DOCTOR CAN WRITE NOTES WITHOUT ACCEPTING APPOINTMENT")
            print(f"   Note ID: {response.get('note_id', 'N/A')}")
            print(f"   Message: {response.get('message', 'N/A')}")
        else:
            print("   ❌ Doctor cannot write notes without accepting appointment")
            all_success = False
        
        # Verify provider can see the doctor's note
        success, response = self.run_test(
            "Provider Views Doctor's Note",
            "GET",
            f"appointments/{self.appointment_id}/notes",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            notes = response
            print(f"   ✅ Provider can view notes ({len(notes)} notes found)")
            
            # Find doctor's note
            doctor_notes = [note for note in notes if note.get('sender_role') == 'doctor']
            if doctor_notes:
                print(f"   ✅ DOCTOR'S NOTE VISIBLE TO PROVIDER")
                print(f"   Doctor Note: {doctor_notes[0].get('note', 'N/A')[:100]}...")
                print(f"   Sender: {doctor_notes[0].get('sender_name', 'N/A')}")
            else:
                print(f"   ❌ Doctor's note not visible to provider")
                all_success = False
        else:
            print("   ❌ Provider cannot view notes")
            all_success = False
        
        # Step 5: Test notification system for video calls
        print("\n5️⃣ STEP 5: Test Video Call Notification System")
        print("-" * 60)
        
        # Test WebSocket status endpoint
        success, response = self.run_test(
            "Check WebSocket Status (Doctor)",
            "GET",
            "websocket/status",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ WebSocket status endpoint accessible")
            print(f"   Total connections: {response.get('websocket_status', {}).get('total_connections', 0)}")
            print(f"   Doctor connected: {response.get('current_user_connected', False)}")
        else:
            print("   ❌ WebSocket status endpoint not accessible")
            all_success = False
        
        # Test sending test WebSocket message
        success, response = self.run_test(
            "Send Test WebSocket Message (Doctor)",
            "POST",
            "websocket/test-message",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ WebSocket test message system working")
            print(f"   Message sent: {response.get('message_sent', False)}")
            print(f"   User connected: {response.get('user_connected', False)}")
        else:
            print("   ❌ WebSocket test message system not working")
            all_success = False
        
        # Step 6: Verify appointment visibility issue is resolved
        print("\n6️⃣ STEP 6: Verify Appointment Visibility Issue Resolution")
        print("-" * 60)
        
        # Create another appointment to test immediate visibility
        second_appointment_data = {
            "patient": {
                "name": "Michael Chen",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "130/85",
                    "heart_rate": 88,
                    "temperature": 99.1,
                    "oxygen_saturation": "98%"
                },
                "consultation_reason": "Persistent abdominal pain and nausea for 6 hours"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient experiencing severe abdominal pain. Possible appendicitis. Needs urgent evaluation."
        }
        
        success, response = self.run_test(
            "Create Second Test Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=second_appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            second_appointment_id = response.get('id')
            print(f"   ✅ Second appointment created: {second_appointment_id}")
            
            # Immediately check if doctor can see it
            success, response = self.run_test(
                "Doctor Sees Second Appointment Immediately",
                "GET",
                "appointments",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                appointments = response
                second_appointment_found = any(apt.get('id') == second_appointment_id for apt in appointments)
                
                if second_appointment_found:
                    print(f"   ✅ APPOINTMENT VISIBILITY ISSUE RESOLVED")
                    print(f"   Doctor can see new appointments immediately after creation")
                else:
                    print(f"   ❌ APPOINTMENT VISIBILITY ISSUE PERSISTS")
                    all_success = False
            else:
                print("   ❌ Doctor cannot access appointments")
                all_success = False
        else:
            print("   ❌ Could not create second test appointment")
            all_success = False
        
        # Final Summary
        print("\n" + "=" * 80)
        print("🎯 NEW DOCTOR WORKFLOW TESTING SUMMARY")
        print("=" * 80)
        
        if all_success:
            print("✅ NEW DOCTOR WORKFLOW: FULLY OPERATIONAL")
            print("✅ Doctors can see new appointments immediately without acceptance")
            print("✅ Doctors can directly video call appointments without accepting")
            print("✅ Doctors can write notes to providers without accepting")
            print("✅ Video call notification system working")
            print("✅ Appointment visibility issue resolved")
            print("\n🎉 ALL REVIEW REQUEST REQUIREMENTS VERIFIED AND WORKING")
        else:
            print("❌ NEW DOCTOR WORKFLOW: ISSUES DETECTED")
            print("❌ Some functionality not working as expected")
            print("❌ Review request requirements not fully met")
        
        return all_success

    def run_all_tests(self):
        """Run all tests for the new doctor workflow"""
        print("🚀 STARTING NEW DOCTOR WORKFLOW TESTING")
        print("=" * 80)
        
        # Login all users first
        if not self.login_all_users():
            print("❌ Failed to login demo users")
            return False
        
        # Run the main workflow test
        workflow_success = self.test_new_doctor_workflow()
        
        # Final results
        print("\n" + "=" * 80)
        print("📊 FINAL TEST RESULTS")
        print("=" * 80)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if workflow_success:
            print("\n🎉 NEW DOCTOR WORKFLOW TESTING: SUCCESS")
            print("All key functionality working as expected after removing accept requirement")
        else:
            print("\n❌ NEW DOCTOR WORKFLOW TESTING: FAILED")
            print("Some issues detected that need to be addressed")
        
        return workflow_success

if __name__ == "__main__":
    tester = NewDoctorWorkflowTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)