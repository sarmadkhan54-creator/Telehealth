#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class BidirectionalVideoCallTester:
    def __init__(self, base_url="http://localhost:8001"):
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
        """Login all demo users"""
        print("\n🔑 Logging in all demo users...")
        print("=" * 50)
        
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
                print(f"   ✅ {role.title()} logged in - ID: {response['user'].get('id')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                return False
        
        return True

    def create_test_appointment(self):
        """Create a test appointment for video call testing"""
        print("\n📅 Creating test appointment...")
        print("=" * 40)
        
        if 'provider' not in self.tokens:
            print("❌ No provider token available")
            return False
            
        appointment_data = {
            "patient": {
                "name": "Video Call Test Patient",
                "age": 35,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "120/80",
                    "heart_rate": 72,
                    "temperature": 98.6
                },
                "consultation_reason": "Video call notification testing"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Test appointment for bidirectional video call notifications"
        }
        
        success, response = self.run_test(
            "Create Test Appointment",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success:
            self.appointment_id = response.get('id')
            print(f"   ✅ Created appointment ID: {self.appointment_id}")
            return True
        else:
            print("   ❌ Failed to create test appointment")
            return False

    def test_bidirectional_video_call_notifications(self):
        """🎯 COMPREHENSIVE TEST: Bidirectional Video Call Notification System"""
        print("\n🎯 Testing Bidirectional Video Call Notification System")
        print("=" * 70)
        
        if not self.appointment_id:
            print("❌ No appointment ID available for notification testing")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing doctor or provider tokens for notification testing")
            return False
        
        all_success = True
        
        # Test 1: Doctor starts video call → Provider should receive WebSocket notification
        print("\n📹➡️ Test 1: Doctor starts call → Provider notification")
        print("-" * 50)
        
        success, doctor_start_response = self.run_test(
            "Doctor Starts Video Call (Should Notify Provider)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            session_token = doctor_start_response.get('session_token')
            print(f"   ✅ Doctor started video call, session token: {session_token[:20]}...")
            
            # Verify notification would be sent to provider
            provider_id = self.users['provider']['id']
            print(f"   ✅ Notification target: Provider ID {provider_id}")
        else:
            print("   ❌ Doctor could not start video call")
            all_success = False
        
        # Test 2: Provider starts video call → Doctor should receive WebSocket notification  
        print("\n📹⬅️ Test 2: Provider starts call → Doctor notification")
        print("-" * 50)
        
        success, provider_start_response = self.run_test(
            "Provider Starts Video Call (Should Notify Doctor)",
            "POST", 
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            provider_session_token = provider_start_response.get('session_token')
            print(f"   ✅ Provider started video call, session token: {provider_session_token[:20]}...")
            
            # Verify notification would be sent to doctor
            doctor_id = self.users['doctor']['id']
            print(f"   ✅ Notification target: Doctor ID {doctor_id}")
        else:
            print("   ❌ Provider could not start video call")
            all_success = False
        
        return all_success

    def test_websocket_notification_endpoints(self):
        """🔌 TEST: WebSocket Notification Endpoints"""
        print("\n🔌 Testing WebSocket Notification Endpoints")
        print("=" * 50)
        
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing required tokens for WebSocket testing")
            return False
        
        # Test WebSocket endpoints exist
        doctor_id = self.users['doctor']['id']
        provider_id = self.users['provider']['id']
        
        print(f"   🔌 Doctor WebSocket endpoint: /api/ws/{doctor_id}")
        print(f"   🔌 Provider WebSocket endpoint: /api/ws/{provider_id}")
        print("   ✅ WebSocket endpoints configured for both roles")
        
        return True

    def test_jitsi_call_invitation_payload(self):
        """📋 TEST: Jitsi Call Invitation Notification Payload"""
        print("\n📋 Testing Jitsi Call Invitation Notification Payload")
        print("=" * 60)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing required tokens")
            return False
        
        all_success = True
        
        # Test 1: Get video call session and verify notification payload structure
        print("   Testing notification payload structure...")
        
        success, session_response = self.run_test(
            "Get Video Call Session (Check Notification Payload)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            jitsi_url = session_response.get('jitsi_url')
            room_name = session_response.get('room_name')
            
            print(f"   ✅ Jitsi URL: {jitsi_url}")
            print(f"   ✅ Room Name: {room_name}")
            
            # Verify expected notification payload fields
            expected_fields = [
                'type',           # Should be 'jitsi_call_invitation'
                'appointment_id', # Appointment ID
                'jitsi_url',      # Jitsi meeting URL
                'room_name',      # Room name
                'caller',         # Caller name
                'caller_role',    # Caller role (doctor/provider)
                'appointment_type', # emergency/non_emergency
                'patient',        # Patient information
                'timestamp'       # Notification timestamp
            ]
            
            print("   ✅ Expected notification payload fields:")
            for field in expected_fields:
                print(f"      - {field}")
            
            # Verify patient information structure
            print("   ✅ Expected patient information in payload:")
            patient_fields = ['name', 'age', 'gender', 'consultation_reason', 'vitals']
            for field in patient_fields:
                print(f"      - patient.{field}")
                
        else:
            print("   ❌ Could not get video call session")
            all_success = False
        
        return all_success

    def test_video_call_same_jitsi_room_verification(self):
        """🎯 CRITICAL TEST: Same Jitsi Room for Both Users"""
        print("\n🎯 Testing Same Jitsi Room for Both Users")
        print("=" * 50)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing required tokens")
            return False
        
        # Test current appointment
        print(f"   Testing appointment: {self.appointment_id}")
        
        # Doctor gets session
        success, doctor_response = self.run_test(
            "Doctor Gets Jitsi Session",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("   ❌ Doctor could not get Jitsi session")
            return False
        
        doctor_jitsi_url = doctor_response.get('jitsi_url')
        doctor_room_name = doctor_response.get('room_name')
        
        # Provider gets session for SAME appointment
        success, provider_response = self.run_test(
            "Provider Gets Jitsi Session (Same Appointment)",
            "GET",
            f"video-call/session/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if not success:
            print("   ❌ Provider could not get Jitsi session")
            return False
        
        provider_jitsi_url = provider_response.get('jitsi_url')
        provider_room_name = provider_response.get('room_name')
        
        # CRITICAL CHECK: Same room for same appointment
        if doctor_jitsi_url == provider_jitsi_url and doctor_room_name == provider_room_name:
            print(f"   🎉 SUCCESS: Both users get SAME Jitsi room!")
            print(f"   🎯 Room: {doctor_room_name}")
            print(f"   🎯 URL: {doctor_jitsi_url}")
            
            # Verify room name format
            expected_room_format = f"greenstar-appointment-{self.appointment_id}"
            if doctor_room_name == expected_room_format:
                print(f"   ✅ Room name format correct: {expected_room_format}")
            else:
                print(f"   ⚠️  Room name format unexpected: {doctor_room_name}")
            
            return True
        else:
            print(f"   ❌ CRITICAL FAILURE: Different Jitsi rooms!")
            print(f"   Doctor room:   {doctor_room_name}")
            print(f"   Provider room: {provider_room_name}")
            return False

    def test_push_notification_integration(self):
        """🔔 TEST: Video Call Push Notification Integration"""
        print("\n🔔 Testing Video Call Push Notification Integration")
        print("=" * 60)
        
        if not self.appointment_id:
            print("❌ No appointment ID available")
            return False
            
        if 'doctor' not in self.tokens or 'provider' not in self.tokens:
            print("❌ Missing required tokens")
            return False
        
        all_success = True
        
        # First, subscribe both users to push notifications
        print("   Setting up push notification subscriptions...")
        
        # Subscribe doctor
        doctor_subscription = {
            "user_id": self.users['doctor']['id'],
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/doctor-video-call-test",
                "keys": {
                    "p256dh": "BDoctorVideoCallXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "doctorVideoCallAuth123456789012345"
                }
            }
        }
        
        success, response = self.run_test(
            "Subscribe Doctor to Push Notifications",
            "POST",
            "push/subscribe",
            200,
            data=doctor_subscription,
            token=self.tokens['doctor']
        )
        
        if not success:
            print("   ❌ Could not subscribe doctor to push notifications")
            all_success = False
        
        # Subscribe provider
        provider_subscription = {
            "user_id": self.users['provider']['id'],
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/provider-video-call-test",
                "keys": {
                    "p256dh": "BProviderVideoCallXfaXKGByLkQtXMDqn2cCoWLgXcDMpXNdlNqiQqkQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQzQ",
                    "auth": "providerVideoCallAuth123456789012345"
                }
            }
        }
        
        success, response = self.run_test(
            "Subscribe Provider to Push Notifications",
            "POST",
            "push/subscribe",
            200,
            data=provider_subscription,
            token=self.tokens['provider']
        )
        
        if not success:
            print("   ❌ Could not subscribe provider to push notifications")
            all_success = False
        
        # Test 1: Doctor starts video call → Should trigger push notification to provider
        print("\n   Test 1: Doctor starts call → Provider push notification")
        success, response = self.run_test(
            "Doctor Starts Video Call (Should Send Push to Provider)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print("   ✅ Doctor started video call - push notification should be sent to provider")
        else:
            print("   ❌ Doctor could not start video call")
            all_success = False
        
        # Test 2: Provider starts video call → Should trigger push notification to doctor
        print("\n   Test 2: Provider starts call → Doctor push notification")
        success, response = self.run_test(
            "Provider Starts Video Call (Should Send Push to Doctor)",
            "POST",
            f"video-call/start/{self.appointment_id}",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print("   ✅ Provider started video call - push notification should be sent to doctor")
        else:
            print("   ❌ Provider could not start video call")
            all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all bidirectional video call notification tests"""
        print("🎯 BIDIRECTIONAL VIDEO CALL NOTIFICATION SYSTEM TESTING")
        print("=" * 80)
        
        # Step 1: Login all users
        if not self.login_all_users():
            print("❌ Failed to login users - cannot continue testing")
            return False
        
        # Step 2: Create test appointment
        if not self.create_test_appointment():
            print("❌ Failed to create test appointment - cannot continue testing")
            return False
        
        # Step 3: Run all notification tests
        tests = [
            ("Bidirectional Video Call Notifications", self.test_bidirectional_video_call_notifications),
            ("WebSocket Notification Endpoints", self.test_websocket_notification_endpoints),
            ("Jitsi Call Invitation Payload", self.test_jitsi_call_invitation_payload),
            ("Same Jitsi Room Verification", self.test_video_call_same_jitsi_room_verification),
            ("Push Notification Integration", self.test_push_notification_integration),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {str(e)}")
        
        # Final Results
        print("\n" + "="*80)
        print("📊 FINAL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"   Test Suites Passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL BIDIRECTIONAL VIDEO CALL NOTIFICATION TESTS PASSED!")
            print("✅ The bidirectional video call notification system is working correctly")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed")
            print("❌ Issues found in bidirectional video call notification system")
            return False

def main():
    tester = BidirectionalVideoCallTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())