#!/usr/bin/env python3
"""
Video Call Scenario Test for Provider Testing
==============================================

This script creates a complete working video call scenario for the provider to test:
1. Admin creates a new appointment with demo_provider as the provider
2. Doctor accepts that appointment (sets status to "accepted")
3. Provider can see the accepted appointment and test "Join Call" functionality
4. Tests the complete video call workflow

Credentials:
- Provider: demo_provider/Demo123!
- Doctor: demo_doctor/Demo123!
- Admin: demo_admin/Demo123!
"""

import requests
import sys
import json
from datetime import datetime

class VideoCallScenarioTester:
    def __init__(self, base_url="https://medconnect-live-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.scenario_appointment_id = None
        
        # Demo credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make API request with proper error handling"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            if response.status_code == expected_status:
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Request failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Request error: {str(e)}")
            return False, {}

    def step_1_login_all_users(self):
        """Step 1: Login as all three user types"""
        print("\n🔑 STEP 1: Login as Admin, Doctor, and Provider")
        print("-" * 60)
        
        for role, credentials in self.demo_credentials.items():
            print(f"   Logging in as {role}...")
            success, response = self.make_request("POST", "login", data=credentials)
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   ✅ {role.title()} login successful")
                print(f"      User ID: {response['user'].get('id')}")
                print(f"      Name: {response['user'].get('full_name')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                return False
        
        print(f"\n✅ All users logged in successfully!")
        return True

    def step_2_admin_creates_appointment(self):
        """Step 2: Admin creates appointment with demo_provider as provider"""
        print("\n📅 STEP 2: Admin creates appointment for demo_provider")
        print("-" * 60)
        
        if 'admin' not in self.tokens:
            print("❌ Admin token not available")
            return False

        # Create appointment data with demo_provider as the provider
        appointment_data = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 42,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "140/90",
                    "heart_rate": 88,
                    "temperature": 99.2,
                    "oxygen_saturation": "97%"
                },
                "consultation_reason": "Persistent headaches and dizziness for the past week"
            },
            "appointment_type": "emergency",
            "consultation_notes": "Patient reports severe headaches with visual disturbances. Requires immediate medical attention."
        }

        # First, we need to login as provider to create the appointment (since only providers can create appointments)
        print("   Creating appointment as provider (system requirement)...")
        success, response = self.make_request(
            "POST", 
            "appointments", 
            data=appointment_data, 
            token=self.tokens['provider']
        )
        
        if success:
            self.scenario_appointment_id = response.get('id')
            print(f"   ✅ Appointment created successfully!")
            print(f"      Appointment ID: {self.scenario_appointment_id}")
            print(f"      Patient: {appointment_data['patient']['name']}")
            print(f"      Type: {appointment_data['appointment_type']}")
            print(f"      Provider: demo_provider")
            print(f"      Status: pending (waiting for doctor acceptance)")
            return True
        else:
            print("   ❌ Failed to create appointment")
            return False

    def step_3_doctor_accepts_appointment(self):
        """Step 3: Doctor accepts the appointment"""
        print("\n👨‍⚕️ STEP 3: Doctor accepts the appointment")
        print("-" * 60)
        
        if not self.scenario_appointment_id or 'doctor' not in self.tokens:
            print("❌ Missing appointment ID or doctor token")
            return False

        # Doctor accepts appointment and assigns themselves
        update_data = {
            "status": "accepted",
            "doctor_id": self.users['doctor']['id'],
            "doctor_notes": "Emergency case reviewed. Patient symptoms suggest possible hypertension. Scheduling immediate consultation."
        }

        print("   Doctor accepting appointment...")
        success, response = self.make_request(
            "PUT", 
            f"appointments/{self.scenario_appointment_id}", 
            data=update_data, 
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ Appointment accepted by doctor!")
            print(f"      Doctor: {self.users['doctor']['full_name']}")
            print(f"      Status: accepted")
            print(f"      Doctor Notes: {update_data['doctor_notes']}")
            return True
        else:
            print("   ❌ Doctor failed to accept appointment")
            return False

    def step_4_verify_provider_can_see_accepted_appointment(self):
        """Step 4: Verify provider can see the accepted appointment"""
        print("\n👩‍⚕️ STEP 4: Verify provider can see accepted appointment")
        print("-" * 60)
        
        if 'provider' not in self.tokens:
            print("❌ Provider token not available")
            return False

        print("   Fetching provider's appointments...")
        success, response = self.make_request(
            "GET", 
            "appointments", 
            token=self.tokens['provider']
        )
        
        if success:
            appointments = response
            accepted_appointments = [apt for apt in appointments if apt.get('status') == 'accepted']
            
            print(f"   ✅ Provider can see {len(appointments)} total appointments")
            print(f"   ✅ Found {len(accepted_appointments)} accepted appointments")
            
            # Find our scenario appointment
            scenario_apt = None
            for apt in appointments:
                if apt.get('id') == self.scenario_appointment_id:
                    scenario_apt = apt
                    break
            
            if scenario_apt:
                print(f"   ✅ Scenario appointment found:")
                print(f"      ID: {scenario_apt.get('id')}")
                print(f"      Status: {scenario_apt.get('status')}")
                print(f"      Patient: {scenario_apt.get('patient', {}).get('name')}")
                print(f"      Doctor: {scenario_apt.get('doctor', {}).get('full_name') if scenario_apt.get('doctor') else 'None'}")
                print(f"      Type: {scenario_apt.get('appointment_type')}")
                
                if scenario_apt.get('status') == 'accepted' and scenario_apt.get('doctor'):
                    print(f"   🎉 PERFECT! Provider can see accepted appointment with assigned doctor")
                    print(f"   📞 Provider should now see 'Join Call' button for this appointment")
                    return True
                else:
                    print(f"   ⚠️  Appointment status: {scenario_apt.get('status')}")
                    return False
            else:
                print("   ❌ Scenario appointment not found in provider's list")
                return False
        else:
            print("   ❌ Failed to fetch provider appointments")
            return False

    def step_5_test_video_call_workflow(self):
        """Step 5: Test the complete video call workflow"""
        print("\n📹 STEP 5: Test complete video call workflow")
        print("-" * 60)
        
        if not self.scenario_appointment_id:
            print("❌ No scenario appointment available")
            return False

        # Test 1: Provider starts video call
        print("   🎬 Testing provider starting video call...")
        success, response = self.make_request(
            "POST", 
            f"video-call/start/{self.scenario_appointment_id}", 
            token=self.tokens['provider']
        )
        
        if success:
            provider_session_token = response.get('session_token')
            print(f"   ✅ Provider successfully started video call")
            print(f"      Session Token: {provider_session_token}")
        else:
            print("   ❌ Provider failed to start video call")
            return False

        # Test 2: Doctor joins the call
        print("   👨‍⚕️ Testing doctor joining the call...")
        success, response = self.make_request(
            "GET", 
            f"video-call/join/{provider_session_token}", 
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ Doctor successfully joined the video call")
            print(f"      Call participants: Provider + Doctor")
        else:
            print("   ❌ Doctor failed to join video call")
            return False

        # Test 3: Doctor starts a new call
        print("   🎬 Testing doctor starting video call...")
        success, response = self.make_request(
            "POST", 
            f"video-call/start/{self.scenario_appointment_id}", 
            token=self.tokens['doctor']
        )
        
        if success:
            doctor_session_token = response.get('session_token')
            print(f"   ✅ Doctor successfully started video call")
            print(f"      Session Token: {doctor_session_token}")
        else:
            print("   ❌ Doctor failed to start video call")
            return False

        # Test 4: Provider joins doctor's call
        print("   👩‍⚕️ Testing provider joining doctor's call...")
        success, response = self.make_request(
            "GET", 
            f"video-call/join/{doctor_session_token}", 
            token=self.tokens['provider']
        )
        
        if success:
            print(f"   ✅ Provider successfully joined doctor's video call")
            print(f"      Call participants: Doctor + Provider")
        else:
            print("   ❌ Provider failed to join doctor's video call")
            return False

        print(f"\n🎉 COMPLETE VIDEO CALL WORKFLOW TESTED SUCCESSFULLY!")
        return True

    def step_6_final_verification(self):
        """Step 6: Final verification and summary"""
        print("\n✅ STEP 6: Final verification and summary")
        print("-" * 60)
        
        # Get final appointment details
        if self.scenario_appointment_id and 'provider' in self.tokens:
            success, response = self.make_request(
                "GET", 
                f"appointments/{self.scenario_appointment_id}", 
                token=self.tokens['provider']
            )
            
            if success:
                apt = response
                print(f"   📋 FINAL APPOINTMENT STATUS:")
                print(f"      ID: {apt.get('id')}")
                print(f"      Status: {apt.get('status')}")
                print(f"      Patient: {apt.get('patient', {}).get('name')}")
                print(f"      Provider: {apt.get('provider', {}).get('full_name')}")
                print(f"      Doctor: {apt.get('doctor', {}).get('full_name')}")
                print(f"      Type: {apt.get('appointment_type')}")
                
                print(f"\n   🎯 PROVIDER TESTING INSTRUCTIONS:")
                print(f"      1. Login as: demo_provider / Demo123!")
                print(f"      2. Look for appointment with patient: {apt.get('patient', {}).get('name')}")
                print(f"      3. Status should show: 'accepted'")
                print(f"      4. Doctor assigned: {apt.get('doctor', {}).get('full_name')}")
                print(f"      5. Click 'Join Call' button to test video call functionality")
                print(f"      6. Video call interface should load with all controls")
                
                return True
        
        return False

    def run_complete_scenario(self):
        """Run the complete video call scenario setup"""
        print("🏥 VIDEO CALL SCENARIO SETUP FOR PROVIDER TESTING")
        print("=" * 80)
        print("Creating a working video call scenario for demo_provider to test...")
        print("This will set up an accepted appointment with assigned doctor.")
        
        steps = [
            ("Login All Users", self.step_1_login_all_users),
            ("Admin Creates Appointment", self.step_2_admin_creates_appointment),
            ("Doctor Accepts Appointment", self.step_3_doctor_accepts_appointment),
            ("Verify Provider Can See Accepted Appointment", self.step_4_verify_provider_can_see_accepted_appointment),
            ("Test Video Call Workflow", self.step_5_test_video_call_workflow),
            ("Final Verification", self.step_6_final_verification)
        ]
        
        failed_steps = []
        for step_name, step_func in steps:
            try:
                result = step_func()
                if not result:
                    failed_steps.append(step_name)
                    print(f"\n❌ STEP FAILED: {step_name}")
            except Exception as e:
                failed_steps.append(step_name)
                print(f"\n❌ STEP ERROR: {step_name} - {str(e)}")
        
        # Final summary
        print(f"\n{'='*80}")
        print(f"📊 SCENARIO SETUP RESULTS:")
        
        if not failed_steps:
            print(f"✅ ALL STEPS COMPLETED SUCCESSFULLY!")
            print(f"\n🎉 VIDEO CALL SCENARIO IS READY FOR PROVIDER TESTING!")
            print(f"\n📱 PROVIDER CAN NOW:")
            print(f"   • Login as demo_provider/Demo123!")
            print(f"   • See accepted appointment with assigned doctor")
            print(f"   • Click 'Join Call' button to test video functionality")
            print(f"   • Test complete video call workflow")
            
            if self.scenario_appointment_id:
                print(f"\n📋 SCENARIO APPOINTMENT DETAILS:")
                print(f"   • Appointment ID: {self.scenario_appointment_id}")
                print(f"   • Status: accepted")
                print(f"   • Provider: demo_provider")
                print(f"   • Doctor: demo_doctor")
                print(f"   • Type: emergency")
            
            return True
        else:
            print(f"❌ {len(failed_steps)} STEPS FAILED:")
            for step in failed_steps:
                print(f"   - {step}")
            return False

def main():
    tester = VideoCallScenarioTester()
    success = tester.run_complete_scenario()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())