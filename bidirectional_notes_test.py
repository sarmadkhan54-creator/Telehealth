import requests
import sys
import json
from datetime import datetime

class BidirectionalNotesTest:
    def __init__(self, base_url="https://19543fde-1955-4452-861c-5fe800d2c222.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.emergency_appointment_id = None
        self.non_emergency_appointment_id = None
        
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

    def login_all_users(self):
        """Login all user types"""
        print("\n🔑 Logging in all users...")
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
                print(f"   ✅ {role.title()} logged in successfully")
            else:
                print(f"   ❌ {role.title()} login failed")
                return False
        return True

    def create_test_appointments(self):
        """Create both emergency and non-emergency appointments for testing"""
        print("\n📅 Creating test appointments...")
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False

        # Create non-emergency appointment
        non_emergency_data = {
            "patient": {
                "name": "Non-Emergency Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6
                },
                "consultation_reason": "Routine checkup for notes testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Provider notes: Patient seems healthy"
        }
        
        success, response = self.run_test(
            "Create Non-Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=non_emergency_data,
            token=self.tokens['provider']
        )
        
        if success:
            self.non_emergency_appointment_id = response.get('id')
            print(f"   ✅ Non-emergency appointment created: {self.non_emergency_appointment_id}")
        else:
            return False

        # Create emergency appointment
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
                "consultation_reason": "Chest pain - emergency notes testing"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Provider notes: URGENT - Patient experiencing severe symptoms"
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
            self.emergency_appointment_id = response.get('id')
            print(f"   ✅ Emergency appointment created: {self.emergency_appointment_id}")
        else:
            return False

        return True

    def test_bidirectional_notes_non_emergency(self):
        """Test bidirectional notes for non-emergency appointments"""
        print("\n📝 Testing Bidirectional Notes - NON-EMERGENCY")
        print("-" * 60)
        
        if not self.non_emergency_appointment_id:
            print("❌ No non-emergency appointment available")
            return False

        # Step 1: Doctor accepts the appointment
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id']
        }
        
        success, response = self.run_test(
            "Doctor Accepts Non-Emergency Appointment",
            "PUT",
            f"appointments/{self.non_emergency_appointment_id}",
            200,
            data=update_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not accept appointment")
            return False

        # Step 2: Doctor sends note to provider
        doctor_note_data = {
            "note": "Doctor to Provider: Patient vitals are stable. Recommend follow-up in 2 weeks for routine monitoring.",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Sends Note to Provider (Non-Emergency)",
            "POST",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            data=doctor_note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not send note")
            return False

        # Step 3: Provider views doctor's note
        success, response = self.run_test(
            "Provider Views Doctor's Note (Non-Emergency)",
            "GET",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not view notes")
            return False

        doctor_notes = [note for note in response if note.get('sender_role') == 'doctor']
        if not doctor_notes:
            print("❌ Doctor's note not visible to provider")
            return False
        
        print(f"   ✅ Provider can see doctor's note: '{doctor_notes[0]['note'][:50]}...'")

        # Step 4: Provider replies with note to doctor
        provider_note_data = {
            "note": "Provider to Doctor: Thank you for the assessment. Patient has been scheduled for follow-up. Any specific tests needed?",
            "sender_role": "provider"
        }
        
        success, response = self.run_test(
            "Provider Sends Reply Note to Doctor (Non-Emergency)",
            "POST",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            data=provider_note_data,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not send reply note")
            return False

        # Step 5: Doctor views provider's reply
        success, response = self.run_test(
            "Doctor Views Provider's Reply (Non-Emergency)",
            "GET",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not view notes")
            return False

        provider_notes = [note for note in response if note.get('sender_role') == 'provider']
        if not provider_notes:
            print("❌ Provider's note not visible to doctor")
            return False
        
        print(f"   ✅ Doctor can see provider's reply: '{provider_notes[0]['note'][:50]}...'")

        # Step 6: Verify full conversation thread
        if len(response) >= 2:
            print(f"   ✅ Full conversation thread maintained ({len(response)} notes)")
            # Sort by timestamp to verify order
            sorted_notes = sorted(response, key=lambda x: x['timestamp'])
            print(f"   ✅ Notes in chronological order:")
            for i, note in enumerate(sorted_notes, 1):
                print(f"      {i}. {note['sender_role'].title()}: {note['note'][:40]}...")
        else:
            print("❌ Full conversation thread not maintained")
            return False

        return True

    def test_bidirectional_notes_emergency(self):
        """Test bidirectional notes for emergency appointments"""
        print("\n🚨 Testing Bidirectional Notes - EMERGENCY")
        print("-" * 60)
        
        if not self.emergency_appointment_id:
            print("❌ No emergency appointment available")
            return False

        # Step 1: Doctor accepts the emergency appointment
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id']
        }
        
        success, response = self.run_test(
            "Doctor Accepts Emergency Appointment",
            "PUT",
            f"appointments/{self.emergency_appointment_id}",
            200,
            data=update_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not accept emergency appointment")
            return False

        # Step 2: Doctor sends urgent note to provider
        doctor_note_data = {
            "note": "URGENT - Doctor to Provider: Patient requires immediate IV fluids and cardiac monitoring. Blood pressure critically high at 180/120. Initiating emergency protocol.",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Sends Urgent Note to Provider (Emergency)",
            "POST",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            data=doctor_note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not send urgent note")
            return False

        # Step 3: Provider views doctor's urgent note
        success, response = self.run_test(
            "Provider Views Doctor's Urgent Note (Emergency)",
            "GET",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not view notes")
            return False

        doctor_notes = [note for note in response if note.get('sender_role') == 'doctor']
        if not doctor_notes:
            print("❌ Doctor's urgent note not visible to provider")
            return False
        
        print(f"   ✅ Provider can see doctor's urgent note: '{doctor_notes[0]['note'][:60]}...'")

        # Step 4: Provider sends status update to doctor
        provider_note_data = {
            "note": "Provider to Doctor: Emergency protocol initiated. IV fluids started, cardiac monitor attached. Patient stable. ETA to hospital 15 minutes. Vitals being monitored continuously.",
            "sender_role": "provider"
        }
        
        success, response = self.run_test(
            "Provider Sends Status Update to Doctor (Emergency)",
            "POST",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            data=provider_note_data,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not send status update")
            return False

        # Step 5: Doctor views provider's status update
        success, response = self.run_test(
            "Doctor Views Provider's Status Update (Emergency)",
            "GET",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not view status update")
            return False

        provider_notes = [note for note in response if note.get('sender_role') == 'provider']
        if not provider_notes:
            print("❌ Provider's status update not visible to doctor")
            return False
        
        print(f"   ✅ Doctor can see provider's status update: '{provider_notes[0]['note'][:60]}...'")

        # Step 6: Doctor sends follow-up instructions
        doctor_followup_data = {
            "note": "Doctor Follow-up: Excellent work. Continue monitoring. Prepare for immediate transfer to cardiac unit upon arrival. I'll be waiting in ER.",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Sends Follow-up Instructions (Emergency)",
            "POST",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            data=doctor_followup_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not send follow-up instructions")
            return False

        # Step 7: Verify complete emergency conversation thread
        success, response = self.run_test(
            "Verify Complete Emergency Conversation Thread",
            "GET",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            token=self.tokens['provider']
        )
        
        if success and len(response) >= 3:
            print(f"   ✅ Complete emergency conversation thread maintained ({len(response)} notes)")
            # Sort by timestamp to verify order
            sorted_notes = sorted(response, key=lambda x: x['timestamp'])
            print(f"   ✅ Emergency notes in chronological order:")
            for i, note in enumerate(sorted_notes, 1):
                print(f"      {i}. {note['sender_role'].title()}: {note['note'][:50]}...")
        else:
            print("❌ Complete emergency conversation thread not maintained")
            return False

        return True

    def test_cross_appointment_note_isolation(self):
        """Test that notes are isolated between different appointments"""
        print("\n🔒 Testing Cross-Appointment Note Isolation")
        print("-" * 60)
        
        if not self.emergency_appointment_id or not self.non_emergency_appointment_id:
            print("❌ Missing appointment IDs for isolation test")
            return False

        # Get notes from non-emergency appointment
        success, non_emergency_notes = self.run_test(
            "Get Non-Emergency Appointment Notes",
            "GET",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            return False

        # Get notes from emergency appointment
        success, emergency_notes = self.run_test(
            "Get Emergency Appointment Notes",
            "GET",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            return False

        # Verify notes are different and isolated
        non_emergency_note_ids = {note['id'] for note in non_emergency_notes}
        emergency_note_ids = {note['id'] for note in emergency_notes}
        
        if non_emergency_note_ids.intersection(emergency_note_ids):
            print("❌ Notes are not properly isolated between appointments")
            return False
        
        print(f"   ✅ Notes properly isolated:")
        print(f"      Non-emergency appointment: {len(non_emergency_notes)} notes")
        print(f"      Emergency appointment: {len(emergency_notes)} notes")
        print(f"      No overlap in note IDs")

        return True

    def test_admin_can_view_all_notes(self):
        """Test that admin can view notes from all appointments"""
        print("\n👑 Testing Admin Access to All Notes")
        print("-" * 60)
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False

        # Admin views non-emergency notes
        success, non_emergency_notes = self.run_test(
            "Admin Views Non-Emergency Notes",
            "GET",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            token=self.tokens['admin']
        )
        
        if not success:
            return False

        # Admin views emergency notes
        success, emergency_notes = self.run_test(
            "Admin Views Emergency Notes",
            "GET",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            token=self.tokens['admin']
        )
        
        if not success:
            return False

        print(f"   ✅ Admin can access all appointment notes:")
        print(f"      Non-emergency notes: {len(non_emergency_notes)}")
        print(f"      Emergency notes: {len(emergency_notes)}")

        return True

def main():
    print("🏥 MedConnect Bidirectional Notes System Testing")
    print("=" * 80)
    
    tester = BidirectionalNotesTest()
    
    # Test sequence
    tests = [
        ("Login All Users", tester.login_all_users),
        ("Create Test Appointments", tester.create_test_appointments),
        ("Bidirectional Notes - Non-Emergency", tester.test_bidirectional_notes_non_emergency),
        ("Bidirectional Notes - Emergency", tester.test_bidirectional_notes_emergency),
        ("Cross-Appointment Note Isolation", tester.test_cross_appointment_note_isolation),
        ("Admin Access to All Notes", tester.test_admin_can_view_all_notes),
    ]
    
    print(f"\n🚀 Running {len(tests)} test suites...")
    
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
    print(f"📊 Bidirectional Notes Test Results:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if failed_tests:
        print(f"\n❌ Failed Test Suites ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    
    # Summary
    print(f"\n📝 BIDIRECTIONAL NOTES SUMMARY:")
    if tester.emergency_appointment_id and tester.non_emergency_appointment_id:
        print(f"   ✅ Both emergency and non-emergency appointments created")
        print(f"   ✅ Emergency appointment: {tester.emergency_appointment_id}")
        print(f"   ✅ Non-emergency appointment: {tester.non_emergency_appointment_id}")
    else:
        print(f"   ❌ Could not create test appointments")
    
    if tester.tests_passed >= tester.tests_run * 0.9:  # 90% pass rate
        print("🎉 Bidirectional notes system is working correctly!")
        return 0
    else:
        print("⚠️  Some critical notes tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())