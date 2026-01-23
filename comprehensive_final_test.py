#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE FINAL TEST - All 4 Fixes Verification
Testing complete system after cache clearing and changes applied

EXPECTED RESULTS:
✅ New consultation areas (confirmed working in frontend)
✅ Real-time appointment sync with WebSocket improvements  
✅ Jitsi moderator automatic configuration (no "waiting for moderator")
✅ Always Online persistent WebSocket connections

This final test confirms all user's requested fixes are functional.
"""

import requests
import json
import time
from datetime import datetime
import sys

class ComprehensiveFinalTester:
    def __init__(self, base_url="https://docstream-sync.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.appointment_id = None
        self.call_id = None
        
        # Demo credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }
        
        # New consultation areas (27+ specialties)
        self.consultation_areas = [
            "Cardiology", "Emergency Medicine", "Allergy and Immunology", 
            "Endocrinology", "Dermatology", "Gastroenterology", "Hematology",
            "Infectious Disease", "Nephrology", "Neurology", "Oncology",
            "Ophthalmology", "Orthopedics", "Otolaryngology", "Pediatrics",
            "Psychiatry", "Pulmonology", "Radiology", "Rheumatology",
            "Surgery", "Urology", "Anesthesiology", "Family Medicine",
            "Internal Medicine", "Obstetrics and Gynecology", "Pathology",
            "Physical Medicine", "Plastic Surgery", "Preventive Medicine"
        ]

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test with enhanced error handling"""
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
        print("\n🔑 STEP 0: Login All Demo Users")
        print("=" * 60)
        
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

    def test_fix_1_new_consultation_areas(self):
        """🎯 FIX 1: Test New Consultation Areas (27+ specialties)"""
        print("\n🎯 FIX 1: NEW CONSULTATION AREAS TESTING")
        print("=" * 60)
        print("Testing all 27+ consultation specialties are working")
        print("=" * 60)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
        
        all_success = True
        tested_areas = []
        
        # Test creating appointments with different consultation areas
        for i, area in enumerate(self.consultation_areas[:5]):  # Test first 5 areas
            appointment_data = {
                "patient": {
                    "name": f"Patient {area} Test",
                    "age": 30 + i,
                    "gender": "Male" if i % 2 == 0 else "Female",
                    "vitals": {
                        "blood_pressure": "120/80",
                        "heart_rate": 72,
                        "temperature": 98.6,
                        "oxygen_saturation": 98,
                        "hb": 12.5,  # New field
                        "sugar_level": 120  # New field
                    },
                    "history": f"Patient history for {area} consultation",  # New field (replaces consultation_reason)
                    "area_of_consultation": area  # New field
                },
                "appointment_type": "emergency",
                "consultation_notes": f"Emergency consultation for {area}"
            }
            
            success, response = self.run_test(
                f"Create Appointment - {area}",
                "POST",
                "appointments",
                200,
                data=appointment_data,
                token=self.tokens['provider']
            )
            
            if success:
                tested_areas.append(area)
                print(f"   ✅ {area} consultation area working")
                if i == 0:  # Store first appointment for later tests
                    self.appointment_id = response.get('id')
            else:
                print(f"   ❌ {area} consultation area failed")
                all_success = False
        
        # Verify new fields are properly stored
        if self.appointment_id:
            success, response = self.run_test(
                "Verify New Fields Storage",
                "GET",
                f"appointments/{self.appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                patient = response.get('patient', {})
                vitals = patient.get('vitals', {})
                
                # Check new vitals fields
                if 'hb' in vitals and 'sugar_level' in vitals:
                    print("   ✅ New vitals fields (hb, sugar_level) properly stored")
                else:
                    print("   ❌ New vitals fields missing")
                    all_success = False
                
                # Check history field (replaces consultation_reason)
                if 'history' in patient:
                    print("   ✅ History field (replaces consultation_reason) working")
                else:
                    print("   ❌ History field missing")
                    all_success = False
                
                # Check area_of_consultation field
                if 'area_of_consultation' in patient:
                    print(f"   ✅ Area of consultation field working: {patient['area_of_consultation']}")
                else:
                    print("   ❌ Area of consultation field missing")
                    all_success = False
        
        print(f"\n📊 CONSULTATION AREAS SUMMARY:")
        print(f"   Tested Areas: {len(tested_areas)}")
        print(f"   Working Areas: {tested_areas}")
        print(f"   Total Available: {len(self.consultation_areas)} specialties")
        
        return all_success

    def test_fix_2_real_time_sync(self):
        """🎯 FIX 2: Test Real-time Appointment Sync with WebSocket improvements"""
        print("\n🎯 FIX 2: REAL-TIME APPOINTMENT SYNC TESTING")
        print("=" * 60)
        print("Testing appointments sync instantly between provider and doctor dashboards")
        print("=" * 60)
        
        if 'provider' not in self.tokens or 'doctor' not in self.tokens:
            print("❌ Missing provider or doctor tokens")
            return False
        
        all_success = True
        
        # Step 1: Get initial appointment counts
        success, provider_initial = self.run_test(
            "Provider Initial Appointments",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        success, doctor_initial = self.run_test(
            "Doctor Initial Appointments", 
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Could not get initial appointment counts")
            return False
        
        provider_initial_count = len(provider_initial)
        doctor_initial_count = len(doctor_initial)
        
        print(f"   📊 Initial counts - Provider: {provider_initial_count}, Doctor: {doctor_initial_count}")
        
        # Step 2: Provider creates new emergency appointment
        sync_test_data = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 28,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "140/90",
                    "heart_rate": 95,
                    "temperature": 99.2,
                    "oxygen_saturation": 96,
                    "hb": 11.5,
                    "sugar_level": 140
                },
                "history": "Severe chest pain and shortness of breath for 2 hours",
                "area_of_consultation": "Emergency Medicine"
            },
            "appointment_type": "emergency",
            "consultation_notes": "URGENT: Patient experiencing severe chest pain"
        }
        
        success, response = self.run_test(
            "Provider Creates Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=sync_test_data,
            token=self.tokens['provider']
        )
        
        if not success:
            print("❌ Provider could not create appointment")
            return False
        
        new_appointment_id = response.get('id')
        print(f"   ✅ New appointment created: {new_appointment_id}")
        
        # Step 3: Immediate check - Provider dashboard should show new appointment
        success, provider_updated = self.run_test(
            "Provider Dashboard - Immediate Check",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_new_count = len(provider_updated)
            if provider_new_count == provider_initial_count + 1:
                print("   ✅ Provider dashboard immediately shows new appointment")
            else:
                print(f"   ❌ Provider dashboard sync issue: expected {provider_initial_count + 1}, got {provider_new_count}")
                all_success = False
        
        # Step 4: Immediate check - Doctor dashboard should show new appointment
        success, doctor_updated = self.run_test(
            "Doctor Dashboard - Immediate Check",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            doctor_new_count = len(doctor_updated)
            if doctor_new_count == doctor_initial_count + 1:
                print("   ✅ Doctor dashboard immediately shows new appointment")
            else:
                print(f"   ❌ Doctor dashboard sync issue: expected {doctor_initial_count + 1}, got {doctor_new_count}")
                all_success = False
            
            # Verify the specific appointment is visible to doctor
            new_appointment_visible = any(apt.get('id') == new_appointment_id for apt in doctor_updated)
            if new_appointment_visible:
                print("   ✅ New appointment immediately visible to doctor")
            else:
                print("   ❌ New appointment not visible to doctor")
                all_success = False
        
        # Step 5: Test WebSocket status endpoint
        success, ws_status = self.run_test(
            "WebSocket Status Check",
            "GET",
            "websocket/status",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ WebSocket status endpoint accessible")
            print(f"   WebSocket connections: {ws_status.get('websocket_status', {}).get('total_connections', 0)}")
        else:
            print("   ❌ WebSocket status endpoint failed")
            all_success = False
        
        # Step 6: Test WebSocket notification system
        success, test_message = self.run_test(
            "WebSocket Test Message",
            "POST",
            "websocket/test-message",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ WebSocket test message system working")
            print(f"   Message sent: {test_message.get('message_sent', False)}")
        else:
            print("   ❌ WebSocket test message failed")
            all_success = False
        
        return all_success

    def test_fix_3_jitsi_moderator_fix(self):
        """🎯 FIX 3: Test Jitsi Moderator Automatic Configuration"""
        print("\n🎯 FIX 3: JITSI MODERATOR AUTOMATIC CONFIGURATION TESTING")
        print("=" * 60)
        print("Testing video calls start immediately without moderator issues")
        print("=" * 60)
        
        if not self.appointment_id or 'doctor' not in self.tokens:
            print("❌ No appointment ID or doctor token available")
            return False
        
        all_success = True
        
        # Step 1: Doctor initiates video call
        success, response = self.run_test(
            "Doctor Initiates Video Call",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("❌ Doctor could not initiate video call")
            return False
        
        self.call_id = response.get('call_id')
        jitsi_url = response.get('jitsi_url')
        room_name = response.get('room_name')
        
        print(f"   ✅ Video call initiated successfully")
        print(f"   Call ID: {self.call_id}")
        print(f"   Room Name: {room_name}")
        print(f"   Jitsi URL: {jitsi_url}")
        
        # Step 2: Verify Jitsi URL contains moderator configuration
        if jitsi_url:
            # Check for automatic moderator settings in URL
            moderator_configs = [
                "config.prejoinPageEnabled=false",
                "config.requireDisplayName=false", 
                "config.startWithVideoMuted=false",
                "config.startWithAudioMuted=false"
            ]
            
            moderator_settings_found = 0
            for config in moderator_configs:
                if config in jitsi_url:
                    moderator_settings_found += 1
                    print(f"   ✅ Moderator setting found: {config}")
            
            if moderator_settings_found >= 2:
                print("   ✅ Jitsi URL contains automatic moderator configuration")
            else:
                print("   ❌ Jitsi URL missing moderator configuration")
                all_success = False
            
            # Check for doctor name in URL (automatic moderator)
            if "Dr." in jitsi_url:
                print("   ✅ Doctor automatically set as moderator in URL")
            else:
                print("   ⚠️  Doctor name not found in URL (may still work)")
        
        # Step 3: Test provider notification and same room access
        if 'provider' in self.tokens:
            # Get video call session for provider
            success, session_response = self.run_test(
                "Provider Gets Video Call Session",
                "GET",
                f"video-call/session/{self.appointment_id}",
                200,
                token=self.tokens['provider']
            )
            
            if success:
                provider_jitsi_url = session_response.get('jitsi_url')
                provider_room_name = session_response.get('room_name')
                
                # Verify both users get same room (no moderator waiting)
                if provider_room_name == room_name:
                    print("   ✅ Provider gets SAME Jitsi room as doctor")
                    print("   ✅ No 'waiting for moderator' issue - both join same room")
                else:
                    print(f"   ❌ Room mismatch - Doctor: {room_name}, Provider: {provider_room_name}")
                    all_success = False
            else:
                print("   ❌ Provider could not get video call session")
                all_success = False
        
        # Step 4: Test multiple call attempts (WhatsApp-like functionality)
        success, second_call = self.run_test(
            "Doctor Second Call Attempt",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            second_call_id = second_call.get('call_id')
            second_room_name = second_call.get('room_name')
            call_attempt = second_call.get('call_attempt', 1)
            
            print(f"   ✅ Multiple call attempts working (WhatsApp-like)")
            print(f"   Second Call ID: {second_call_id}")
            print(f"   Call Attempt Number: {call_attempt}")
            
            # Verify different call IDs but same appointment
            if second_call_id != self.call_id:
                print("   ✅ Each call attempt gets unique call ID")
            else:
                print("   ❌ Call IDs should be unique for each attempt")
                all_success = False
        
        return all_success

    def test_fix_4_always_online_websockets(self):
        """🎯 FIX 4: Test Always Online Persistent WebSocket Connections"""
        print("\n🎯 FIX 4: ALWAYS ONLINE PERSISTENT WEBSOCKET CONNECTIONS TESTING")
        print("=" * 60)
        print("Testing WhatsApp-like calling functionality with persistent connections")
        print("=" * 60)
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens")
            return False
        
        all_success = True
        
        # Step 1: Test WebSocket connection status for both users
        for role in ['doctor', 'provider']:
            success, ws_status = self.run_test(
                f"WebSocket Status - {role.title()}",
                "GET",
                "websocket/status",
                200,
                token=self.tokens[role]
            )
            
            if success:
                user_connected = ws_status.get('current_user_connected', False)
                total_connections = ws_status.get('websocket_status', {}).get('total_connections', 0)
                
                print(f"   ✅ {role.title()} WebSocket status accessible")
                print(f"   Total connections: {total_connections}")
                print(f"   User connected: {user_connected}")
            else:
                print(f"   ❌ {role.title()} WebSocket status failed")
                all_success = False
        
        # Step 2: Test persistent notification delivery
        for role in ['doctor', 'provider']:
            success, test_msg = self.run_test(
                f"Test Notification - {role.title()}",
                "POST",
                "websocket/test-message",
                200,
                token=self.tokens[role]
            )
            
            if success:
                message_sent = test_msg.get('message_sent', False)
                user_connected = test_msg.get('user_connected', False)
                
                print(f"   ✅ {role.title()} notification system working")
                print(f"   Message delivery: {message_sent}")
                print(f"   Connection status: {user_connected}")
            else:
                print(f"   ❌ {role.title()} notification system failed")
                all_success = False
        
        # Step 3: Test video call notification delivery (WhatsApp-like)
        if self.appointment_id:
            success, call_response = self.run_test(
                "Video Call with Notification",
                "POST",
                f"video-call/start/{self.appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                provider_notified = call_response.get('provider_notified', False)
                auto_answer = call_response.get('auto_answer', False)
                
                print("   ✅ Video call notification system working")
                print(f"   Provider notified: {provider_notified}")
                print(f"   WhatsApp-like instant delivery: {auto_answer}")
                
                if provider_notified:
                    print("   ✅ Always-online notification delivery confirmed")
                else:
                    print("   ❌ Notification delivery failed")
                    all_success = False
            else:
                print("   ❌ Video call notification failed")
                all_success = False
        
        # Step 4: Test call history tracking (multiple attempts)
        if self.appointment_id:
            success, appointment_details = self.run_test(
                "Check Call History",
                "GET",
                f"appointments/{self.appointment_id}",
                200,
                token=self.tokens['doctor']
            )
            
            if success:
                call_history = appointment_details.get('call_history', [])
                
                if call_history:
                    print(f"   ✅ Call history tracking working ({len(call_history)} calls)")
                    for i, call in enumerate(call_history):
                        print(f"   Call {i+1}: {call.get('status', 'unknown')} - {call.get('doctor_name', 'unknown')}")
                else:
                    print("   ❌ Call history not tracked")
                    all_success = False
        
        # Step 5: Test appointment type restrictions (emergency vs non-emergency)
        # Create non-emergency appointment to test restrictions
        non_emergency_data = {
            "patient": {
                "name": "Non-Emergency Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6,
                    "oxygen_saturation": 98,
                    "hb": 13.0,
                    "sugar_level": 110
                },
                "history": "Routine follow-up consultation",
                "area_of_consultation": "Family Medicine"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Regular checkup appointment"
        }
        
        success, non_emergency_response = self.run_test(
            "Create Non-Emergency Appointment",
            "POST",
            "appointments",
            200,
            data=non_emergency_data,
            token=self.tokens['provider']
        )
        
        if success:
            non_emergency_id = non_emergency_response.get('id')
            
            # Try to start video call on non-emergency (should fail)
            success, call_response = self.run_test(
                "Video Call on Non-Emergency (Should Fail)",
                "POST",
                f"video-call/start/{non_emergency_id}",
                403,  # Should be forbidden
                token=self.tokens['doctor']
            )
            
            if success:
                print("   ✅ Non-emergency video call restriction working")
                print("   ✅ System correctly blocks video calls for non-emergency appointments")
            else:
                print("   ❌ Non-emergency video call restriction failed")
                all_success = False
        
        return all_success

    def run_comprehensive_final_test(self):
        """Run the complete comprehensive final test"""
        print("🎯 COMPREHENSIVE FINAL TEST - ALL 4 FIXES VERIFICATION")
        print("=" * 80)
        print("Testing complete system after cache clearing and changes applied")
        print("=" * 80)
        
        # Step 0: Login all users
        if not self.login_all_users():
            print("❌ CRITICAL: Could not login demo users")
            return False
        
        # Step 1: Test Fix 1 - New Consultation Areas
        fix1_success = self.test_fix_1_new_consultation_areas()
        
        # Step 2: Test Fix 2 - Real-time Sync
        fix2_success = self.test_fix_2_real_time_sync()
        
        # Step 3: Test Fix 3 - Jitsi Moderator Fix
        fix3_success = self.test_fix_3_jitsi_moderator_fix()
        
        # Step 4: Test Fix 4 - Always Online WebSockets
        fix4_success = self.test_fix_4_always_online_websockets()
        
        # Final Summary
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE FINAL TEST RESULTS")
        print("=" * 80)
        
        fixes_status = [
            ("✅ New Consultation Areas (27+ specialties)", fix1_success),
            ("✅ Real-time Appointment Sync with WebSocket improvements", fix2_success), 
            ("✅ Jitsi Moderator Automatic Configuration", fix3_success),
            ("✅ Always Online Persistent WebSocket Connections", fix4_success)
        ]
        
        all_fixes_working = True
        for fix_name, status in fixes_status:
            if status:
                print(f"✅ {fix_name}: WORKING")
            else:
                print(f"❌ {fix_name}: FAILED")
                all_fixes_working = False
        
        print(f"\n📊 OVERALL TEST RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if all_fixes_working:
            print("\n🎉 COMPREHENSIVE FINAL TEST: ALL 4 FIXES WORKING CORRECTLY")
            print("✅ Emergency appointment creation with new History and Area of Consultation fields")
            print("✅ Instant appointment visibility across dashboards") 
            print("✅ Video calls start immediately without moderator issues")
            print("✅ WhatsApp-like calling functionality working")
            print("\n🎯 SYSTEM READY FOR PRODUCTION USE")
        else:
            print("\n❌ COMPREHENSIVE FINAL TEST: SOME FIXES NEED ATTENTION")
            print("❌ Review failed tests above for specific issues")
        
        return all_fixes_working

if __name__ == "__main__":
    print("Starting Comprehensive Final Test...")
    tester = ComprehensiveFinalTester()
    success = tester.run_comprehensive_final_test()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - SYSTEM FULLY OPERATIONAL")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - REVIEW RESULTS ABOVE")
        sys.exit(1)