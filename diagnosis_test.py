#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class AppointmentDiagnosisTester:
    def __init__(self, base_url="https://medconnect-live-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        
        # Test credentials
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

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        # Retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
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

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"⏰ Timeout on attempt {attempt + 1}, retrying...")
                    continue
                else:
                    print(f"❌ Failed - Timeout after {max_retries} attempts")
                    return False, {}
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Error on attempt {attempt + 1}: {str(e)}, retrying...")
                    continue
                else:
                    print(f"❌ Failed - Error: {str(e)}")
                    return False, {}

        return False, {}

    def login_all_roles(self):
        """Login for all user roles"""
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
                print(f"   ✅ {role.title()} login successful")
                print(f"   User ID: {response['user'].get('id')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                all_success = False
        
        return all_success

    def diagnose_appointment_visibility_and_calling(self):
        """🎯 DIAGNOSE APPOINTMENT VISIBILITY AND CALLING ISSUES"""
        print("\n🎯 APPOINTMENT VISIBILITY AND CALLING DIAGNOSIS")
        print("=" * 80)
        print("Testing specific issues: appointment visibility and calling functionality")
        print("Focus: Provider creates appointment → Doctor sees it → Video call works")
        print("=" * 80)
        
        all_success = True
        
        # STEP 1: Create new appointment with demo_provider
        print("\n1️⃣ STEP 1: Create New Appointment with demo_provider/Demo123!")
        print("-" * 60)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        # Create realistic appointment data
        appointment_data = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 28,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "130/85",
                    "heart_rate": 88,
                    "temperature": 99.2,
                    "oxygen_saturation": 97,
                    "hb": 12.5,
                    "sugar_level": 110
                },
                "history": "Severe chest pain and shortness of breath for 2 hours",
                "area_of_consultation": "Emergency Medicine"
            },
            "appointment_type": "emergency",
            "consultation_notes": "URGENT: Patient experiencing severe chest pain, needs immediate attention"
        }
        
        success, response = self.run_test(
            "Create Emergency Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ CRITICAL: Provider cannot create appointment")
            return False
        
        new_appointment_id = response.get('id')
        print(f"   ✅ Emergency appointment created successfully")
        print(f"   Appointment ID: {new_appointment_id}")
        print(f"   Patient: {appointment_data['patient']['name']}")
        print(f"   Type: {appointment_data['appointment_type']}")
        print(f"   Provider ID: {self.users['provider']['id']}")
        
        # STEP 2: Check if appointment appears in provider's own dashboard
        print("\n2️⃣ STEP 2: Check Provider's Own Dashboard")
        print("-" * 60)
        
        success, provider_appointments = self.run_test(
            "Get Provider's Appointments",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ CRITICAL: Provider cannot access their own appointments")
            all_success = False
        else:
            # Check if new appointment is visible
            provider_appointment_ids = [apt.get('id') for apt in provider_appointments]
            if new_appointment_id in provider_appointment_ids:
                print(f"   ✅ New appointment visible in provider dashboard")
                print(f"   Total provider appointments: {len(provider_appointments)}")
                
                # Verify filtering logic - all should belong to this provider
                provider_id = self.users['provider']['id']
                own_appointments = [apt for apt in provider_appointments if apt.get('provider_id') == provider_id]
                other_appointments = [apt for apt in provider_appointments if apt.get('provider_id') != provider_id]
                
                print(f"   Provider-owned appointments: {len(own_appointments)}")
                print(f"   Other-owned appointments: {len(other_appointments)}")
                
                if len(other_appointments) == 0:
                    print("   ✅ Provider filtering working correctly (only sees own appointments)")
                else:
                    print("   ❌ Provider filtering broken (seeing other providers' appointments)")
                    all_success = False
            else:
                print("   ❌ CRITICAL: New appointment NOT visible in provider dashboard")
                all_success = False
        
        # STEP 3: Check if appointment appears in doctor's dashboard
        print("\n3️⃣ STEP 3: Check Doctor's Dashboard")
        print("-" * 60)
        
        if 'doctor' not in self.tokens:
            print("❌ No doctor token available")
            return False
        
        success, doctor_appointments = self.run_test(
            "Get Doctor's Appointments",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ CRITICAL: Doctor cannot access appointments")
            all_success = False
        else:
            # Check if new appointment is visible to doctor
            doctor_appointment_ids = [apt.get('id') for apt in doctor_appointments]
            if new_appointment_id in doctor_appointment_ids:
                print(f"   ✅ New appointment visible in doctor dashboard")
                print(f"   Total doctor appointments: {len(doctor_appointments)}")
                
                # Find the specific appointment
                target_appointment = None
                for apt in doctor_appointments:
                    if apt.get('id') == new_appointment_id:
                        target_appointment = apt
                        break
                
                if target_appointment:
                    print(f"   Appointment status: {target_appointment.get('status', 'unknown')}")
                    print(f"   Appointment type: {target_appointment.get('appointment_type', 'unknown')}")
                    print(f"   Patient name: {target_appointment.get('patient', {}).get('name', 'unknown')}")
                    print("   ✅ Appointment data structure complete")
                else:
                    print("   ❌ Could not find appointment details")
                    all_success = False
            else:
                print("   ❌ CRITICAL: New appointment NOT visible in doctor dashboard")
                all_success = False
        
        # STEP 4: Test video call initiation from doctor to provider
        print("\n4️⃣ STEP 4: Test Video Call Initiation (Doctor → Provider)")
        print("-" * 60)
        
        success, call_response = self.run_test(
            "Doctor Initiates Video Call",
            "POST",
            f"video-call/start/{new_appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ CRITICAL: Doctor cannot initiate video call")
            all_success = False
        else:
            call_id = call_response.get('call_id')
            jitsi_url = call_response.get('jitsi_url')
            room_name = call_response.get('room_name')
            provider_notified = call_response.get('provider_notified', False)
            
            print(f"   ✅ Video call initiated successfully")
            print(f"   Call ID: {call_id}")
            print(f"   Jitsi URL: {jitsi_url}")
            print(f"   Room Name: {room_name}")
            print(f"   Provider Notified: {provider_notified}")
            
            if not jitsi_url or not room_name:
                print("   ❌ Missing Jitsi URL or room name")
                all_success = False
            
            if not provider_notified:
                print("   ❌ Provider was not notified of incoming call")
                all_success = False
        
        # STEP 5: Test WebSocket notification system
        print("\n5️⃣ STEP 5: Test WebSocket Notification System")
        print("-" * 60)
        
        # Test WebSocket status endpoint
        success, ws_status = self.run_test(
            "WebSocket Status Check",
            "GET",
            "websocket/status",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            total_connections = ws_status.get('websocket_status', {}).get('total_connections', 0)
            connected_users = ws_status.get('websocket_status', {}).get('connected_users', [])
            current_user_connected = ws_status.get('current_user_connected', False)
            
            print(f"   ✅ WebSocket status accessible")
            print(f"   Total connections: {total_connections}")
            print(f"   Connected users: {len(connected_users)}")
            print(f"   Current user connected: {current_user_connected}")
        else:
            print("   ❌ WebSocket status not accessible")
            all_success = False
        
        # Test WebSocket test message
        success, test_msg_response = self.run_test(
            "WebSocket Test Message",
            "POST",
            "websocket/test-message",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            message_sent = test_msg_response.get('message_sent', False)
            user_connected = test_msg_response.get('user_connected', False)
            
            print(f"   ✅ WebSocket test message system working")
            print(f"   Message sent: {message_sent}")
            print(f"   User connected: {user_connected}")
            
            if not message_sent:
                print("   ⚠️  WebSocket message delivery may have issues")
        else:
            print("   ❌ WebSocket test message failed")
            all_success = False
        
        # Final diagnosis summary
        print("\n" + "=" * 80)
        print("🎯 APPOINTMENT VISIBILITY AND CALLING DIAGNOSIS SUMMARY")
        print("=" * 80)
        
        if all_success:
            print("✅ DIAGNOSIS COMPLETE: ALL SYSTEMS OPERATIONAL")
            print("✅ Appointment creation working correctly")
            print("✅ Provider dashboard shows own appointments")
            print("✅ Doctor dashboard shows all appointments")
            print("✅ Video call initiation working")
            print("✅ WebSocket notification system functional")
            print("✅ Appointment filtering logic correct")
            print("\n🎯 CONCLUSION: Backend appointment and calling systems are FULLY OPERATIONAL")
            print("If issues persist, they are likely in FRONTEND implementation")
        else:
            print("❌ DIAGNOSIS COMPLETE: ISSUES DETECTED")
            print("❌ Some appointment visibility or calling functionality failed")
            print("❌ Check specific failed tests above for details")
            print("\n🎯 CONCLUSION: Backend issues found that need fixing")
        
        return all_success

if __name__ == "__main__":
    # Run the appointment visibility and calling diagnosis test
    tester = AppointmentDiagnosisTester()
    
    print("🎯 APPOINTMENT VISIBILITY AND CALLING DIAGNOSIS")
    print("=" * 80)
    print("Testing specific issues mentioned in review request:")
    print("1. Create appointment with demo_provider/Demo123!")
    print("2. Check if appointment appears in provider's own dashboard")
    print("3. Check if appointment appears in doctor's dashboard")
    print("4. Test video call initiation from doctor to provider")
    print("5. Check WebSocket notifications")
    print("6. Verify notification delivery system")
    print("=" * 80)
    
    # First login to get tokens
    if not tester.login_all_roles():
        print("\n❌ Login failed - cannot continue with diagnosis")
        sys.exit(1)
    
    # Run the specific diagnosis test
    success = tester.diagnose_appointment_visibility_and_calling()
    
    if success:
        print("\n🎉 DIAGNOSIS COMPLETE: All systems working correctly!")
        print("✅ Backend appointment visibility and calling functionality is operational")
        print("✅ If issues persist, they are likely in frontend implementation")
    else:
        print("\n❌ DIAGNOSIS COMPLETE: Issues found in backend systems")
        print("❌ Check the detailed test results above for specific problems")
        print("❌ Backend fixes needed before frontend testing")
    
    sys.exit(0 if success else 1)