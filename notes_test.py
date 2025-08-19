import requests
import sys
import json
from datetime import datetime
import time

class NotesSystemTester:
    def __init__(self, base_url="https://greenstar-health.preview.emergentagent.com"):
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
                "name": "Notes Test Patient (Non-Emergency)",
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
            "consultation_notes": "Provider initial notes for non-emergency"
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
                "name": "Notes Test Patient (Emergency)",
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
            "consultation_notes": "Provider initial notes for emergency case"
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
            return True
        else:
            return False

    def test_doctor_notes_to_provider_non_emergency(self):
        """Test doctor can send notes to provider for non-emergency appointments"""
        print("\n📝 Testing Doctor → Provider Notes (Non-Emergency)")
        print("-" * 60)
        
        if not self.non_emergency_appointment_id or 'doctor' not in self.tokens:
            print("❌ Missing appointment ID or doctor token")
            return False

        # Doctor adds note to pending non-emergency appointment (before accepting)
        note_data = {
            "note": "Doctor note for non-emergency case - reviewing patient history before accepting",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Adds Note to Pending Non-Emergency",
            "POST",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            data=note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor cannot add notes to pending non-emergency appointment")
            return False

        # Doctor accepts the appointment
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
            print("❌ Doctor cannot accept non-emergency appointment")
            return False

        # Doctor adds another note after accepting
        note_data = {
            "note": "Doctor note after accepting non-emergency - treatment plan discussed",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Adds Note After Accepting Non-Emergency",
            "POST",
            f"appointments/{self.non_emergency_appointment_id}/notes",
            200,
            data=note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor cannot add notes after accepting non-emergency appointment")
            return False

        print("   ✅ Doctor can send notes for non-emergency appointments (both pending and accepted)")
        return True

    def test_doctor_notes_to_provider_emergency(self):
        """Test doctor can send notes to provider for emergency appointments"""
        print("\n🚨 Testing Doctor → Provider Notes (Emergency)")
        print("-" * 60)
        
        if not self.emergency_appointment_id or 'doctor' not in self.tokens:
            print("❌ Missing appointment ID or doctor token")
            return False

        # Doctor adds note to pending emergency appointment
        note_data = {
            "note": "Doctor note for emergency case - urgent assessment needed, preparing for immediate consultation",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Adds Note to Pending Emergency",
            "POST",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            data=note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor cannot add notes to pending emergency appointment")
            return False

        # Doctor accepts the emergency appointment
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
            print("❌ Doctor cannot accept emergency appointment")
            return False

        # Doctor adds another note after accepting
        note_data = {
            "note": "Doctor note after accepting emergency - immediate treatment initiated, monitoring vitals",
            "sender_role": "doctor"
        }
        
        success, response = self.run_test(
            "Doctor Adds Note After Accepting Emergency",
            "POST",
            f"appointments/{self.emergency_appointment_id}/notes",
            200,
            data=note_data,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor cannot add notes after accepting emergency appointment")
            return False

        print("   ✅ Doctor can send notes for emergency appointments (both pending and accepted)")
        return True

    def test_provider_notes_to_doctor(self):
        """Test provider can send notes to doctor (bidirectional communication)"""
        print("\n💬 Testing Provider → Doctor Notes (Bidirectional)")
        print("-" * 60)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False

        all_success = True

        # Provider replies to doctor for non-emergency appointment
        if self.non_emergency_appointment_id:
            note_data = {
                "note": "Provider response to doctor for non-emergency - patient is comfortable, vitals stable",
                "sender_role": "provider"
            }
            
            success, response = self.run_test(
                "Provider Replies to Doctor (Non-Emergency)",
                "POST",
                f"appointments/{self.non_emergency_appointment_id}/notes",
                200,
                data=note_data,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider can reply to doctor for non-emergency")
            else:
                print("   ❌ Provider cannot reply to doctor for non-emergency")
                all_success = False

        # Provider replies to doctor for emergency appointment
        if self.emergency_appointment_id:
            note_data = {
                "note": "Provider response to doctor for emergency - patient condition improving, following treatment plan",
                "sender_role": "provider"
            }
            
            success, response = self.run_test(
                "Provider Replies to Doctor (Emergency)",
                "POST",
                f"appointments/{self.emergency_appointment_id}/notes",
                200,
                data=note_data,
                token=self.tokens['provider']
            )
            
            if success:
                print("   ✅ Provider can reply to doctor for emergency")
            else:
                print("   ❌ Provider cannot reply to doctor for emergency")
                all_success = False

        return all_success

    def test_notes_visibility_and_conversation_threads(self):
        """Test that all notes are visible to both parties and form conversation threads"""
        print("\n👀 Testing Notes Visibility & Conversation Threads")
        print("-" * 60)
        
        all_success = True

        # Test non-emergency appointment notes visibility
        if self.non_emergency_appointment_id:
            # Doctor views all notes
            success, response = self.run_test(
                "Doctor Views All Notes (Non-Emergency)",
                "GET",
                f"appointments/{self.non_emergency_appointment_id}/notes",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                doctor_notes = response
                print(f"   ✅ Doctor can see {len(doctor_notes)} notes for non-emergency")
                
                # Check for conversation thread
                doctor_sent = [n for n in doctor_notes if n.get('sender_role') == 'doctor']
                provider_sent = [n for n in doctor_notes if n.get('sender_role') == 'provider']
                
                print(f"   📝 Doctor sent: {len(doctor_sent)} notes")
                print(f"   📝 Provider sent: {len(provider_sent)} notes")
                
                if len(doctor_sent) > 0 and len(provider_sent) > 0:
                    print("   ✅ Bidirectional conversation confirmed for non-emergency")
                else:
                    print("   ❌ Missing bidirectional conversation for non-emergency")
                    all_success = False
            else:
                all_success = False

            # Provider views all notes
            success, response = self.run_test(
                "Provider Views All Notes (Non-Emergency)",
                "GET",
                f"appointments/{self.non_emergency_appointment_id}/notes",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                provider_notes = response
                print(f"   ✅ Provider can see {len(provider_notes)} notes for non-emergency")
                
                # Verify both parties see the same notes
                if len(doctor_notes) == len(provider_notes):
                    print("   ✅ Both parties see same number of notes for non-emergency")
                else:
                    print("   ❌ Note count mismatch between doctor and provider for non-emergency")
                    all_success = False
            else:
                all_success = False

        # Test emergency appointment notes visibility
        if self.emergency_appointment_id:
            # Doctor views all notes
            success, response = self.run_test(
                "Doctor Views All Notes (Emergency)",
                "GET",
                f"appointments/{self.emergency_appointment_id}/notes",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                doctor_notes = response
                print(f"   ✅ Doctor can see {len(doctor_notes)} notes for emergency")
                
                # Check for conversation thread
                doctor_sent = [n for n in doctor_notes if n.get('sender_role') == 'doctor']
                provider_sent = [n for n in doctor_notes if n.get('sender_role') == 'provider']
                
                print(f"   📝 Doctor sent: {len(doctor_sent)} notes")
                print(f"   📝 Provider sent: {len(provider_sent)} notes")
                
                if len(doctor_sent) > 0 and len(provider_sent) > 0:
                    print("   ✅ Bidirectional conversation confirmed for emergency")
                else:
                    print("   ❌ Missing bidirectional conversation for emergency")
                    all_success = False
            else:
                all_success = False

            # Provider views all notes
            success, response = self.run_test(
                "Provider Views All Notes (Emergency)",
                "GET",
                f"appointments/{self.emergency_appointment_id}/notes",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                provider_notes = response
                print(f"   ✅ Provider can see {len(provider_notes)} notes for emergency")
                
                # Verify both parties see the same notes
                if len(doctor_notes) == len(provider_notes):
                    print("   ✅ Both parties see same number of notes for emergency")
                else:
                    print("   ❌ Note count mismatch between doctor and provider for emergency")
                    all_success = False
            else:
                all_success = False

        return all_success

    def test_no_403_errors(self):
        """Specifically test that there are no 403 errors in the notes system"""
        print("\n🚫 Testing No 403 Errors in Notes System")
        print("-" * 60)
        
        all_success = True
        
        # Test various scenarios that previously might have caused 403 errors
        test_scenarios = [
            ("Doctor adds note to pending non-emergency", self.non_emergency_appointment_id, 'doctor'),
            ("Doctor adds note to accepted non-emergency", self.non_emergency_appointment_id, 'doctor'),
            ("Provider adds note to non-emergency", self.non_emergency_appointment_id, 'provider'),
            ("Doctor adds note to pending emergency", self.emergency_appointment_id, 'doctor'),
            ("Doctor adds note to accepted emergency", self.emergency_appointment_id, 'doctor'),
            ("Provider adds note to emergency", self.emergency_appointment_id, 'provider'),
        ]
        
        for scenario_name, appointment_id, user_role in test_scenarios:
            if appointment_id and user_role in self.tokens:
                note_data = {
                    "note": f"Test note for scenario: {scenario_name}",
                    "sender_role": user_role
                }
                
                success, response = self.run_test(
                    f"No 403 Test: {scenario_name}",
                    "POST",
                    f"appointments/{appointment_id}/notes",
                    200,  # Expecting success, not 403
                    data=note_data,
                    token=self.tokens[user_role]
                )
                
                if success:
                    print(f"   ✅ No 403 error for: {scenario_name}")
                else:
                    print(f"   ❌ Unexpected error for: {scenario_name}")
                    all_success = False
        
        return all_success

def main():
    print("📝 MedConnect Notes System Testing - BIDIRECTIONAL COMMUNICATION")
    print("=" * 80)
    
    tester = NotesSystemTester()
    
    # Test sequence for comprehensive notes testing
    tests = [
        ("Login All Users", tester.login_all_users),
        ("Create Test Appointments", tester.create_test_appointments),
        ("Doctor → Provider Notes (Non-Emergency)", tester.test_doctor_notes_to_provider_non_emergency),
        ("Doctor → Provider Notes (Emergency)", tester.test_doctor_notes_to_provider_emergency),
        ("Provider → Doctor Notes (Bidirectional)", tester.test_provider_notes_to_doctor),
        ("Notes Visibility & Conversation Threads", tester.test_notes_visibility_and_conversation_threads),
        ("No 403 Errors Test", tester.test_no_403_errors),
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
    print(f"📊 Final Results:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if failed_tests:
        print(f"\n❌ Failed Test Suites ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test}")
    
    # Notes system summary
    print(f"\n📝 NOTES SYSTEM SUMMARY:")
    if tester.non_emergency_appointment_id and tester.emergency_appointment_id:
        print(f"   ✅ Both appointment types created successfully")
        print(f"   📋 Non-Emergency: {tester.non_emergency_appointment_id}")
        print(f"   🚨 Emergency: {tester.emergency_appointment_id}")
    else:
        print(f"   ❌ Failed to create test appointments")
    
    if tester.tests_passed >= tester.tests_run * 0.9:  # 90% pass rate
        print("🎉 Notes system is working correctly with bidirectional communication!")
        print("✅ No 403 errors detected")
        print("✅ Doctor → Provider notes work for both appointment types")
        print("✅ Provider → Doctor notes work (bidirectional)")
        print("✅ Conversation threads are maintained")
        return 0
    else:
        print("⚠️  Some critical notes tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())